#!/usr/bin/env python


import logging
logging.basicConfig(leve=logging.INFO)
logging.getLogger('amtt.parser').setLevel(logging.ERROR)
logging.getLogger('amtt.db').setLevel(logging.DEBUG)

from amtt import parser
from amtt.db import *

import psycopg2
conn = psycopg2.connect(database="postgres")
drop_database(conn)
create_database(conn)
conn = psycopg2.connect(database="amtt")
db.create_tables(conn)
db.prepare_inserts(conn)

#handler = db.StoreHandler()
#handler.setConnection(conn)
#parser = parser.make_parser(handler)
#parser
