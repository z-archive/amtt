# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.

import distutils.cmd
import unittest
import sys
import os


# Required for import
ROOT_PATH=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_PATH)

# Hack: http://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable
import builtins
setattr(builtins, "AMTT_TEST_MODE", True)
setattr(builtins, "AMTT_ROOT_PATH", ROOT_PATH)

# Import test modules
from tests import parser_test


class TestCommand(distutils.cmd.Command):
    description=("run unit-tests")
    user_options=[]


    def initialize_options(self):
        import logging
        #logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger('amtt.parser')
        logger.disabled=True
        pass


    def finalize_options(self):
        pass


    def run(self):
        # Configure test loader
        suite = unittest.TestSuite()        
        suite.addTest(unittest.TestLoader().loadTestsFromModule(parser_test))

        # Run tests
        unittest.TextTestRunner(verbosity=2).run(suite)


__all__ = ['TestCommand']
