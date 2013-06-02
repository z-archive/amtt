#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import argparse
import sys
import errno
import psycopg2
from amtt.parser import make_parser
from amtt.db import StoreHandler
import logging

def create_arg_parser():
    result = argparse.ArgumentParser(
        description='Parse feed and store data to database.')
    result.add_argument('--debug',
                        help='debug logging output',
                        action='store_true')
    result.add_argument('--database', 
                        required=True,
                        help="PostgreSQL database name. It should be created before")
    subparsers = result.add_subparsers(title='action',
                                       dest='action')
    subparsers.add_parser('prepare', help="(re)create tables in database")
    subparsers.add_parser('clear', help="clear tables")
    parse = subparsers.add_parser('parse', help="parse feed")
    parse.add_argument('url',
                       nargs='?',
                       help="URL to feed with data",
                       default='http://www.betfair.com/partner/marketData_loader.asp?fa=ss&id=1&SportName=Soccer&Type=BL')
    subparsers.add_parser('list', help="list events from database")
    subparsers.add_parser('stats')    
    return result

if __name__ == '__main__':
    arg_parser = create_arg_parser()
    args = arg_parser.parse_args()

    if args.action is None:
        print("Please specify command. See help for details", file=sys.stderr)
        sys.exit(-1)

    if args.debug:
        logging.getLogger('amtt.parser').setLevel(logging.INFO)
        logging.getLogger('amtt.db').setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.getLogger('amtt.parser').setLevel(logging.INFO)
        logging.getLogger('amtt.db').setLevel(logging.INFO)
        logging.basicConfig(level=logging.INFO)

    print("Connecting to database...", file=sys.stderr)

    try:
        connection = psycopg2.connect(database=args.database)
        handler = StoreHandler(connection, full=False)
    except psycopg2.OperationalError as e:
        print(e, file=sys.stderr)
        sys.exit(-1)

    if args.action == 'prepare':

        print("Drop tables from %s..." % args.database, file=sys.stderr)
        handler.drop_tables()
        print("Create tables in %s..." % args.database, file=sys.stderr)
        handler.create_tables()

    elif args.action == 'clear':
        
        print("Clear tables from  database %s..." % args.database, file=sys.stderr)
        handler.clear()

    elif args.action == 'parse':

        print("Compile insert queries...", file=sys.stderr)
        handler.compile_inserts()
        parser = make_parser(handler)

        print("Parsing...")
        parser.parse(args.url)

    elif args.action == 'stats':
        import os
        print(os.linesep.join(os.linesep.join("\t".join(map(str,line))
                                              for line in query_result)
                              for query_result in handler.stats()))

    elif args.action == 'list':
        try:
            for row in handler.list_events():
                print(row[0])
        except IOError as e:
            if e.errno == errno.EPIPE:
                pass
            else:
                raise
