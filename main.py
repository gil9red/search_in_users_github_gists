#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import sys
# import logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s',
#     handlers=[
#         logging.FileHandler('log', encoding='utf8'),
#         logging.StreamHandler(stream=sys.stdout),
#     ],
# )


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


if __name__ == '__main__':
    from grab import Grab
    g = Grab()

    print("...Перехожу на страницу входа...")
    g.go('https://github.com/login')

    login = ''
    password = ''

    print("...Заполняем формы логина и пароля...")
    g.set_input('login', login)
    g.set_input('password', password)

    print("...Отсылаю данные формы...")
    g.submit()


    page = 1

    print("...Перехожу на страницу с гистов...")
    g.go("https://gist.github.com/gil9red?page={}".format(page))

    redirect = g.css_one('.blankslate p a').attrib['href']
    print("...Выполняю редирект на {}...".format(redirect))
    g.go(redirect)

    css_select_gist = '.gist-snippet .byline'

    i = 0

    from urllib.parse import urljoin


    import time
    t = time.clock()

    while True:
        for gist in g.css_list(css_select_gist):
            i += 1

            a = gist.cssselect('.creator a')[1]
            href = urljoin(g.response.url, a.attrib['href'])

            # Проверка, что в базе гиста с таким url нет
            has = session.query(Gist).filter(Gist.url == href).exists()
            has = session.query(literal(True)).filter(has).scalar()
            if has:
                continue

            desc = gist.cssselect('.description')
            desc_children = desc[0].xpath('child::*')
            if desc_children:
                desc = ' '.join([_.text.strip() for _ in desc + desc_children]).strip()
            else:
                desc = desc[0].text.strip()

            print('{}. "{}": {}'.format(i, desc, href))

            # Переход на страницу гиста
            g.go(href)
            text = ''
            for url_raw in g.css_list('.file .file-header .file-actions a'):
                href = urljoin(g.response.url, url_raw.attrib['href'])
                print('    {}'.format(href))

                g.go(href)
                text += g.response.body

            print()

            gist = Gist(href, desc, text)
            session.add(gist)

        page += 1
        g.go("https://gist.github.com/gil9red?page={}".format(page))

        if not g.css_exists(css_select_gist):
            break

    session.commit()

    for gist in session.query(Gist).all():
        print(gist)

    print()
    print("Time:", time.clock() - t)
