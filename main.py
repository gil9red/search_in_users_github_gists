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


from sqlalchemy import Column, Integer, String, literal, or_
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class Gist(Base):
    """
    Класс описывает гист гитхаба.

    """

    __tablename__ = 'Gist'

    id = Column(Integer, primary_key=True)

    url = Column(String)

    description = Column(String)

    # Суммарный текст всех файлов гиста
    text = Column(String)

    def __init__(self, url, description, text):
        self.url = url
        self.description = description
        self.text = text

    def __repr__(self):
        return "<Gist(id: {}, url: {}, description: {}, len(text): {})>".format(
            self.id, self.url, self.description, len(self.text))


def get_session():
    import os
    DIR = os.path.dirname(__file__)
    DB_FILE_NAME = 'sqlite:///' + os.path.join(DIR, 'database')
    # DB_FILE_NAME = 'sqlite:///:memory:'

    # Создаем базу, включаем логирование и автообновление подключения каждые 2 часа (7200 секунд)
    from sqlalchemy import create_engine
    engine = create_engine(
        DB_FILE_NAME,
        # echo=True,
        pool_recycle=7200
    )

    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()


session = get_session()


from urllib.parse import urljoin


# TODO: перенесение в py
class ParserGists:
    URL_GIST_PAGE = 'https://gist.github.com/{}?page={}'
    URL_LOGIN = 'https://github.com/login'

    def __init__(self, session, login, password, log_func=None, proxy=None, proxy_type=None):
        self.session = session
        self.query = session.query(Gist)

        self.login = login
        self.password = password

        self.log_func = log_func

        self.proxy = proxy
        self.proxy_type = proxy_type

        self.stop = False

    def log(self, *args, **kwargs):
        if self.log_func:
            self.log_func(*args, **kwargs)

    def run(self):
        from grab import Grab
        g = Grab()
        g.setup(proxy=self.proxy, proxy_type=self.proxy_type)

        self.log("...Перехожу на страницу входа...")
        g.go(ParserGists.URL_LOGIN)

        self.log("...Заполняем формы логина и пароля...")
        g.set_input('login', self.login)
        g.set_input('password', self.password)

        self.log("...Отсылаю данные формы...")
        g.submit()

        page = 1

        self.log("...Перехожу на страницу с гистов...")
        g.go(ParserGists.URL_GIST_PAGE.format(self.login, page))

        redirect = g.css_one('.blankslate p a').attrib['href']
        self.log("...Выполняю редирект на {}...".format(redirect))
        g.go(redirect)

        css_select_gist = '.gist-snippet .byline'

        i = 0

        import time
        t = time.clock()

        while True:
            try:
                for gist in g.css_list(css_select_gist):
                    i += 1

                    a = gist.cssselect('.creator a')[1]
                    href = urljoin(g.response.url, a.attrib['href'])

                    # Проверка, что в базе гиста с таким url нет
                    if self.has_gist(href):
                        self.log('Гист с url "%s" уже есть в базе', href)
                        continue

                    desc = gist.cssselect('.description')

                    desc_children = desc[0].xpath('child::*')
                    if desc_children:
                        desc = ' '.join([_.text.strip() for _ in desc + desc_children]).strip()
                    else:
                        desc = desc[0].text.strip()

                    self.log('{}. "{}": {}'.format(i, desc, href))

                    # Получение содержимого гиста
                    text = self.get_gist_content(g, href)

                    gist = Gist(href, desc, text)
                    self.session.add(gist)
                    self.session.commit()

            except Exception:
                # TODO: перенести в log
                logging.exception('Error:')

            page += 1
            g.go(ParserGists.URL_GIST_PAGE.format(self.login, page))

            if not g.css_exists(css_select_gist):
                break

        self.log("...На сбор потрачено времени %s...", time.clock() - t)

    def has_gist(self, url):
        # Проверка, что в базе гиста с таким url нет
        has = self.query.filter(Gist.url == url).exists()
        return self.session.query(literal(True)).filter(has).scalar()

    def get_gist_content(self, grab, url):
        # Переход на страницу гиста
        grab.go(url)
        text = ''
        for url_raw in grab.css_list('.file .file-header .file-actions a'):
            href = urljoin(grab.response.url, url_raw.attrib['href'])
            self.log('    {}'.format(href))

            grab.go(href)
            text += grab.response.body

        return text


from PySide.QtGui import *
from PySide.QtCore import *


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('search_in_users_github_gists')

        self.filter_line_edit = QLineEdit()
        self.filter_line_edit.textEdited.connect(self.run_filter)

        self.gist_list = QListWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.filter_line_edit)
        layout.addWidget(self.gist_list)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        tool_bar = self.addToolBar('MainToolBar')
        action = tool_bar.addAction("Перечитать все гисты пользователя")
        action.triggered.connect(self.reload)

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
        dialog.show()

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

        parser = ParserGists(
            session,
            config.login, config.password,
            log,
            config.proxy, config.proxy_type
        )
        parser.run()

        dialog.exec_()

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
            self.gist_list.addItem(gist.url + ': ' + gist.description)

    def closeEvent(self, *args, **kwargs):
        quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    mw = MainWindow()
    mw.show()
    mw.run_filter()

    app.exec_()
