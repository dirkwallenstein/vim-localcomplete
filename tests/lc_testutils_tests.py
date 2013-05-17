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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import mock
import sys
import unittest

from tests.lc_testutils import LCTestUtilsError
from tests.lc_testutils import VimMockFactory
from tests.lc_testutils import fix_vim_module

class TestTests(unittest.TestCase):
    """
    Test parts of the test framework.
    """

    def test_mock_object_classes_are_isolated(self):
        mod_mock = mock.MagicMock()
        type(mod_mock).test_attribute = "attribute"
        self.assertEqual(mod_mock.test_attribute, "attribute")
        self.assertIsInstance(mock.MagicMock().test_attribute, mock.MagicMock)

    def test_unpatched_vim_exception(self):
        fix_vim_module()
        with self.assertRaises(LCTestUtilsError):
            sys.modules['vim'].command("echo")

    def test_buffer_unset(self):
        """Raise an exception when no buffer has been specified"""
        vim_mock = VimMockFactory.get_mock()
        with self.assertRaises(LCTestUtilsError):
            return vim_mock.current.buffer

    def test_buffer_full(self):
        """There is something in the buffer"""
        vim_mock = VimMockFactory.get_mock(buffer_content=["zero", "one"])
        self.assertEqual(vim_mock.current.buffer[1], "one")

    def test_last_line_is_line_number(self):
        vim_mock = VimMockFactory.get_mock(buffer_content=["1", "2", "3"])
        self.assertEqual(vim_mock.eval("line('$')"), 3)

    def test_current_line_is_line_number(self):
        vim_mock = VimMockFactory.get_mock(current_line_index=3)
        self.assertEqual(vim_mock.eval("line('.')"), 4)

    def test_requesting_an_invalid_mock_config_key_raises_an_exception(self):
        with self.assertRaises(LCTestUtilsError):
            VimMockFactory.get_mock(__INVALID__KEY__='')

    def test_evaluating_unregistered_vim_expressions_raises_an_exception(self):
        vim_mock = VimMockFactory.get_mock()
        with self.assertRaises(LCTestUtilsError):
            vim_mock.eval("&invalid")
