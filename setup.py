#!/usr/bin/env python
# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

from distutils.core import setup
from tests import TestCommand

def get_version():
    """parse _version for version number instead of importing the file, see http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
"""
    INIT_LINES = open('amtt/__init__.py').readlines()
    VERSION_STRING_LINE = [line for line in INIT_LINES if '__version__' in line][0]
    return VERSION_STRING_LINE.split('=')[1].split("'")[1]

NAME="amtt"
VERSION=get_version()
DESCRIPTION="A. M. Test Task"
LONG_DESCRIPTION=open("README").read() + "\n\n" + open("HISTORY").read()
AUTHOR="Oleg Tsarev"
AUTHOR_EMAIL="oleg@oleg.sh"
URL="https://github.com/zamotivator/amtt"
PACKAGES=["amtt"]
TEST_SUITE="tests"
CMD_CLASS={'test': TestCommand}
CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "License :: OSI Approved :: BSD License",
    "Intended Audience :: Information Technology",
    "Natural Language :: English",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.3",
    "Topic :: Database",
    "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    "Topic :: Text Processing :: Markup :: XML"
]
setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    url = URL,
    packages = PACKAGES,
    cmdclass = CMD_CLASS,
    classifiers = CLASSIFIERS
)
