# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import os
import psycopg2
from amtt import parser


import logging
logger = logging.getLogger(__name__)


def drop_database_query():
    yield 'DROP DATABASE IF EXISTS amtt'


def create_database_query():
    yield 'CREATE DATABASE amtt'


def drop_queries():
    yield 'DROP TABLE IF EXISTS betfair'
    yield 'DROP TABLE IF EXISTS event'
    yield 'DROP TABLE IF EXISTS subevent'
    yield 'DROP TABLE IF EXISTS selection'


MONEY_SCALE=(2)
MONEY_PRECISION=(10 + MONEY_SCALE)


SELECTION_MONEY_COLUMN_NAMES = [
    "%s%s%s" % (prefix, medium, suffix)
    for suffix in map(str, range(1,4))
    for prefix in ["back", "lay"]
    for medium in ["p", "s"]
]


def create_queries():
    # betfair
    yield '''CREATE TABLE betfair (
      id    int         serial primary key
    , sport varchar(16)
    )'''

    # event
    yield '''CREATE TABLE event (
      id         int           primary key
    , betfair_id int           references betfair(id)
    , name       varchar('32')
    , date       date
    )'''
    yield 'CREATE UNIQUE INDEX ON event(betfair_id)'

    # subevent
    yield '''CREATE TABLE subevent (
      id                 int           primary key
    , event_id           int           references event(id)
    , title              varchar('32')
    , date               date
    , time               time
    , totalAmountMatched int           -- I do not sure what it means
    )'''
    yield 'CREATE UNIQUE INDEX ON subevent(event_id)'

    # selection
    yield '''CREATE TABLE selection(
      id             int         primary key
    , subevent_id    int         references subevent(id)
    , name           varchar(32)
    , %s
    )''' % ('%s    , ' % os.linesep).join([
        "%s decimal(%s, %s)" % (name, MONEY_PRECISION, MONEY_SCALE)
        for name in SELECTION_MONEY_COLUMN_NAMES
    ])
    yield 'CREATE UNIQUE INDEX ON subevent(subevent_id)'


def prepare_insert_queries():
    def plist(count):
        return ', '.join(['$%s' % index for index in range(1,count+1)])

    yield '''PREPARE betfair_insert AS INSERT INTO betfair(
          sport
    ) VALUES(%s)''' % plist(1)

    yield '''PREPARE event_insert AS INSERT INTO event(
          id
        , betfair_id
        , name, date
    ) VALUES(%s)''' % plist(4)

    yield '''PREPARE subevent_insert AS INSERT INTO subevent(
          id
        , event_id
        , title
        , date
        , time
        , totalAmountMatched
    ) VALUES(%s)''' % plist(6)

    yield '''PREPARE selection_insert AS INSERT INTO selection(
          id
        , subevent_id
        , name
        , %s
    ) VALUES(%s)''' % (
          ('%s    , ' % os.linesep).join(SELECTION_MONEY_COLUMN_NAMES)
        , plist(15)
    )


def insert_queries():
    def plist(count):
        return ', '.join(['%%%s' % index for index in range(1,count+1)])
    yield '''EXECUTE betfair_insert   (%s)''' % plist(1)
    yield '''EXECUTE event_insert     (%s)''' % plist(4)
    yield '''EXECUTE subevent_insert  (%s)''' % plist(6)
    yield '''EXECUTE selection_insert (%s)''' % plist(15)


class StoreHandler(parser.UserHandler):
    def __init__(self):
        (  self._betfair_query
         , self._event_query
         , self._subevent_query
         , self._selection_query) = tuple(insert_queries)


    def setConnecton(self, connection):
        self._connection = connection
        self._cursor = connection.cursor()


    def startBetfair(self, *args):
        self._cursor.execute(self._betfair_query, tuple(args))
        self._betfair= int(self._cursor.fetchone()[0])


    def startEvent(self, *args):
        self._cursor.execute(self._event_query, tuple(args))
        self._event= int(self._cursor.fetchone()[0])


    def startSubEvent(self, *args):
        self._cursor.execute(self._subevent_query, tuple(args))
        self._event= int(self._cursor.fetchone()[0])


    def selection(self, *args):
        self._cursor.execute(self._selection_query, tuple(args))


    def endBetfair(self):
        self._connection.commit()
        self._cursor.close()


    def endEvent(self):
        pass


    def endSubEvent(self):
        pass

def execqs(conn, query_sequence, description):
    try:
        print(conn)
        print(conn.cursor)
        c = conn.сursor()
        print (c)
        logger.info("begin %s", description)
        for query in query_sequence:
            logger.debug("%s => executing %s" % (description, query))
            cursor.execqs(query)
            if logger.isEnabledFor(logging.DEBUG):
                for line_number, record in enumerate(cursor):
                    logger.debug("\t%s\t%s", line_number, record)
        logger.info("commit %s" % description)
        conn.commit()
        cursor.close()
    except BaseException as e:
        logger.error(e)
        logger.info("rollback %s" % description)
        conn.rollback()
        raise


def create_database(conn):
    print(conn)
    execqs(conn, create_database_query(), "create database")


def drop_database(conn):
    print(conn)
    execqs(conn, drop_database_query(), "drop database")


def create_tables(conn):
    execqs(conn, drop_queries(), "create tables")


def drop_tables(conn):
    execqs(conn, drop_queries(), "create tables")


def prepare_inserts(conn):
    execqs(conn, prepare_insert_queries(), "prepare (compile) insert queries")
