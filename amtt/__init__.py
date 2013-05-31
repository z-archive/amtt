# Copyright (C) 2013 Oleg Tsarev, oleg@oleg.sh
#
# This module is part of amtt and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

"""A.M. Test Task

This package contains sub-packages:

parser -- parse marketing data in XML format
db -- utility for connect to DBMS, (re)create database, (re)place data, read data from database
cli - command-line interface utility
"""

__version__='0.1'
__all__ = ['parser', 'db']
