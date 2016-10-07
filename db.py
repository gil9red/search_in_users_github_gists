#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


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
