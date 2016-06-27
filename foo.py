#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


"""Скрипт для тренировки написания запросов."""


from main import session, Gist

# # Получить все
# for gist in session.query(Gist).all():
#     print(gist)

# Поиск гистов у которых в заголовке есть строка "go"
for gist in session.query(Gist).filter(Gist.description.like("%go%")).all():
    print(gist)
