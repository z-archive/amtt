#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import os
import functools
import psycopg2
import amtt.parser


import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger(__name__)

DROP = [
    'DROP TABLE IF EXISTS betfair',
    'DROP TABLE IF EXISTS event',
    'DROP TABLE IF EXISTS subevent',
    'DROP TABLE IF EXISTS selection'
]

MONEY_SCALE = 2
MONEY_PRECISION = (10 + MONEY_SCALE)


SELECTION_MONEY_COLUMN_NAMES = [
    "%s%s%s" % (prefix, medium, suffix)
    for suffix in map(str, range(1, 4))
    for prefix in ["back", "lay"]
    for medium in ["p", "s"]
]

CREATE = [
    # betfair
    '''CREATE TABLE betfair (
      id    serial,
      sport varchar(16),
      primary key(id)
    )''',

    # event
    '''CREATE TABLE event (
      betfair_id int,
      id         serial,
      name       varchar(128),
      date       date,
      foreign key(betfair_id)
        references betfair(id),
      primary key(betfair_id, id)
    )''',

    # subevent
    '''CREATE TABLE subevent (
      betfair_id int,
      event_id   int,
      id         int,
      title      varchar(64),
      date       date,
      time       time,
      totalAmountMatched int, -- I do not sure what it means
      foreign key(betfair_id, event_id)
        references event(betfair_id, id),
      primary key(betfair_id, event_id, id)
    )''',

    # selection
    '''CREATE TABLE selection(
      betfair_id  int,
      event_id    int,
      subevent_id int,
      id          int,
      name        varchar(64),
      %s,
      foreign key(betfair_id, event_id, subevent_id)
        references subevent(betfair_id, event_id, id),
      primary key(betfair_id, event_id, subevent_id, id, name)
    )''' % (',%s      ' % os.linesep).join(
        ["%s decimal(%s, %s)" % (name, MONEY_PRECISION, MONEY_SCALE)
         for name in SELECTION_MONEY_COLUMN_NAMES]),
]


def plist(count):
    return ', '.join(['$%s' % index for index in range(1, count+1)])


PREPARE_INSERT = [
    '''PREPARE betfair_insert AS INSERT INTO betfair(
        sport
    ) VALUES(%s) RETURNING id''' % plist(1),

    '''PREPARE event_insert AS INSERT INTO event(
         betfair_id,
         name,
         date
    ) VALUES(%s) RETURNING id''' % plist(3),

    '''PREPARE subevent_insert AS INSERT INTO subevent(
         betfair_id,
         event_id,
         id,
         title,
         date,
         time,
         totalAmountMatched
    ) VALUES(%s) RETURNING id''' % plist(7),

    '''PREPARE selection_insert AS INSERT INTO selection(
        betfair_id,
        event_id,
        subevent_id,
        id,
        name,
        %s
    ) VALUES(%s) RETURNING id''' % (
        (',%s        ' % os.linesep).join(SELECTION_MONEY_COLUMN_NAMES),
        plist(17))
]


def plist(count):
    return ', '.join(['%s'] * count)


INSERT = [
    '''EXECUTE betfair_insert(%s)''' % plist(1),
    '''EXECUTE event_insert(%s)''' % plist(3),
    '''EXECUTE subevent_insert(%s)''' % plist(7),
    '''EXECUTE selection_insert(%s)''' % plist(17),
]


STATS = [
    'SELECT count(*) as betfair_count  FROM betfair',
    'SELECT count(*) as event_count    FROM event',
    'SELECT count(*) as subevent_count FROM subevent',
    'SELECT count(*) as selection      FROM selection'
]


CLEAR = [
    'DELETE FROM betfair',
    'DELETE FROM event',
    'DELETE FROM subevent',
    'DELETE FROM selection',
]


QUERY_BETFAIR = 0
QUERY_EVENT = 1
QUERY_SUBEVENT = 2
QUERY_SELECTION = 3


def debug(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self._debug(method.__name__, *args, **kwargs)
        return method(self, *args, **kwargs)
    return wrapper


class StoreHandler(amtt.parser.UserHandler):
    def __init__(self, conn, full=False):
        self._full = full
        self._conn = conn
        self._cursor = None
        self._betfair = None
        self._event = None
        self._subevent = None
        self._queries = {}
        for (key, queries) in [('create', CREATE),
                               ('compile_inserts', PREPARE_INSERT),
                               ('stats', STATS),
                               ('clear', CLEAR)]:
            if full:
                self._queries[key] = queries
            else:
                self._queries[key] = queries[:2]
        self._queries['drop'] = reversed(DROP)
        self._queries['clear'] = reversed(self._queries['clear'])

    def _execute(self, queries):
        try:
            cursor = self._conn.cursor()
            for query in queries:
                logger.debug("executing '%s'", query)
                cursor.execute(query)
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    @debug
    def _insert(self, index, *args):
        query = INSERT[index]
        self._cursor.execute(query, args)
        return self._cursor.fetchone()[0]

    @debug
    def create_tables(self):
        self._execute(self._queries['create'])

    @debug
    def drop_tables(self):
        self._execute(self._queries['drop'])

    @debug
    def compile_inserts(self): 
        return self._execute(self._queries['compile_inserts'])

    @debug
    def clear(self):
        self._execute(self._queries['clear'])

    @debug
    def list_events(self):
        try:
            cursor = self._conn.cursor()
            query = "SELECT name FROM event"
            logger.debug("executing '%s'", query)
            cursor.execute(query)
            for row in cursor:
                yield row
        except BaseException:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @debug
    def stats(self):
        cursor = self._conn.cursor()
        # get query for event
        query = self._queries['stats'][1]
        cursor.execute(query)
        yield cursor
        self._conn.commit()
        cursor.close()

    def _log(self, level, method, *args, **kwargs):
        if logger.isEnabledFor(level):
            args = list(map(str,args))
            kwargs = ["%s=%s" % (name, str(kwargs[name])) for name in kwargs]
            message = "conn=%s, %s(%s)" % (self._conn,
                                           method,
                                           ", ".join(args + kwargs))
            logger.log(level, message)

    def _debug(self, method, *args, **kwargs):
        self._log(DEBUG, method, *args, **kwargs)

    @debug
    def start(self):
        assert(not self._cursor)
        self._cursor = self._conn.cursor()

    @debug
    def end(self):
        self._conn.commit()
        self._cursor.close()
        self._cursor = None

    @debug
    def startBetfair(self, *args):
        assert(self._cursor)
        self._betfair = self._insert(QUERY_BETFAIR, *args)

    @debug
    def startEvent(self, *args):
        assert(self._cursor)
        self._event = self._insert(QUERY_EVENT,
                                   self._betfair,
                                   *args)

    @debug
    def startSubEvent(self, *args):
        assert(self._cursor)
        assert(self._full)
        self._subevent = self._insert(QUERY_SUBEVENT,
                                      self._betfair,
                                      self._event,
                                      *args)

    @debug
    def selection(self, *args):
        assert(self._cursor)
        assert(self._full)
        self._insert(QUERY_SELECTION,
                     self._betfair,
                     self._event,
                     self._subevent,
                     *args)


    @debug
    def endBetfair(self):
        self._betfair = None
        pass

    @debug
    def endEvent(self):
        self._event = None

    @debug
    def endSubEvent(self):
        assert(self._full)
        self._subevent = None


__all__ = ['StoreHandler']
