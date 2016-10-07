#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


from urllib.parse import urljoin
import logging

from db import *


# TODO: объекдинить код обработки парсерами. Сделать его универсальным
# class ParserGists:
#     URL_GIST_PAGE = 'https://gist.github.com/{}?page={}'
#     URL_LOGIN = 'https://github.com/login'
#
#     def __init__(self, session, login, password, log_func=None, proxy=None, proxy_type=None):
#         self.session = session
#         self.query = session.query(Gist)
#
#         self.login = login
#         self.password = password
#
#         self.log_func = log_func
#
#         self.proxy = proxy
#         self.proxy_type = proxy_type
#
#         self.stop = False
#
#     def log(self, *args, **kwargs):
#         if self.log_func:
#             self.log_func(*args, **kwargs)
#
#     def run(self):
#         from grab import Grab
#         g = Grab()
#         g.setup(proxy=self.proxy, proxy_type=self.proxy_type)
#
#         self.log("...Перехожу на страницу входа...")
#         g.go(ParserGists.URL_LOGIN)
#
#         self.log("...Заполняем формы логина и пароля...")
#         g.set_input('login', self.login)
#         g.set_input('password', self.password)
#
#         self.log("...Отсылаю данные формы...")
#         g.submit()
#
#         page = 1
#
#         self.log("...Перехожу на страницу с гистов...")
#         g.go(ParserGists.URL_GIST_PAGE.format(self.login, page))
#
#         redirect = g.css_one('.blankslate p a').attrib['href']
#         self.log("...Выполняю редирект на {}...".format(redirect))
#         g.go(redirect)
#
#         css_select_gist = '.gist-snippet .byline'
#
#         i = 0
#
#         import time
#         t = time.clock()
#
#         while True:
#             try:
#                 for gist in g.css_list(css_select_gist):
#                     i += 1
#
#                     a = gist.cssselect('.creator a')[1]
#                     href = urljoin(g.response.url, a.attrib['href'])
#
#                     # Проверка, что в базе гиста с таким url нет
#                     if self.has_gist(href):
#                         self.log('Гист с url "%s" уже есть в базе', href)
#                         continue
#
#                     desc = gist.cssselect('.description')
#
#                     desc_children = desc[0].xpath('child::*')
#                     if desc_children:
#                         desc = ' '.join([_.text.strip() for _ in desc + desc_children]).strip()
#                     else:
#                         desc = desc[0].text.strip()
#
#                     self.log('{}. "{}": {}'.format(i, desc, href))
#
#                     # Получение содержимого гиста
#                     text = self.get_gist_content(g, href)
#
#                     gist = Gist(href, desc, text)
#                     self.session.add(gist)
#                     self.session.commit()
#
#             except Exception:
#                 # TODO: перенести в log
#                 logging.exception('Error:')
#
#             page += 1
#             g.go(ParserGists.URL_GIST_PAGE.format(self.login, page))
#
#             if not g.css_exists(css_select_gist):
#                 break
#
#         self.log("...На сбор потрачено времени %s...", time.clock() - t)
#
#     def has_gist(self, url):
#         # Проверка, что в базе гиста с таким url нет
#         has = self.query.filter(Gist.url == url).exists()
#         return self.session.query(literal(True)).filter(has).scalar()
#
#     def get_gist_content(self, grab, url):
#         # Переход на страницу гиста
#         grab.go(url)
#         text = ''
#         for url_raw in grab.css_list('.file .file-header .file-actions a'):
#             href = urljoin(grab.response.url, url_raw.attrib['href'])
#             self.log('    {}'.format(href))
#
#             grab.go(href)
#             text += grab.response.body
#
#         return text


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
        from robobrowser import RoboBrowser
        browser = RoboBrowser(
            user_agent='Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0',
            parser='lxml'
        )

        # Настройка прокси
        if self.proxy_type or self.proxy:
            browser.session.proxies = {self.proxy_type: self.proxy}

        self.log("...Перехожу на страницу входа...")
        browser.open(ParserGists.URL_LOGIN)

        self.log("...Заполняем формы логина и пароля...")
        signup_form = browser.get_form()
        signup_form['login'].value = self.login
        signup_form['password'].value = self.password

        self.log("...Отсылаю данные формы...")
        # Submit the form
        browser.submit_form(signup_form)

        page = 1

        self.log("...Перехожу на страницу с гистов...")
        browser.open(ParserGists.URL_GIST_PAGE.format(self.login, page))

        # NOTE: для robobrowser похоже не требуется
        # redirect = g.css_one('.blankslate p a').attrib['href']
        # self.log("...Выполняю редирект на {}...".format(redirect))
        # g.go(redirect)

        css_select_gist = '.gist-snippet .byline'

        i = 0

        import time
        t = time.clock()

        while True:
            for gist in browser.select(css_select_gist):
                i += 1

                a = gist.select('.creator > a')[1]
                href = urljoin(browser.response.url, a['href'])

                # Проверка, что в базе гиста с таким url нет
                if self.has_gist(href):
                    self.log('Гист с url "%s" уже есть в базе', href)
                    continue

                desc = gist.select('.description')
                desc_children = desc[0].select('*')
                if desc_children:
                    desc = ' '.join([_.text.strip() for _ in desc + desc_children]).strip()
                else:
                    desc = desc[0].text.strip()

                self.log('{}. "{}": {}'.format(i, desc, href))

                # Получение содержимого гиста
                text = self.get_gist_content(browser, href)

                gist = Gist(href, desc, text)
                self.session.add(gist)
                self.session.commit()

            page += 1
            browser.open(ParserGists.URL_GIST_PAGE.format(self.login, page))

            if not browser.select(css_select_gist):
                break

        self.log("...На сбор потрачено времени %s...", time.clock() - t)

    def has_gist(self, url):
        # Проверка, что в базе гиста с таким url нет
        has = self.query.filter(Gist.url == url).exists()
        return self.session.query(literal(True)).filter(has).scalar()

    def get_gist_content(self, browser, url):
        # Переход на страницу гиста
        browser.open(url)
        text = ''
        for url_raw in browser.select('.file .file-header .file-actions a'):
            href = urljoin(browser.response.url, url_raw['href'])
            self.log('    {}'.format(href))

            browser.open(href)
            text += browser.response.text

        return text

