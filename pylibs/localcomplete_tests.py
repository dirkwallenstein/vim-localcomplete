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


import mock
import os
import sys
import unittest


class LocalCompleteTestsError(Exception):
    """
    The base exception for this module.
    """


def fix_vim_module():
    """
    Insert a fake vim module into sys.modules that informs about a missing
    actual mock for tests and makes importing localcomplete possible.
    """
    message_mock = mock.MagicMock(spec_set=['eval', 'command', 'current'])
    attribute_exception = mock.PropertyMock(
            side_effect=LocalCompleteTestsError(
            "ERROR: no mock provided for the module 'vim'"))
    type(message_mock).current = attribute_exception
    type(message_mock).command = attribute_exception
    type(message_mock).eval = attribute_exception
    sys.modules['vim'] = message_mock


# Import localcomplete
fix_vim_module()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import localcomplete


class VimMockFactory(object):
    """
    Create a vim mock for test cases.
    """

    ConfigMapping = dict(
        want_reversed = "g:localcomplete#WantReversedOrder",
        want_centered = "g:localcomplete#WantCenteredOrder",
        want_ignorecase = "g:localcomplete#WantIgnoreCase",
        above_count = "localcomplete#getLinesAboveCount()",
        below_count = "localcomplete#getLinesBelowCount()",
        show_origin = "g:localcomplete#ShowOriginNote",
        iskeyword = "&iskeyword",
        encoding = "&encoding",
        keyword_base = "a:keyword_base",
        dictionary = "&dictionary",
    )

    @classmethod
    def get_mock(cls,
            buffer_content=None,
            current_line_index=None,
            **config):
        """
        Get a vim mock with the configuration according to the arguments.

        buffer_content: A list of lines in the current buffer
        current_line_index: An index into the buffer_content
        **config: Vim configuration.  See ConfigMapping for possible keys and
                what they mean.
        """
        factory_instance = cls(
                current_line_index=current_line_index,
                buffer_content=buffer_content,
                **config)
        vim_mock = mock.NonCallableMock(
                spec_set=['eval', 'command', 'current'])
        vim_mock.eval = mock.Mock(spec_set=[],
                side_effect=factory_instance.eval_mocker)
        vim_mock.command = mock.Mock(spec_set=[],
                side_effect=LocalCompleteTestsError(
                        "vim.command is not implemented"))
        vim_mock.current = mock.NonCallableMock(spec_set=['buffer'])
        if buffer_content is None:
            type(vim_mock.current).buffer = mock.PropertyMock(
                    side_effect=LocalCompleteTestsError(
                    "ERROR: no buffer specified"))
        else:
            vim_mock.current.buffer = buffer_content
        return vim_mock

    def __init__(self,
            current_line_index=None,
            buffer_content=None,
            **config):
        """
        Internally used to hold state for closures.  Client code uses the
        factory classmethod only.
        """
        self.current_line_index = current_line_index
        self.buffer_content = buffer_content
        self.eval_results = {}

        self._prepare_eval_results(config)

    def _prepare_eval_results(self, config):
        """
        Populate self.eval_results used by eval_mocker
        """
        invalid_config_keys = set(config) - set(self.ConfigMapping.keys())
        if invalid_config_keys:
            raise LocalCompleteTestsError("Invalid config keys: %s"
                    % " ".join(invalid_config_keys))
        for k, result in config.items():
            self.eval_results[self.ConfigMapping[k]] = result

    def eval_mocker(self, expression):
        """
        The side_effect for vim.eval
        """
        try:
            return self.eval_results[expression]
        except KeyError:
            raise LocalCompleteTestsError("No eval result recorded for '%s'"
                    % expression)


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
        with self.assertRaises(LocalCompleteTestsError):
            sys.modules['vim'].command("echo")

    def test_buffer_unset(self):
        """Raise an exception when no buffer has been specified"""
        vim_mock = VimMockFactory.get_mock()
        with self.assertRaises(LocalCompleteTestsError):
            return vim_mock.current.buffer

    def test_buffer_full(self):
        """There is something in the buffer"""
        vim_mock = VimMockFactory.get_mock(buffer_content=["zero", "one"])
        self.assertEqual(vim_mock.current.buffer[1], "one")


class TestZipFlattenLongest(unittest.TestCase):

    def test_below_tail(self):
        zip_gen = localcomplete.zip_flatten_longest([1, 2], [11, 22, 33, 44])
        self.assertEqual(list(zip_gen), [1, 11, 2, 22, 33, 44])

    def test_above_tail(self):
        zip_gen = localcomplete.zip_flatten_longest([1, 2, 3, 4], [11, 22])
        self.assertEqual(list(zip_gen), [1, 11, 2, 22, 3, 4])

    def test_zeros_are_present(self):
        zip_gen = localcomplete.zip_flatten_longest([1, 0], [11, 0, 33, 44])
        self.assertEqual(list(zip_gen), [1, 11, 0, 0, 33, 44])

    def test_both_empty(self):
        zip_gen = localcomplete.zip_flatten_longest([], [])
        self.assertEqual(list(zip_gen), [])

    def test_one_empty(self):
        zip_gen_above = localcomplete.zip_flatten_longest([1, 2], [])
        self.assertEqual(list(zip_gen_above), [1, 2])
        zip_gen_below = localcomplete.zip_flatten_longest([], [1, 2])
        self.assertEqual(list(zip_gen_below), [1, 2])


class TestJoinBufferLines(unittest.TestCase):

    def _helper_join_test(self,
            want_reversed,
            want_centered,
            expected_result_lines,
            **join_args
            ):
        vim_mock = VimMockFactory.get_mock(
                want_reversed=want_reversed,
                want_centered=want_centered)
        expected_result_string = os.linesep.join(expected_result_lines)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.join_buffer_lines(**join_args)
        self.assertEqual(actual_result, expected_result_string)

    def test_centered_join(self):
        self._helper_join_test(
                want_reversed=1,
                want_centered=1,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["3", "2", "4", "1", "5"])

    def test_reversed_join(self):
        self._helper_join_test(
                want_reversed=1,
                want_centered=0,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["5", "4", "3", "2", "1"])

    def test_forward_join(self):
        self._helper_join_test(
                want_reversed=0,
                want_centered=0,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["1", "2", "3", "4", "5"])

    def test_single_line_join(self):
        self._helper_join_test(
                want_reversed=1,
                want_centered=1,
                above_lines=[],
                current_lines=["this is the only line"],
                below_lines=[],
                expected_result_lines=["this is the only line"])


class TestGetBufferIndexes(unittest.TestCase):
    pass
# TODO (also add test framework tests for line getting)
# TODO when do we use the call() helper? Only for chains ?

@mock.patch('localcomplete.join_buffer_lines')
class TestGetHaystack(unittest.TestCase):
    """
    Test localcomplete.get_haystack().

    The index validity is not a responsibility here.
    """

    def test_common_case(self, join_mock):
        vim_mock = VimMockFactory.get_mock(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"])
        with mock.patch('localcomplete.vim', vim_mock):
            localcomplete.get_haystack(1, 3, 5)
        join_call_dict = dict(
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"]
        )
        join_mock.assert_called_once_with(**join_call_dict)

    def test_single_line_case(self, join_mock):
        vim_mock = VimMockFactory.get_mock(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"])
        with mock.patch('localcomplete.vim', vim_mock):
            localcomplete.get_haystack(4, 4, 4)
        join_call_dict = dict(
                above_lines=[],
                current_lines=["4"],
                below_lines=[]
        )
        join_mock.assert_called_once_with(**join_call_dict)
