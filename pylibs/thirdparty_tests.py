# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License


import unittest

from pylibs import thirdparty


class ThirdpartyTestsError(Exception):
    """
    The base exception for this module.
    """


class TestPythonToVimStr(unittest.TestCase):

    def test_normal_string(self):
        reprer = thirdparty.PythonToVimStr('without any special cases')
        self.assertEqual(repr(reprer), r'"without any special cases"')

    def test_embedded_double_quotes(self):
        reprer = thirdparty.PythonToVimStr('contains \"double\" qoutes')
        self.assertEqual(repr(reprer), r'"contains \"double\" qoutes"')

    def test_embedded_unicode(self):
        reprer = thirdparty.PythonToVimStr(u'der \u00fcberfu\u00df')
        self.assertEqual(repr(reprer), '"der \xc3\xbcberfu\xc3\x9f"')
