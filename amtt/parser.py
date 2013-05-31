#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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
from datetime import date, time, datetime


class Problem(Exception):
    ''' Super class for all possible problems'''
    def __init__(self, locator):
        self.line = locator.getLineNumber()
        self.column = locator.getColumnNumber()

    def __str__(self):
        message = "Line: %s Column: %s Problem: %s"
        return message % (self.line, self.column, self._problem())

    def _problem(self):
        ''' description of the problem '''
        raise NotImplementedError("%s._problem()" % self.__class__.__name__)


class UnExpectedTag(Problem):
    ''' Unexpected tag in XML document '''
    def __init__(self, locator, name, expected):
        super().__init__(locator)
        self.name = name
        self.expected = expected

    def _problem(self):
        message = "unexpected tag '%s', expected '%s'"
        return message % (self.name, self.expected)


class BrokenAttributes(Problem):
    ''' Unexpected or missed attributes of tag in XML document '''
    def __init__(self, locator, unexpected, missed):
        super().__init__(locator)
        self.unexpected = unexpected
        self.missed = missed

    def _problem(self):
        unexpected = ", ".join(self.unexpected)
        missed = ", ".join(self.missed)
        message = "broken attributes, unexpected=[%s], missed=[%s]"
        return message % (unexpected, missed)


class AttributeTypeError(Problem):
    ''' Invalid value type for attribute '''
    def __init__(self, locator, name, type_name, value):
        super().__init__(locator)
        self.name = name
        self.type_name = type_name
        self.value = value

    def _problem(self):
        message = "parse attribute '%s' (expected type: '%s') " \
                  "invalid value '%s'"
        return message % (self.name, self.type_name, self.value)


class UserHandler(object):
    ''' You should create sub-class of UserHandler
    for process data from XML document
    '''
    def __not_implemented(self, name_and_signature):
        message = "%s.%s" % (self.__class__.__name__, name_and_signature)
        raise NotImplementedError(message)

    def startBetfair(self, sport):
        self.__not_implemented('startBetfair(sport)')

    def startEvent(self, name, date):
        self.__not_implemented('startEvent(name, date)')

    def startSubEvent(self, id, title, date, time, totalAmountMathced):
        signature = 'startSubEvent(id, title, date, time, totalAmountMathced)'
        self.__not_implemented(signature)

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
                return self._parse(value)
            except (ValueError, decimal.InvalidOperation):
                raise AttributeTypeError(self._locator,
                                         self._name,
                                         self.__class__.__name__,
                                         value)

        def _parse(self, value):
            message = "%s.parse(value)" % (self.__class__.__name__)
            raise NotImplementedError(message)

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
        raise BrokenAttributes(self._locator, unexpected, missed)

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
        for suffix in map(str, range(1, 4)):
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


MODE_ROOT = 0
MODE_BETFAIR = 1
MODE_EVENT = 2
MODE_SUBEVENT = 3
MODE_SELECTION = 4
MODE_LEAF = 4

TAG_EXPECTED = [None,
                'betfair',
                'event',
                'subevent',
                'selection']
TAG_SCHEME = [None,
              Tag.betfair(),
              Tag.event(),
              Tag.subEvent(),
              Tag.selection()]


class ExpatContentHandler(xml.sax.handler.ContentHandler):
    '''
    Parses XML with fixed (defined, known) structure.
    Member _mode represents actual tree level and
    used for document scheme verification.

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
        assert(self._mode == MODE_ROOT)
        self._mode = MODE_ROOT+1

    def endDocument(self):
        assert(self._mode == MODE_ROOT+1)
        self._mode = MODE_ROOT

    def startElement(self, name, attrs):
        expected = TAG_EXPECTED[self._mode]
        if (expected != name):
            raise UnExpectedTag(self._locator, name, expected)
        self._parser[self._mode].open(attrs)
        self._mode += 1

    def endElement(self, name):
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


def get_test_suite_list():
    import functools
    import unittest

    class TestProblem(unittest.TestCase):
        def setUp(self):
            self.parser = xml.sax.make_parser()
            self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
            self.message = "Line: 1 Column: None Problem: %s"

        def test_Problem(self):
            with self.assertRaisesRegex(NotImplementedError,
                                        'Problem._problem()'):
                problem = Problem(self.locator)
                str(problem)

        def test_UnExpectedTag(self):
            problem = UnExpectedTag(self.locator, "b", "a")
            expected = "unexpected tag 'b', expected 'a'"
            self.assertEqual(str(problem), self.message % expected)

        def test_BrokenAttributes(self):
            problem = BrokenAttributes(self.locator, ["a", "b"], ["c", "d"])
            expected = "broken attributes, unexpected=[a, b], missed=[c, d]"
            self.assertEqual(str(problem), self.message % expected)

        def test_AttributeTypeError(self):
            problem = AttributeTypeError(self.locator,
                                         "somename",
                                         "sometype",
                                         "somevalue")
            expected = "parse attribute 'somename' " \
                       "(expected type: 'sometype') " \
                       "invalid value 'somevalue'"
            self.assertEqual(str(problem), self.message % expected)

    class TestParser(unittest.TestCase):
        def setUp(self):
            self.parser = xml.sax.make_parser()
            self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
            self.message = "Line: 1 Column: None Problem: %s"
            fail = "parse attribute 'name' \(expected type: '%s'\) " \
                   "invalid value 'fail'"
            self.fail = self.message % fail

        def _invalid(self, create, source):
            parser = create("name")(self.locator)
            fail = self.fail % parser.__class__.__name__
            with self.assertRaisesRegex(AttributeTypeError, fail):
                parser.parse(source)

        def _correct(self, create, source, expected):
            parser = create("name")(self.locator)
            actual = parser.parse(source)
            self.assertEqual(actual, expected)

    class TestParserInt(TestParser):
        def test_invalid(self):
            self._invalid(Parser.int, "fail")

        def test_correct(self):
            self._correct(Parser.int, "123", 123)

    class TestParserString(TestParser):
        def test_correct(self):
            self._correct(Parser.string, "some string", "some string")

    class TestParserMoney(TestParser):
        def test_invalid(self):
            self._invalid(Parser.money, "fail")

        def test_correct(self):
            self._correct(Parser.money, "123.54", decimal.Decimal('123.54'))

    class TestParserDate(TestParser):
        def test_invalid(self):
            self._invalid(Parser.date, "fail")

        def test_correct(self):
            self._correct(Parser.date, "13/09/2013", date(2013, 9, 13))

    class TestParserTime(TestParser):
        def test_invalid(self):
            self._invalid(Parser.time, "fail")

        def test_correct(self):
            self._correct(Parser.time, "12:43", time(12, 43))

    class DCH(UserHandler):
        def __init__(self):
            self.result = []

        def startBetfair(self, *args):
            self.result.append(("start", "betfair", args))

        def startEvent(self, *args):
            self.result.append(("start", "event", args))

        def startSubEvent(self, *args):
            self.result.append(("start", "subEvent", args))

        def selection(self, *args):
            self.result.append(("start", "selection", args))

        def endBetfair(self):
            self.result.append(("end", "betfair", None))

        def endEvent(self):
            self.result.append(("end", "event", None))

        def endSubEvent(self):
            self.result.append(("end", "subEvent", None))

    def convertAttrs(method):
        @functools.wraps(method)
        def wrapper(self, *args, attrs=None):
            attrs = xml.sax.xmlreader.AttributesImpl(attrs)
            return method(self, *args, attrs=attrs)
        return wrapper

    class TestTag(unittest.TestCase):
        def setUp(self):
            self.parser = xml.sax.make_parser()
            self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
            self.dch = DCH()
            self.message = "Line: 1 Column: None Problem: %s"

        @convertAttrs
        def _correct(self, create, expected, attrs=None):
            parser = create(self.locator, self.dch)
            parser.open(attrs)
            parser.close()

            def getNames():
                return attrs.keys()

            setattr(attrs, 'getNames', getNames)
            actual = self.dch.result
            self.assertEqual(actual, expected)

        @convertAttrs
        def _invalid(self, create, message, attrs=None):
            parser = create(self.locator, self.dch)
            with self.assertRaisesRegex(BrokenAttributes,
                                        self.message % message):
                parser.open(attrs)
            self.assertEqual(self.dch.result, [])

        def test_correct(self):
            attrs = {'sport': 'value'}
            expected = [('start', 'betfair', ('value',)),
                        ('end', 'betfair', None)]
            self._correct(Tag.betfair(), expected, attrs=attrs)

        def test_broken_attributes_one(self):
            attrs = {'sport': 'value', 'bad': 'value2'}
            expected = "broken attributes, unexpected=\[bad\], missed=\[\]"
            self._invalid(Tag.betfair(), expected, attrs=attrs)

        def test_broken_attributes_two(self):
            attrs = {'bad': 'value2'}
            expected = "broken attributes, " \
                       "unexpected=\[bad\], " \
                       "missed=\[sport\]"
            self._invalid(Tag.betfair(), expected, attrs=attrs)

    class ECH(ExpatContentHandler):
        @convertAttrs
        def startElement(self, name, attrs=None):
            return super().startElement(name, attrs)

    class TestExpatContentHandlerAPI(unittest.TestCase):
        def setUp(self):
            self.parser = xml.sax.make_parser()
            self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
            self.dch = DCH()
            self.message = "Line: 1 Column: None Problem: %s"

        @property
        def ech(self):
            return ECH(self.locator, self.dch)

        def test_create(self):
            self.assertIsInstance(self.ech, ExpatContentHandler)

        def test_empty(self):
            ech = self.ech
            ech.startDocument()
            ech.endDocument()

        def test_double_start(self):
            ech = self.ech
            ech.startDocument()
            with self.assertRaises(AssertionError):
                ech.startDocument()

        def test_double_start(self):
            ech = self.ech
            with self.assertRaises(AssertionError):
                ech.endDocument()
            ech.startDocument()
            ech.endDocument()
            with self.assertRaises(AssertionError):
                ech.endDocument()

        def test_parse(self):
            ech = self.ech
            ech.startDocument()
            expected = self.message % "unexpected tag 'bad', " \
                                      "expected 'betfair'"
            with self.assertRaisesRegex(UnExpectedTag, expected):
                ech.startElement("bad", attrs={})
            ech.startElement("betfair", attrs={'sport': 'value'})
            expected = self.message % "unexpected tag 'betfair', " \
                                      "expected 'event'"
            with self.assertRaisesRegex(UnExpectedTag, expected):
                ech.startElement("betfair", attrs={'sport': 'value'})
            ech.endElement('betfair')

    class TestExpatContentHandler(unittest.TestCase):
        def setUp(self):
            self.dch = DCH()
            self.parser = make_parser(self.dch)

        def test_parse(self):
            from os.path import join, dirname, abspath
            TEST_FILE_NAME = abspath(join(dirname(__file__), "test.xml"))
            self.parser.parse(TEST_FILE_NAME)

    loader = unittest.TestLoader()
    return [loader.loadTestsFromTestCase(test)
            for test in [TestProblem,
                         TestParser,
                         TestParserInt,
                         TestParserString,
                         TestParserMoney,
                         TestParserDate,
                         TestParserTime,
                         TestTag,
                         TestExpatContentHandlerAPI,
                         TestExpatContentHandler]]


__all__ = [
    'Problem',
    'UnExpectedTag',
    'BrokenAttributes',
    'AttributeTypeError',
    'UserHandler',
    'ExpatContentHandler',
    'make_parser',
    'get_test_suite_list'
]
