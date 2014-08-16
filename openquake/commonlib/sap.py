#  -*- coding: utf-8 -*-
#  vim: tabstop=4 shiftwidth=4 softtabstop=4

#  Copyright (c) 2014, GEM Foundation

#  OpenQuake is free software: you can redistribute it and/or modify it
#  under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  OpenQuake is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU Affero General Public License
#  along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.

"""
Here is a minimal example of usage:

.. code-block:: python

    from openquake.commonlib import sap
    def fun(input, inplace, output=None, x='X', out='/tmp'):
        'Example'
        print locals()

    p = sap.Parser(fun)
    p.arg('input', 'input file or archive')
    p.arg('output', 'output archive')
    p.opt('out', 'optional output file')
    p.flg('inplace', 'convert inplace')
    p.callfunc()

Parsers can be composed too.
"""

import sys
import inspect
import argparse
from collections import OrderedDict


NODEFAULT = object()


class Parser(object):
    """
    A simple way to define command processors based on argparse.
    Each parser is associated to a function and parsers can be
    composed together, by dispatching on a given name (if not given,
    the function name is used).
    """
    def __init__(self, func, name=None, parentparser=None):
        self.func = func
        self.name = name or func.__name__
        args, varargs, varkw, defaults = inspect.getargspec(func)
        defaults = defaults or ()
        nodefaults = len(args) - len(defaults)
        alldefaults = (NODEFAULT,) * nodefaults + defaults
        self.argdict = OrderedDict(zip(args, alldefaults))
        self.parentparser = parentparser or argparse.ArgumentParser(
            description=func.__doc__)
        self.names = set()
        self.all_arguments = []
        self._argno = 0

    def _add(self, name, *args, **kw):
        """
        Add an argument to the underlying parser and grow the list
        .all_arguments and the set .names
        """
        argname = self.argdict.keys()[self._argno]
        if argname != name:
            raise NameError(
                'Setting argument %s, but it should be %s' % (name, argname))
        self.parentparser.add_argument(*args, **kw)
        self.all_arguments.append((args, kw))
        self.names.add(name)
        self._argno += 1

    def arg(self, name, help, type=None, choices=None, metavar=None):
        """Describe a positional argument"""
        kw = dict(help=help, type=type, choices=choices, metavar=metavar)
        default = self.argdict[name]
        if default is not NODEFAULT:
            kw['nargs'] = '?'
            kw['default'] = default
            kw['help'] = kw['help'] + ' [default: %s]' % str(default)
        self._add(name, name, **kw)

    def opt(self, name, help, abbrev=None,
            type=None, choices=None, metavar=None):
        """Describe an option"""
        kw = dict(help=help, type=type, choices=choices, metavar=metavar)
        default = self.argdict[name]
        if default is not NODEFAULT:
            kw['default'] = default
            kw['metavar'] = metavar or str(default)
        abbrev = abbrev or '-' + name[0]
        longname = '--' + name
        self._add(name, abbrev, longname, **kw)

    def flg(self, name, help, abbrev=None):
        """Describe a flag"""
        abbrev = abbrev or '-' + name[0]
        longname = '--' + name
        self._add(name, abbrev, longname, action='store_true', help=help)

    def callfunc(self, argv=None):
        """
        Parse the argv list and extract a dictionary of arguments which
        is then passed to  the function underlying the Parser.
        """
        for name, default in self.argdict.iteritems():
            if not name in self.names and default is NODEFAULT:
                raise NameError('Missing argparse description for %s' % name)
        namespace = self.parentparser.parse_args(argv or sys.argv[1:])
        return self.func(**vars(namespace))

    def help(self):
        """
        Return the help message as a string
        """
        return self.parentparser.format_help()


def compose(parsers, name='main', parentparser=None):
    """
    Collects together different arguments parsers and builds a single
    Parser dispatching on the subparsers depending on
    the first argument, i.e. the name of the subparser to invoke.

    :param parsers: a list of Parser instances
    :param name: the name of the composed parser
    """
    assert len(parsers) > 1, parsers
    parentparser = parentparser or argparse.ArgumentParser()
    subparsers = parentparser.add_subparsers(
        help='available subcommands (see sub help)')
    for p in parsers:
        subp = subparsers.add_parser(p.name)
        for args, kw in p.all_arguments:
            subp.add_argument(*args, **kw)
        subp.set_defaults(_func=p.func)

    def main(**kw):
        func = kw.pop('_func')
        return func(**kw)
    main.__name__ = name
    return Parser(main, name, parentparser)
