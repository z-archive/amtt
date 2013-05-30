# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import functools
import unittest
import decimal
import xml.sax
from datetime import date, time
import os
from amtt.parser import *

# Hack: http://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable
import builtins
ROOT_PATH=getattr(builtins, 'AMTT_ROOT_PATH')

class TestProblem(unittest.TestCase):
    def setUp(self):
        self.parser = xml.sax.make_parser()
        self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
        self.message = "Line: 1 Column: None Problem: %s"


    def test_Problem(self):
        with self.assertRaisesRegex(NotImplementedError, 'Problem.problem()'):
            problem = Problem(self.locator)
            str(problem)


    def test_UnExpectedTag(self):
        problem = UnExpectedTag(self.locator, "b", "a")
        self.assertEqual(str(problem), self.message % "unexpected tag 'b', expected 'a'")
        
                
    def test_BrokenAttributes(self):
        problem = BrokenAttributes(self.locator, ["a", "b"], ["c", "d"])
        self.assertEqual(str(problem), self.message % "broken attributes, unexpected=[a, b], missed=[c, d]" )
        
                
    def test_AttributeTypeError(self):
        problem = AttributeTypeError(self.locator, "somename", "sometype", "somevalue")
        self.assertEqual(str(problem), self.message % "parse attribute 'somename' (expected type: 'sometype') invalid value 'somevalue'" )

class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = xml.sax.make_parser()
        self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
        self.message = "Line: 1 Column: None Problem: %s"
        self.fail = self.message % "parse attribute 'name' \(expected type: '%s'\) invalid value 'fail'"


    def _invalid(self, create, source):
        parser = create("name")(self.locator)
        fail =  self.fail % parser.__class__.__name__
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
        self._correct(Parser.date, "13/09/2013", date(2013,9,13))
        
                
class TestParserTime(TestParser):    
    def test_invalid(self):
        self._invalid(Parser.time, "fail")
        
                
    def test_correct(self):
        self._correct(Parser.time, "12:43", time(12,43))


class DCH(UserHandler):
    def __init__(self):
        self.result = []
        # we can generate methods dynamically, but I prefer straigforward code here
        # dynamic generation required when method(s) (name(s)) depend from (runtime) data


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
        attrs= xml.sax.xmlreader.AttributesImpl(attrs)
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
        with self.assertRaisesRegex(BrokenAttributes, self.message % message):
            parser.open(attrs)
        self.assertEqual(self.dch.result, [])


    def test_correct(self):
        attrs = { 'sport': 'value' }
        expected = [('start', 'betfair', ('value',)), ('end', 'betfair', None)]
        self._correct(Tag.betfair(), expected, attrs=attrs)

    
    def test_broken_attributes_one(self):
        attrs = { 'sport': 'value', 'bad': 'value2' }
        self._invalid(Tag.betfair(), "broken attributes, unexpected=\[bad\], missed=\[\]", attrs=attrs)


    def test_broken_attributes_two(self):
        attrs = { 'bad': 'value2' }
        self._invalid(Tag.betfair(), "broken attributes, unexpected=\[bad\], missed=\[sport\]", attrs=attrs)


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
        with self.assertRaisesRegex(UnExpectedTag, self.message % "unexpected tag 'bad', expected 'betfair'"):
            ech.startElement("bad", attrs={})
        ech.startElement("betfair", attrs={'sport': 'value'})
        with self.assertRaisesRegex(UnExpectedTag, self.message % "unexpected tag 'betfair', expected 'event'"):
            ech.startElement("betfair", attrs={'sport': 'value'})
        ech.endElement('betfair')

class TestExpatContentHandler(unittest.TestCase):
    def setUp(self):
        self.parser = xml.sax.make_parser()
        self.locator = xml.sax.expatreader.ExpatLocator(self.parser)
        self.dch = DCH()
        self.ech = ExpatContentHandler(self.locator, self.dch)
        self.parser.setContentHandler(self.ech)


    def test_parse(self):
        TEST_FILE_NAME=os.path.join(ROOT_PATH, "tests", "test.xml")
        self.parser.parse(TEST_FILE_NAME)
