#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.


import distutils.cmd


class TestCommand(distutils.cmd.Command):
    description = ("run unit-tests")
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Required for import
        import sys
        from os.path import abspath, join, dirname
        ROOT_PATH = abspath(join(dirname(__file__), ".."))
        sys.path.append(ROOT_PATH)

        import unittest
        import amtt.parser

        run = unittest.TestSuite()
        for suite in amtt.parser.get_test_suite_list():
            run.addTest(suite)

        unittest.TextTestRunner(verbosity=2).run(run)


__all__ = ['TestCommand']
