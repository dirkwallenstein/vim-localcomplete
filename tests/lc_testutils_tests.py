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
