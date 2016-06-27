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


from sqlalchemy import Column, Integer, String, literal
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


import config
from urllib.parse import urljoin


class ParserGists:
    URL_GIST_PAGE = 'https://gist.github.com/{}?page={}'
    URL_LOGIN = 'https://github.com/login'

    def __init__(self, session):
        self.session = session
        self.query = session.query(Gist)

    def run(self):
        from grab import Grab
        g = Grab()
        g.setup(proxy=config.proxy, proxy_type=config.proxy_type)

        logging.debug("...Перехожу на страницу входа...")
        g.go(ParserGists.URL_LOGIN)

        logging.debug("...Заполняем формы логина и пароля...")
        g.set_input('login', config.login)
        g.set_input('password', config.password)

        logging.debug("...Отсылаю данные формы...")
        g.submit()

        page = 1

        logging.debug("...Перехожу на страницу с гистов...")
        g.go(ParserGists.URL_GIST_PAGE.format(config.login, page))

        redirect = g.css_one('.blankslate p a').attrib['href']
        logging.debug("...Выполняю редирект на {}...".format(redirect))
        g.go(redirect)

        css_select_gist = '.gist-snippet .byline'

        i = 0

        import time
        t = time.clock()

        while True:
            for gist in g.css_list(css_select_gist):
                i += 1

                a = gist.cssselect('.creator a')[1]
                href = urljoin(g.response.url, a.attrib['href'])

                # Проверка, что в базе гиста с таким url нет
                if self.has_gist(href):
                    continue

                desc = gist.cssselect('.description')
                desc_children = desc[0].xpath('child::*')
                if desc_children:
                    desc = ' '.join([_.text.strip() for _ in desc + desc_children]).strip()
                else:
                    desc = desc[0].text.strip()

                logging.debug('{}. "{}": {}'.format(i, desc, href))

                # Получение содержимого гиста
                text = self.get_gist_content(g, href)

                gist = Gist(href, desc, text)
                self.session.add(gist)

            page += 1
            g.go(ParserGists.URL_GIST_PAGE.format(page))

            if not g.css_exists(css_select_gist):
                break

            break

        self.session.commit()

        logging.debug("...На сбор потрачено времени %s...", time.clock() - t)

    def has_gist(self, url):
        # Проверка, что в базе гиста с таким url нет
        has = self.query.filter(Gist.url == url).exists()
        return self.session.query(literal(True)).filter(has).scalar()

    @staticmethod
    def get_gist_content(grab, url):
        # Переход на страницу гиста
        grab.go(url)
        text = ''
        for url_raw in grab.css_list('.file .file-header .file-actions a'):
            href = urljoin(grab.response.url, url_raw.attrib['href'])
            logging.debug('    {}'.format(href))

            grab.go(href)
            text += grab.response.body

        return text

if __name__ == '__main__':
    parser = ParserGists(session)
    parser.run()
