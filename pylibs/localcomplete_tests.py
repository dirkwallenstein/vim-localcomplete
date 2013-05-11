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


import contextlib
import functools
import mock
import os
import re
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
        match_result_order = "localcomplete#getMatchResultOrder()",
        want_ignorecase = "localcomplete#getWantIgnoreCase()",
        above_count = "localcomplete#getLinesAboveCount()",
        below_count = "localcomplete#getLinesBelowCount()",
        show_origin = "localcomplete#getWantOriginNote()",
        iskeyword = "&iskeyword",
        encoding = "&encoding",
        keyword_base = "a:keyword_base",
        dictionary = "&dictionary",
        keyword_chars = "localcomplete#getAdditionalKeywordChars()"
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
        vim_mock.command = mock.Mock(spec_set=[])
        vim_mock.current = mock.NonCallableMock(
                spec_set=['buffer', 'line', 'window'])
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
        if self.current_line_index is not None:
            self.eval_results["line('.')"] = self.current_line_index + 1
        if self.buffer_content is not None:
            self.eval_results["line('$')"] = len(self.buffer_content)

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

    def test_last_line_is_line_number(self):
        vim_mock = VimMockFactory.get_mock(buffer_content=["1", "2", "3"])
        self.assertEqual(vim_mock.eval("line('$')"), 3)

    def test_current_line_is_line_number(self):
        vim_mock = VimMockFactory.get_mock(current_line_index=3)
        self.assertEqual(vim_mock.eval("line('.')"), 4)


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
            match_result_order,
            expected_result_lines,
            **join_args
            ):
        vim_mock = VimMockFactory.get_mock(
                match_result_order=match_result_order)
        expected_result_string = os.linesep.join(expected_result_lines)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.join_buffer_lines(**join_args)
        self.assertEqual(actual_result, expected_result_string)

    def test_centered_join(self):
        self._helper_join_test(
                match_result_order=localcomplete.MATCH_ORDER_CENTERED,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["3", "2", "4", "1", "5"])

    def test_reversed_above_first_join(self):
        self._helper_join_test(
                match_result_order=(
                        localcomplete.MATCH_ORDER_REVERSE_ABOVE_FIRST),
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["3", "2", "1", "5", "4"])

    def test_reversed_join(self):
        self._helper_join_test(
                match_result_order=localcomplete.MATCH_ORDER_REVERSE,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["5", "4", "3", "2", "1"])

    def test_forward_join(self):
        self._helper_join_test(
                match_result_order=localcomplete.MATCH_ORDER_NORMAL,
                above_lines=["1", "2"],
                current_lines=["3"],
                below_lines=["4", "5"],
                expected_result_lines=["1", "2", "3", "4", "5"])

    def test_single_line_join(self):
        self._helper_join_test(
                match_result_order=localcomplete.MATCH_ORDER_CENTERED,
                above_lines=[],
                current_lines=["this is the only line"],
                below_lines=[],
                expected_result_lines=["this is the only line"])

    def test_invalid_order_request_raises_exception(self):
        with self.assertRaises(localcomplete.LocalCompleteError):
            self._helper_join_test(
                    match_result_order=-1,
                    above_lines=[],
                    current_lines=[],
                    below_lines=[],
                    expected_result_lines=[])


class TestGetBufferIndexes(unittest.TestCase):

    def _helper_index_test(self, expected_result, **mock_arguments):
        vim_mock = VimMockFactory.get_mock(**mock_arguments)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.get_buffer_indexes()
        self.assertEqual(actual_result, expected_result)

    def test_negative_range_indexes(self):
        """Negative range indexes select up to the start or end of the file"""
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=-1,
                below_count=-1,
                expected_result=(0, 3, 6))

    def test_zero_range_indexes(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=0,
                below_count=0,
                expected_result=(3, 3, 3))

    def test_unadjusted_range_indexes(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=2,
                below_count=2,
                expected_result=(1, 3, 5))

    def test_adjusted_range_indexes(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=20,
                below_count=20,
                expected_result=(0, 3, 6))


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


class TestProduceResultValue(unittest.TestCase):

    def test_empty(self):
        vim_mock = VimMockFactory.get_mock(show_origin=1)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.produce_result_value(
                    [], 'testorigin')
        expected_result = []
        self.assertEqual(actual_result, expected_result)

    def test_nonempty_with_orign_note(self):
        vim_mock = VimMockFactory.get_mock(show_origin=1)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.produce_result_value(
                    ['1', '2', '3'],
                    'testorigin')
        expected_result = [
                 {'word': '1', 'menu': 'testorigin'},
                 {'word': '2', 'menu': 'testorigin'},
                 {'word': '3', 'menu': 'testorigin'},
                 ]
        self.assertEqual(actual_result, expected_result)

    def test_nonempty_without_orign_note(self):
        vim_mock = VimMockFactory.get_mock(show_origin=0)
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = localcomplete.produce_result_value(
                    ['1', '2', '3'],
                    'testorigin')
        expected_result = [
                 {'word': '1'},
                 {'word': '2'},
                 {'word': '3'},
                 ]
        self.assertEqual(actual_result, expected_result)


class TestGetAdditionalKeywordCharsFromVim(unittest.TestCase):

    def test_diverse_matches(self):
        vim_mock = VimMockFactory.get_mock(
                iskeyword='@,48-57,_,#,:,$%!,192-255')
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = (
                    localcomplete.get_additional_keyword_chars_from_vim())
        self.assertEqual(actual_result, '@_#:')

    def test_no_matches(self):
        vim_mock = VimMockFactory.get_mock(
                iskeyword='48-57,192-255')
        with mock.patch('localcomplete.vim', vim_mock):
            actual_result = (
                    localcomplete.get_additional_keyword_chars_from_vim())
        self.assertEqual(actual_result, '')


class TestGetAdditionalKeywordChars(unittest.TestCase):

    _select_from_vim = localcomplete.SPECIAL_VALUE_SELECT_VIM_KEYWORDS

    @contextlib.contextmanager
    def _helper_isolate_test_subject(self,
            expected_result,
            keyword_chars,
            keyword_chars_from_vim=''):

        vim_mock = VimMockFactory.get_mock(keyword_chars=keyword_chars)
        from_vim_mock = mock.Mock(return_value=keyword_chars_from_vim)

        with mock.patch.multiple('localcomplete',
                get_additional_keyword_chars_from_vim=from_vim_mock,
                vim=vim_mock):
            actual_result = localcomplete.get_additional_keyword_chars()
        self.assertEqual(actual_result, expected_result)

    def test_vim_keywords(self):
        self._helper_isolate_test_subject(
                expected_result=':#',
                keyword_chars=':#')

    def test_select_from_vim(self):
        self._helper_isolate_test_subject(
                expected_result='.#',
                keyword_chars=self._select_from_vim,
                keyword_chars_from_vim='.#')


class TestGetCasematchFlag(unittest.TestCase):

    def test_casematch_flag_requested(self):
        vim_mock = VimMockFactory.get_mock(want_ignorecase=1)
        with mock.patch('localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_casematch_flag(),
                    re.IGNORECASE)

    def test_casematch_flag_not_requested(self):
        vim_mock = VimMockFactory.get_mock(want_ignorecase=0)
        with mock.patch('localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_casematch_flag(),
                    0)


class TestCompleteLocalMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_local_matches(self,
            haystack,
            keyword_base,
            encoding='utf-8',
            keyword_chars='',
            buffer_indexes=(),
            want_ignorecase=False):
        """
        Mock out all collaborator functions in the function under temporary
        test and the vim module.

        Yield (vim_mock, produce_mock)
        """
        case_mock_retval = re.IGNORECASE if want_ignorecase else 0

        chars_mock = mock.Mock(spec_set=[], return_value=keyword_chars)
        case_mock = mock.Mock(spec_set=[], return_value=case_mock_retval)
        indexes_mock = mock.Mock(spec_set=[], return_value=buffer_indexes)
        haystack_mock = mock.Mock(spec_set=[], return_value=haystack)
        produce_mock = mock.Mock(spec_set=[], return_value=[])

        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                keyword_base=keyword_base)

        with mock.patch.multiple('localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                get_buffer_indexes=indexes_mock,
                get_haystack=haystack_mock,
                produce_result_value=produce_mock,
                vim=vim_mock):
            yield (vim_mock, produce_mock)

    def test_helper_function_actually_restores(self):
        with self._helper_isolate_local_matches(haystack="", keyword_base=""
                ) as (_unused_vim_mock, produce_mock):
            self.assertIs(produce_mock, localcomplete.produce_result_value)
        self.assertIsNot(produce_mock, localcomplete.produce_result_value)

    def _helper_completion_tests(self,
            result_list,
            want_space_translation=True,
            **isolation_args):
        """
        Use the isolation helper to set up the environment and compare the
        results from complete_local_matches with the given result_list.

        If want_space_translation is True (the default), execute a second test
        with all the spaces in the haystack argument to the isolation helper
        with newlines.
        """
        def actual_test(isolation_args):
            with self._helper_isolate_local_matches(**isolation_args) as (
                    vim_mock, produce_mock):

                localcomplete.complete_local_matches()

            produce_mock.assert_called_once_with(result_list, mock.ANY)
            vim_mock.command.assert_called_once_with(mock.ANY)

        actual_test(isolation_args)

        if want_space_translation:
            haystack = isolation_args['haystack']
            isolation_args['haystack'] = os.linesep.join(haystack.split())
            actual_test(isolation_args)

    def test_find_simple_oneline_matches(self):
        self._helper_completion_tests(
                haystack="  priory prize none prized none primary  ",
                keyword_base="pri",
                result_list=u"priory prize prized primary".split())

    def test_find_case_insensitive_matches(self):
        self._helper_completion_tests(
                haystack="  Priory Prize none prized none primary  ",
                want_ignorecase=True,
                keyword_base="pri",
                result_list=u"Priory Prize prized primary".split())

    def test_find_additional_keyword_char_matches(self):
        self._helper_completion_tests(
                haystack="  prior@ priz: non: priz:d non: primar@  ",
                keyword_chars=":@",
                keyword_base="pri",
                result_list=u"prior@ priz: priz:d primar@".split())

    def test_find_unicode_matches(self):
        self._helper_completion_tests(
                haystack=u"  \u00fcber \u00fcberfu\u00df  ".encode('utf-8'),
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())

    def test_find_debugging_matches(self):
        isolation_args = dict(
                haystack="  priory prize none prized none primary  ",
                keyword_base="pri",
                buffer_indexes=(3,4,777))
        result_list = u"priory prize prized primary".split()
        result_list.extend(["4", "5", "778"])
        result_list.append(isolation_args['keyword_base'])
        result_list.append(isolation_args['haystack'])
        with mock.patch.dict('os.environ', LOCALCOMPLETE_DEBUG="yes-nonempty"):
            self._helper_completion_tests(
                    want_space_translation=False,
                    result_list=result_list,
                    **isolation_args)


class TestFindstartGetLineUpToCursor(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_mock_current(self, full_line, cursor_index):
        if (cursor_index + 1) > len(full_line):
            raise LocalCompleteTestsError("cursor index not within line")
        vim_mock = VimMockFactory.get_mock(encoding="utf-8")
        vim_mock.current.line = full_line
        vim_mock.current.window.cursor = (0, cursor_index)

        with mock.patch('localcomplete.vim', vim_mock):
            yield

    def test_helper_index_exception_outside_border(self):
        with self.assertRaises(LocalCompleteTestsError):
            self._helper_mock_current("x", 1).__enter__()

    def test_helper_index_exception_within_border(self):
        self._helper_mock_current("x", 0).__enter__()

    def test_findstart_up_to_cursor(self):
        with self._helper_mock_current("abba", 2):
            actual_result = localcomplete.findstart_get_line_up_to_cursor()
        self.assertEqual(actual_result, u"ab")


class TestFindstartGetKeywordIndex(unittest.TestCase):

    def test_normal_keyword_in_the_middle(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                '', "abba yuhu")
        self.assertEqual(actual_index, 5)

    def test_no_keyword_trailing(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                '', "abba ")
        self.assertEqual(actual_index, None)

    def test_unicode_keywords(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                u'', u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df")
        self.assertEqual(actual_index, 7)

    def test_additional_keywords(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                ':@', "abba y:u@hu")
        self.assertEqual(actual_index, 5)


class TestFindstartGetStartingColumn(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_column_getter(self,
            line_start,
            encoding='utf-8',
            keyword_chars=''):

        chars_mock = mock.Mock(spec_set=[], return_value=keyword_chars)
        line_mock = mock.Mock(spec_set=[], return_value=line_start)

        vim_mock = VimMockFactory.get_mock(encoding=encoding)

        with mock.patch.multiple('localcomplete',
                get_additional_keyword_chars=chars_mock,
                findstart_get_line_up_to_cursor=line_mock,
                vim=vim_mock):
            yield

    def test_findstart_simple(self):
        with self._helper_isolate_column_getter(line_start="ab b"):
            self.assertEqual(3,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_space(self):
        # The cursor is behind the string
        with self._helper_isolate_column_getter(line_start="ab b "):
            self.assertEqual(5,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_unicode_trailing(self):
        utf8_line = u"uuuber \u00fcberfu\u00df"
        with self._helper_isolate_column_getter(line_start=utf8_line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_unicode_leading(self):
        utf8_line = u"\u00fc\u00fc\u00fcber uberfus"
        with self._helper_isolate_column_getter(line_start=utf8_line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_unicode_both(self):
        utf8_line = u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df"
        with self._helper_isolate_column_getter(line_start=utf8_line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())


class TestFindstartTranslateToByteIndex(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_column_translator(self,
            line_start,
            encoding='utf-8'):

        line_mock = mock.Mock(spec_set=[], return_value=line_start)
        vim_mock = VimMockFactory.get_mock(encoding=encoding)

        with mock.patch.multiple('localcomplete',
                findstart_get_line_up_to_cursor=line_mock,
                vim=vim_mock):
            yield

    def test_findstart_translate_leading_multibytes(self):
        utf8_line = u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df"
        with self._helper_isolate_column_translator(line_start=utf8_line):
            self.assertEqual(10,
                    localcomplete.findstart_translate_to_byte_index(7))

    def test_findstart_translate_no_leading_multibytes(self):
        utf8_line = u"uuuber \u00fcberfu\u00df"
        with self._helper_isolate_column_translator(line_start=utf8_line):
            self.assertEqual(7,
                    localcomplete.findstart_translate_to_byte_index(7))


class TestFindstartLocalMatches(unittest.TestCase):

    def _helper_isolate_findstarter(byte_index):
        def configured_decorator(f):
            @functools.wraps(f)
            def wrapped_test_method(self):
                byte_mock = mock.Mock(spec_set=[], return_value=byte_index)
                vim_mock = VimMockFactory.get_mock()

                with mock.patch.multiple('localcomplete',
                        findstart_translate_to_byte_index=byte_mock,
                        findstart_get_starting_column_index=mock.Mock(),
                        vim=vim_mock):
                    f(self, vim_mock, byte_index)
            return wrapped_test_method
        return configured_decorator

    @_helper_isolate_findstarter(17)
    def test_findstart_result_command_called(self, vim_mock, byte_index):
        localcomplete.findstart_local_matches()
        vim_mock.command.assert_called_once_with(
                localcomplete.VIM_COMMAND_FINDSTART % byte_index)


class TestCompleteDictMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_dict_matches(self,
            dict_content,
            keyword_base,
            encoding='utf-8',
            want_space_translation=True,
            is_dictionary_configured=True,
            is_dictionary_path_valid=True):

        if want_space_translation:
            translated_content = os.linesep.join(dict_content.split())
        else:
            translated_content = dict_content.strip()

        dictionary_path = 'test:nonempty' if is_dictionary_configured else ''

        content_mock = mock.Mock(spec_set=[], return_value=translated_content)
        if not is_dictionary_path_valid:
            content_mock.side_effect = IOError("undertest")
        produce_mock = mock.Mock(spec_set=[], return_value=[])
        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                keyword_base=keyword_base,
                dictionary=dictionary_path)

        with mock.patch.multiple('localcomplete',
                read_file_contents=content_mock,
                produce_result_value=produce_mock,
                vim=vim_mock):

            yield (vim_mock, produce_mock)

    def _helper_completion_tests(self, result_list, **isolation_args):
        with self._helper_isolate_dict_matches(**isolation_args) as (
                vim_mock, produce_mock):

            localcomplete.complete_dictionary_matches()

        produce_mock.assert_called_once_with(result_list, mock.ANY)
        vim_mock.command.assert_called_once_with(mock.ANY)

    def test_find_dict_normal_matches(self):
        self._helper_completion_tests(
                dict_content=u"  priory prize none   Priority   primary  ",
                keyword_base="pri",
                result_list=u"priory prize primary".split())

    def test_find_dict_unicode_matches(self):
        self._helper_completion_tests(
                dict_content=u" \u00fcber \u00fcberfu\u00df  ",
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())

    def test_find_no_matches_without_dictionary(self):
        self._helper_completion_tests(
                dict_content=u"  priory prize none   Priority   primary  ",
                keyword_base="pri",
                is_dictionary_configured=False,
                result_list=[])

    def test_invalid_dictionary_path_results_in_no_matches(self):
        with self._helper_isolate_dict_matches(
                dict_content=u"  priory prize none   Priority   primary  ",
                keyword_base="pri",
                is_dictionary_path_valid=False
                        ) as (vim_mock, produce_mock):

            localcomplete.complete_dictionary_matches()

        produce_mock.assert_called_once_with([], mock.ANY)
        self.assertEqual(vim_mock.command.call_count, 2)


class TestReadFileContent(unittest.TestCase):

    def test_read_file_content(self):
        content = u" \u00fcber \u00fcberfu\u00df  "
        with mock.patch('codecs.open', mock.mock_open(read_data=content)):
            self.assertEqual(localcomplete.read_file_contents(""), content)

class TestGenerateBufferLines(unittest.TestCase):

    @contextlib.contextmanager
    def _mock_out_vim_buffers(self, buffers_content):
        vim_mock = mock.Mock(spec_set=['buffers'])
        vim_mock.buffers = buffers_content
        with mock.patch('localcomplete.vim', vim_mock):
            yield vim_mock

    def test_lines_of_buffers_become_one_sequence(self):
        with self._mock_out_vim_buffers([
                "a b c".split(),
                "one".split(),
                "x y z".split(),
                ]):
            actual_result = list(localcomplete.generate_all_buffer_lines())
        self.assertEqual(actual_result, "a b c one x y z".split())

class TestCompleteAllBufferMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_buffer_matches(self,
            buffers_contents,
            keyword_base,
            encoding='utf-8',
            keyword_chars='',
            want_ignorecase=False):

        case_mock_retval = re.IGNORECASE if want_ignorecase else 0

        chars_mock = mock.Mock(spec_set=[], return_value=keyword_chars)
        case_mock = mock.Mock(spec_set=[], return_value=case_mock_retval)
        buffers_mock = mock.Mock(spec_set=[], return_value=buffers_contents)
        produce_mock = mock.Mock(spec_set=[], return_value=[])

        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                keyword_base=keyword_base)

        with mock.patch.multiple('localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                generate_all_buffer_lines=buffers_mock,
                produce_result_value=produce_mock,
                vim=vim_mock):
            yield (vim_mock, produce_mock)

    def _helper_completion_tests(self,
            result_list,
            **isolation_args):
        """
        Use the isolation helper to set up the environment and compare the
        results from complete_local_matches with the given result_list.
        """
        with self._helper_isolate_buffer_matches(**isolation_args) as (
                vim_mock, produce_mock):

            localcomplete.complete_all_buffer_matches()

        produce_mock.assert_called_once_with(result_list, mock.ANY)
        vim_mock.command.assert_called_once_with(mock.ANY)

    def test_find_in_all_buffers(self):
        self._helper_completion_tests(
                buffers_contents=[
                        " priory prize ",
                        " none prized none primary  ",
                        "Priority number",
                        "number Prime   principal skinner",
                        ],
                keyword_base="pri",
                result_list=(u"priory prize prized primary principal".split()))

    def test_find_case_insensitive_matches(self):
        self._helper_completion_tests(
                buffers_contents=[
                        "  Priory Prize none",
                        " prized none primary  "
                        ],
                want_ignorecase=True,
                keyword_base="pri",
                result_list=u"Priory Prize prized primary".split())

    def test_find_additional_keyword_char_matches(self):
        self._helper_completion_tests(
                buffers_contents=["  prior@ priz: non: priz:d non: primar@  "],
                keyword_chars=":@",
                keyword_base="pri",
                result_list=u"prior@ priz: priz:d primar@".split())

    def test_find_unicode_matches(self):
        self._helper_completion_tests(
                buffers_contents=[
                        u"  \u00fcber \u00fcberfu\u00df  ".encode('utf-8')
                        ],
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())
