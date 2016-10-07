#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import sys
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s',
    handlers=[
        logging.FileHandler('log', encoding='utf8'),
        logging.StreamHandler(stream=sys.stdout),
    ],
)


# Для отлова всех исключений, которые в слотах Qt могут "затеряться" и привести к тихому падению
def log_uncaught_exceptions(ex_cls, ex, tb):
    import traceback

    text = '{}: {}:\n'.format(ex_cls.__name__, ex)
    text += ''.join(traceback.format_tb(tb))

    logging.error(text)
    QMessageBox.critical(None, 'Error', text)
    quit()


sys.excepthook = log_uncaught_exceptions


from db import *
session = get_session()


from parser_gists import ParserGists

try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('search_in_users_github_gists')

        self.filter_line_edit = QLineEdit()
        self.filter_line_edit.textEdited.connect(self.run_filter)

        self.gist_list = QListWidget()
        self.gist_list.itemDoubleClicked.connect(self.item_double_click)

        layout = QVBoxLayout()
        layout.addWidget(self.filter_line_edit)
        layout.addWidget(self.gist_list)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        tool_bar = self.addToolBar('Основное')
        action_reload = tool_bar.addAction("Перечитать все гисты пользователя")
        action_reload.setToolTip('Удаление текущих гистов и подгрузка новых')
        action_reload.setStatusTip(action_reload.toolTip())
        action_reload.triggered.connect(self.reload)

        action_sync = tool_bar.addAction("Синхронизация")
        action_sync.setToolTip('Удаление уже несуществующих гистов и добавление новых')
        action_sync.setStatusTip(action_reload.toolTip())
        action_sync.triggered.connect(self.sync)

        self.setStatusBar(QStatusBar())

    @staticmethod
    def item_double_click(item):
        url = item.data(Qt.UserRole)
        QDesktopServices.openUrl(QUrl(url))

    def reload(self):
        for _ in session.query(Gist).all():
            session.delete(_)
        session.commit()

        # TODO: возможность прервать считывание
        dialog = QDialog()
        dialog.setWindowTitle('Reload')
        dialog.resize(200, 200)

        dialog_button_box = QDialogButtonBox()
        dialog_button_box.accepted.connect(dialog.accept)
        dialog_button_box.rejected.connect(dialog.reject)

        log_text_edit = QPlainTextEdit()
        log_text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(log_text_edit)
        layout.addWidget(dialog_button_box)

        dialog.setLayout(layout)

        import config

        def log(*args, **kwargs):
            logging.debug(*args, **kwargs)

            # Используем стандартный print для печати в строку
            import io
            str_io = io.StringIO()
            kwargs['file'] = str_io
            kwargs['end'] = ''
            print(*args, **kwargs)
            text = str_io.getvalue()
            log_text_edit.appendPlainText(text)

            QApplication.processEvents()

        if not config.login or not config.password:
            QMessageBox.information(self, "Внимание", "Не указан логин или пароль.")
            return

        dialog.show()

        parser = ParserGists(
            session,
            config.login, config.password,
            log,
            config.proxy, config.proxy_type
        )
        parser.run()

        dialog.close()

        self.run_filter()

    def sync(self):
        # TODO: дублирование reload
        # TODO: возможность прервать считывание
        dialog = QDialog()
        dialog.setWindowTitle('Sync')
        dialog.resize(200, 200)

        dialog_button_box = QDialogButtonBox()
        dialog_button_box.accepted.connect(dialog.accept)
        dialog_button_box.rejected.connect(dialog.reject)

        log_text_edit = QPlainTextEdit()
        log_text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(log_text_edit)
        layout.addWidget(dialog_button_box)

        dialog.setLayout(layout)

        import config

        def log(*args, **kwargs):
            logging.debug(*args, **kwargs)

            # Используем стандартный print для печати в строку
            import io
            str_io = io.StringIO()
            kwargs['file'] = str_io
            kwargs['end'] = ''
            print(*args, **kwargs)
            text = str_io.getvalue()
            log_text_edit.appendPlainText(text)

            QApplication.processEvents()

        if not config.login or not config.password:
            QMessageBox.information(self, "Внимание", "Не указан логин или пароль.")
            return

        dialog.show()

        # TODO: вынести в класс
        def check_url(url):
            """Функция проверяет, что url доступен."""

            from urllib.error import HTTPError

            try:
                from urllib.request import urlopen
                urlopen(url)
            except HTTPError as e:
                if e.code == 404:
                    return False

            return True

        for _ in session.query(Gist).all():
            if not check_url(_.url):
                log('Гист с url: "%s", description: "%s" не существует.', _.url, _.description)
                session.delete(_)
            else:
                log('Гист с url: "%s", description: "%s" существует.', _.url, _.description)

        session.commit()

        parser = ParserGists(
            session,
            config.login, config.password,
            log,
            config.proxy, config.proxy_type
        )
        parser.run()

        dialog.close()

        self.run_filter()

    def run_filter(self):
        # TODO: лучше использовать модель
        # TODO: лучше использовать стандартный фильтр qt
        # TODO: поиграться с делегатами для красивого отображения описания + ссылки на гист
        self.gist_list.clear()

        filter_text = self.filter_line_edit.text()
        filter_text = "%{}%".format(filter_text)
        sql_filter = or_(Gist.description.like(filter_text), Gist.text.like(filter_text))

        for gist in session.query(Gist).filter(sql_filter).all():
            item = QListWidgetItem(gist.url + ': ' + gist.description)
            item.setData(Qt.UserRole, gist.url)
            item.setData(Qt.UserRole + 1, gist.description)
            self.gist_list.addItem(item)

    def closeEvent(self, *args, **kwargs):
        quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.resize(500, 300)
    mw.show()
    mw.run_filter()

    app.exec_()
