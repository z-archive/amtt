# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""A.M. Test Task - Parser

Parse marking data in XML format

You should create define handler class:

    import amtt.parser

    class UserHandler(amtt.parser.UserHandler):
        def startBetfair(self, sport):
            # your implementation here
        def startEvent(self, name, date):
            # your implementation here
        def startSubEvent(self, id, title, date, time, totalAmountMathced):
            # your implementation here
        def selection(self, id, name, *money):
            '''
            *money is
                backp1, backs1, layp1, lays1,
                backp2, backs2, layp2, lays2,
                backp3, backs3, layp3, lays3
            '''
            # your implementation here
        def endBetfair(self):
            # your implementation here
        def endEvent(self):
            # your implementation here
        def endSubEvent(self):
            # your implementation here

Example of usage (simple):

    user_handler = UserHandler()
    parser = make_parser(user_handler)
    parser.parse('/path/to/xml')

Example of usage (flexible):

    import xml.sax
    import xml.sax.expatreader
    import amtt.parser

    parser = xml.sax.make_parser()
    locator = xml.sax.expatreader.ExpatLocator(parser)
    user_handler = UserHandler()
    content_handler = amtt.parser.ExpatContentHandler(locator, user_handler)
    parser.setContentHandler(content_handler)
    parser.parser('/path/to/xml/file')
"""
import xml.sax.handler
import xml.sax.xmlreader
import decimal
from datetime import datetime


import logging
logger = logging.getLogger(__name__)


class Problem(Exception):
    ''' Super class for all possible problems'''
    def __init__(self, locator):
        self.line = locator.getLineNumber()
        self.column = locator.getColumnNumber()


    def __str__(self):
        return "Line: %s Column: %s Problem: %s" % (self.line, self.column, self._problem())


    def _problem(self):
        ''' description of the problem '''
        e = NotImplementedError("%s._problem()" % self.__class__.__name__)
        logger.critical(e)
        raise e


class UnExpectedTag(Problem):
    ''' Unexpected tag in XML document '''
    def __init__(self, locator, name, expected):
        super().__init__(locator)
        self.name = name
        self.expected = expected


    def _problem(self):
        return "unexpected tag '%s', expected '%s'" % (self.name, self.expected)


class BrokenAttributes(Problem):
    ''' Unexpected or missed attributes of tag in XML document '''
    def __init__(self, locator, unexpected, missed):
        super().__init__(locator)
        self.unexpected = unexpected
        self.missed = missed


    def _problem(self):
        unexpected = ", ".join(self.unexpected)
        missed = ", ".join(self.missed)
        return "broken attributes, unexpected=[%s], missed=[%s]" % (unexpected, missed)


class AttributeTypeError(Problem):
    ''' Invalid value type for attribute '''
    def __init__(self, locator, name, type_name, value):
        super().__init__(locator)
        self.name = name
        self.type_name = type_name
        self.value = value
    
    
    def _problem(self):
        message = "parse attribute '%s' (expected type: '%s') invalid value '%s'"
        return message % (self.name, self.type_name, self.value)


class UserHandler(object):
    '''' You should create sub-class of UserHandler for process data from XML document '''
    def __not_implemented(self, name_and_signature):
        e = NotImplementedError("%s.%s" % (self.__class__.__name__, name_and_signature))
        logger.critical(e)
        raise e
    

    def startBetfair(self, sport):
        self.__not_implemented('startBetfair(sport)')


    def startEvent(self, name, date):
        self.__not_implemented('startEvent(name, date)')


    def startSubEvent(self, id, title, date, time, totalAmountMathced):
        self.__not_implemented('startSubEvent(id, title, date, time, totalAmountMathced)')


    def selection(self, id, name, *money):
        '''
        *money is
            backp1, backs1, layp1, lays1,
            backp2, backs2, layp2, lays2,
            backp3, backs3, layp3, lays3
        '''
        self.__not_implemented('startSubEvent(id, name, *money)')

        
    def endBetfair(self):
        self.__not_implemented('endBetfair()')


    def endEvent(self):
        self.__not_implemented('endEvent()')


    def endSubEvent(self):
        self.__not_implemented('endSubEvent')


class Parser(object):
    class Attribute(object):
        def __init__(self, locator, name):
            super().__init__()
            self._locator = locator
            self._name = name

        @property
        def name(self):
            return self._name


        def parse(self, value):
            try:
                logger.debug("attribute name=%s type=%s attempt to parse '%s'", 
                             self.name,
                             self.__class__.__name__,
                             value)
                return self._parse(value)
            except (ValueError, decimal.InvalidOperation):
                e = AttributeTypeError(self._locator, 
                                       self._name, 
                                       self.__class__.__name__,
                                       value)
                logger.error(e)
                raise e

        def _parse(self, value):
            e = NotImplementedError("%s.parse(value)" % (self.__class__.__name__))
            logger.critical(e)
            raise e

    
    class String(Attribute):
        def _parse(self, value):
            return value


    class Int(Attribute):
        def _parse(self, value):
            return int(value)

    
    class Money(Attribute):
        def _parse(self, value):
            # incompatible with Python 2.x
            return decimal.Decimal(value)


    class Date(Attribute):
        def _parse(self, value):
            return datetime.strptime(value, "%d/%m/%Y").date()


    class Time(Attribute):
        def _parse(self, value):
            return datetime.strptime(value, "%H:%M").time()


    @staticmethod
    def _create(c, name):
        def result(locator):
            return c(locator, name)
        return result


    @staticmethod
    def string(name):
        return Parser._create(Parser.String, name)


    @staticmethod
    def int(name):
        return Parser._create(Parser.Int, name)


    @staticmethod
    def money(name):
        return Parser._create(Parser.Money, name)


    @staticmethod
    def date(name):
        return Parser._create(Parser.Date, name)


    @staticmethod
    def time(name):
        return Parser._create(Parser.Time, name)


class Tag(object):
    def __init__(self, locator, open, close, scheme):
        super().__init__()
        self._locator = locator
        self._open = open
        self.close = close
        self._scheme = [ascheme(locator) for ascheme in scheme]


    def _broken_names_report(self, attrs):
        expected = set(ascheme.name for ascheme in self._scheme)
        actual = set(attrs.getNames())
        missed = list(expected.difference(actual))
        unexpected = list(actual.difference(expected))
        e = BrokenAttributes(self._locator, unexpected, missed)
        logger.error(e)
        raise e


    def _verify_names(self, attrs):
        if len(self._scheme) != len(attrs):
            self._broken_names_report(attrs)
        for ascheme in self._scheme:
            if not ascheme.name in attrs:
                self._broken_names_report(attrs)

    
    def open(self, attrs):
        self._verify_names(attrs)
        result = []
        for ascheme in self._scheme:
            value = attrs[ascheme.name]
            parsed = ascheme.parse(value)
            result.append(parsed)
        self._open(*result)

        
    @staticmethod
    def betfair():
        scheme = [
            Parser.string("sport")
        ]
        def create(locator, data_handler):
            return Tag(locator, 
                       data_handler.startBetfair,
                       data_handler.endBetfair,
                       scheme)
        return create

    @staticmethod
    def event():
        scheme = [
            Parser.string("name"),
            Parser.date("date")
        ]
        def create(locator, data_handler):
            return Tag(locator, 
                       data_handler.startEvent,
                       data_handler.endEvent,
                       scheme)
        return create

    
    @staticmethod
    def subEvent():
        scheme = [
            Parser.int("id"),
            Parser.string("title"),
            Parser.date("date"),
            Parser.time("time"),
            Parser.int("TotalAmountMatched")
        ]
        def create(locator, data_handler):
            return Tag(locator, 
                       data_handler.startSubEvent,
                       data_handler.endSubEvent,
                       scheme)
        return create


    @staticmethod
    def selection():
        scheme = [
            Parser.int("id"),
            Parser.string("name")
        ]
        for suffix in map(str, range(1,4)):
            for prefix in ["back", "lay"]:
                for medium in ["p", "s"]:
                    name = "%s%s%s" % (prefix, medium, suffix)
                    scheme.append(Parser.money(name))
        def create(locator, data_handler):
            return Tag(locator, 
                       data_handler.selection,
                       lambda: None,
                       scheme)
        return create


MODE_ROOT      = 0
MODE_BETFAIR   = 1
MODE_EVENT     = 2
MODE_SUBEVENT  = 3
MODE_SELECTION = 4
MODE_LEAF      = 4

TAG_EXPECTED = [None, 'betfair',     'event',     'subevent',     'selection']
TAG_SCHEME =   [None, Tag.betfair(), Tag.event(), Tag.subEvent(), Tag.selection()]

class ExpatContentHandler(xml.sax.handler.ContentHandler):
    '''
    Parses XML with fixed (defined, known) structure.
    Member _mode represents actual tree level and used for document scheme verification.

    Example of document:
        (root)                      # MODE_NONE      (== MODE_ROOT)
            <betfair>               # MODE_BETFAIR
                <event>             # MODE_EVENT
                    <subevent>      # MODE_SUBEVENT
                        <selection> # MODE_SELECTION (== MODE_LEAF)
    '''
    def __init__(self, locator, data_handler):
        '''locator is instance of xml.sax.xmlreader.Locator
        data_handler is instance of UserHandler'''
        super().__init__()
        super().setDocumentLocator(locator)
        self._locator = locator
        self._mode = MODE_ROOT
        def c(create):
            if create is None:
                return None
            else:
                return create(locator, data_handler)
        self._parser = list(map(c, TAG_SCHEME))


    def startDocument(self):
        logger.debug("startDocument, mode=%s", self._mode)
        assert(self._mode == MODE_ROOT)
        self._mode = MODE_ROOT+1


    def endDocument(self):
        logger.debug("endDocument, mode=%s", self._mode)
        assert(self._mode == MODE_ROOT+1)
        self._mode = MODE_ROOT


    def startElement(self, name, attrs):
        logger.debug("startElement(%s), mode=%s", name, self._mode)
        expected = TAG_EXPECTED[self._mode]
        if (expected != name):
            e = UnExpectedTag(self._locator, name, expected)
            logger.error(e)
            raise e
        self._parser[self._mode].open(attrs)
        self._mode += 1


    def endElement(self, name):
        logger.debug("endElement(%s), mode=%s", name, self._mode)
        # I rely to Expat parser about open/close tags сoncord
        assert(TAG_EXPECTED[self._mode-1] == name)
        self._mode -= 1
        self._parser[self._mode].close()

def make_parser(user_handler):
    parser = xml.sax.make_parser()
    locator = xml.sax.expatreader.ExpatLocator(parser)
    content_handler = ExpatContentHandler(locator, user_handler)
    parser.setContentHandler(content_handler)
    return parser


__all__ = [
    'Problem',
    'UnExpectedTag',
    'BrokenAttributes',
    'AttributeTypeError',
    'UserHandler', 
    'ExpatContentHandler',
    'make_parser'
]


# Hack: http://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable
# For unit-tests we should import more
import builtins
if getattr(builtins, 'AMTT_TEST_MODE', False):
    __all__ += ['Tag', 'Parser']
