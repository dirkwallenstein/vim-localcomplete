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


import contextlib
import functools
import mock
import os
import re
import unittest


# Import Test Utils
from tests.lc_testutils import VimMockFactory
from tests.lc_testutils import fix_vim_module

# Import localcomplete
fix_vim_module()
from pylibs import localcomplete


class LocalCompleteTestsError(Exception):
    """
    The base exception for this module.
    """


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


class TestGenerateHaystack(unittest.TestCase):

    def _helper_isolate_sut(self,
            match_result_order,
            expected_result_lines,
            buffer_content=["0", "1", "2", "3", "4", "5", "6"],
            above_range=range(1, 3),
            current_index=3,
            below_range=range(4, 6)):

        vim_mock = VimMockFactory.get_mock(
                match_result_order=match_result_order,
                buffer_content=buffer_content)
        buffer_range_mock = mock.Mock(
                return_value=(above_range, current_index, below_range))

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_buffer_ranges=buffer_range_mock,
                vim=vim_mock):
            actual_result = list(localcomplete.generate_haystack())
        self.assertEqual(actual_result, expected_result_lines)

    def test_centered_order(self):
        self._helper_isolate_sut(
                match_result_order=localcomplete.MATCH_ORDER_CENTERED,
                expected_result_lines=["3", "2", "4", "1", "5"])

    def test_reversed_above_first_order(self):
        self._helper_isolate_sut(
                match_result_order=(
                        localcomplete.MATCH_ORDER_REVERSE_ABOVE_FIRST),
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                expected_result_lines=["3", "2", "1", "5", "4"])

    def test_reversed_order(self):
        self._helper_isolate_sut(
                match_result_order=localcomplete.MATCH_ORDER_REVERSE,
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                expected_result_lines=["5", "4", "3", "2", "1"])

    def test_forward_order(self):
        self._helper_isolate_sut(
                match_result_order=localcomplete.MATCH_ORDER_NORMAL,
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                expected_result_lines=["1", "2", "3", "4", "5"])

    def test_invalid_order_request_raises_exception(self):
        with self.assertRaises(localcomplete.LocalCompleteError):
            self._helper_isolate_sut(
                    match_result_order=-1,
                    expected_result_lines=[])


class TestGetBufferRanges(unittest.TestCase):

    def _helper_index_test(self, expected_result, **mock_arguments):
        vim_mock = VimMockFactory.get_mock(**mock_arguments)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            ar, c, br = localcomplete.get_buffer_ranges()
            actual_result = (list(ar), c, list(br))
        self.assertEqual(actual_result, expected_result)

    def test_negative_range_specs_select_the_whole_buffer(self):
        """Negative range indexes select up to the start or end of the file"""
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=-1,
                below_count=-1,
                expected_result=([0, 1, 2], 3, [4, 5, 6]))

    def test_all_zero_range_specs_produce_a_single_index(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=0,
                below_count=0,
                expected_result=([], 3, []))

    def test_valid_range_spec_clipping(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=2,
                below_count=2,
                expected_result=([1, 2], 3, [4, 5]))

    def test_beyond_bounds_range_specs_clip_to_the_whole_buffer(self):
        self._helper_index_test(
                buffer_content=["0", "1", "2", "3", "4", "5", "6"],
                current_line_index=3,
                above_count=20,
                below_count=20,
                expected_result=([0, 1, 2], 3, [4, 5, 6]))


class TestProduceResultValue(unittest.TestCase):

    def test_empty(self):
        vim_mock = VimMockFactory.get_mock(show_origin=1)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            actual_result = localcomplete.produce_result_value(
                    [], 'testorigin')
        expected_result = []
        self.assertEqual(actual_result, expected_result)

    def test_nonempty_with_orign_note(self):
        vim_mock = VimMockFactory.get_mock(show_origin=1)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
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
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
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
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            actual_result = (
                    localcomplete.get_additional_keyword_chars_from_vim())
        self.assertEqual(actual_result, '@_#:')

    def test_no_matches(self):
        vim_mock = VimMockFactory.get_mock(
                iskeyword='48-57,192-255')
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
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

        with mock.patch.multiple(__name__ + '.localcomplete',
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
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_casematch_flag(),
                    re.IGNORECASE)

    def test_casematch_flag_not_requested(self):
        vim_mock = VimMockFactory.get_mock(want_ignorecase=0)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_casematch_flag(),
                    0)


class TestTransmitLocalMatchResultToVim(unittest.TestCase):

    def test_argument_is_passed_through(self):
        produce_mock = mock.Mock(side_effect=lambda matches, origin : matches)
        vim_mock = VimMockFactory.get_mock()
        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock,
                vim=vim_mock):
            localcomplete.transmit_local_matches_result_to_vim(1)
        vim_command_string = localcomplete.VIM_COMMAND_LOCALCOMPLETE % 1
        vim_mock.command.assert_called_once_with(vim_command_string)


class TestCompleteLocalMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_local_matches(self,
            haystack,
            keyword_base,
            encoding='utf-8',
            min_len_local=0,
            keyword_chars='',
            want_ignorecase=False):
        """
        Mock out all collaborator functions in the function under temporary
        test and the vim module.

        Yield produce_mock
        """
        case_mock_retval = re.IGNORECASE if want_ignorecase else 0

        chars_mock = mock.Mock(spec_set=[], return_value=keyword_chars)
        case_mock = mock.Mock(spec_set=[], return_value=case_mock_retval)
        haystack_mock = mock.Mock(spec_set=[], return_value=haystack)
        transmit_result_mock = mock.Mock(spec_set=[], return_value=[])

        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                min_len_local=min_len_local,
                keyword_base=keyword_base)

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                generate_haystack=haystack_mock,
                transmit_local_matches_result_to_vim=transmit_result_mock,
                vim=vim_mock):
            yield transmit_result_mock

    def test_helper_function_actually_restores(self):
        with self._helper_isolate_local_matches(haystack=[], keyword_base=""
                ) as transmit_result_mock:
            self.assertIs(transmit_result_mock,
                    localcomplete.transmit_local_matches_result_to_vim)
        self.assertIsNot(transmit_result_mock,
                localcomplete.transmit_local_matches_result_to_vim)

    def _helper_completion_tests(self,
            result_list,
            **isolation_args):
        """
        Use the isolation helper to set up the environment and compare the
        results from complete_local_matches with the given result_list.

        The haystack argument has to be a string that will be used to execute
        the test two times.  Once as the sole buffer line, and once split into
        multiple buffer lines.
        """
        def actual_test(isolation_args):
            with self._helper_isolate_local_matches(**isolation_args
                    ) as (transmit_result_mock):

                localcomplete.complete_local_matches()

            transmit_result_mock.assert_called_once_with(result_list)

        haystack_source = isolation_args['haystack']

        isolation_args['haystack'] = [haystack_source]
        actual_test(isolation_args)

        isolation_args['haystack'] = haystack_source.split()
        actual_test(isolation_args)

    def test_find_results_exactly_at_the_min_length_limit(self):
        self._helper_completion_tests(
                haystack="  priory Prize none prized none Primary  ",
                keyword_base="pri",
                min_len_local=3,
                result_list=u"priory prized".split())

    def test_find_no_results_below_the_min_length_limit(self):
        self._helper_completion_tests(
                haystack="  priory Prize none prized none Primary  ",
                keyword_base="pri",
                min_len_local=4,
                result_list=[])

    def test_find_case_sensitive_matches(self):
        self._helper_completion_tests(
                haystack="  priory Prize none prized none Primary  ",
                keyword_base="pri",
                result_list=u"priory prized".split())

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
                keyword_base="pri")
        result_list = u"priory prize prized primary".split()
        result_list.append(isolation_args['keyword_base'])
        with mock.patch.dict('os.environ', LOCALCOMPLETE_DEBUG="yes-nonempty"):
            self._helper_completion_tests(
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

        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
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

        with mock.patch.multiple(__name__ + '.localcomplete',
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
        line = u"uuuber \u00fcberfu\u00df"
        with self._helper_isolate_column_getter(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_unicode_leading(self):
        line = u"\u00fc\u00fc\u00fcber uberfus"
        with self._helper_isolate_column_getter(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_findstart_unicode_both(self):
        line = u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df"
        with self._helper_isolate_column_getter(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())


class TestFindstartTranslateToByteIndex(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_column_translator(self,
            line_start,
            encoding='utf-8'):

        line_mock = mock.Mock(spec_set=[], return_value=line_start)
        vim_mock = VimMockFactory.get_mock(encoding=encoding)

        with mock.patch.multiple(__name__ + '.localcomplete',
                findstart_get_line_up_to_cursor=line_mock,
                vim=vim_mock):
            yield

    def test_findstart_translate_leading_multibytes(self):
        line = u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df"
        with self._helper_isolate_column_translator(line_start=line):
            self.assertEqual(10,
                    localcomplete.findstart_translate_to_byte_index(7))

    def test_findstart_translate_no_leading_multibytes(self):
        line = u"uuuber \u00fcberfu\u00df"
        with self._helper_isolate_column_translator(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_translate_to_byte_index(7))


class TestFindstartLocalMatches(unittest.TestCase):

    def _helper_isolate_findstarter(byte_index):
        def configured_decorator(f):
            @functools.wraps(f)
            def wrapped_test_method(self):
                byte_mock = mock.Mock(spec_set=[], return_value=byte_index)
                vim_mock = VimMockFactory.get_mock()

                with mock.patch.multiple(__name__ + '.localcomplete',
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
            is_dictionary_configured=True,
            is_dictionary_path_valid=True):

        translated_content = os.linesep.join(dict_content.split())

        dictionary_path = 'test:nonempty' if is_dictionary_configured else ''

        content_mock = mock.Mock(spec_set=[], return_value=translated_content)
        if not is_dictionary_path_valid:
            content_mock.side_effect = IOError("undertest")
        produce_mock = mock.Mock(spec_set=[], return_value=[])
        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                keyword_base=keyword_base,
                dictionary=dictionary_path)

        with mock.patch.multiple(__name__ + '.localcomplete',
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


class TestGetCurrentBufferIndex(unittest.TestCase):

    def test_getting_the_buffer_index_embedded_between_other_buffers(self):

        WANTED_BUFFER_NUMBER = 5

        vim_mock = mock.Mock()
        vim_mock.current.buffer.number = WANTED_BUFFER_NUMBER
        vim_mock.buffers = []
        vim_mock.buffers.append(mock.Mock(number=17))
        vim_mock.buffers.append(mock.Mock(number=7))
        vim_mock.buffers.append(mock.Mock(number=WANTED_BUFFER_NUMBER))
        vim_mock.buffers.append(mock.Mock(number=27))

        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_current_buffer_index(),
                    2)

    def test_current_buffer_is_the_first(self):

        WANTED_BUFFER_NUMBER = 5

        vim_mock = mock.Mock()
        vim_mock.current.buffer.number = WANTED_BUFFER_NUMBER
        vim_mock.buffers = []
        vim_mock.buffers.append(mock.Mock(number=WANTED_BUFFER_NUMBER))
        vim_mock.buffers.append(mock.Mock(number=27))

        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            self.assertEqual(
                    localcomplete.get_current_buffer_index(),
                    0)


class TestGenerateBuffersSearchOrder(unittest.TestCase):

    @contextlib.contextmanager
    def _isolate_sut(self, buffer_count, current_index, zip_result_list):

        index_mock = mock.Mock(return_value=current_index)
        zip_mock = mock.Mock(return_value=zip_result_list)

        vim_mock = mock.Mock()
        vim_mock.buffers.__len__ = mock.Mock(return_value=buffer_count)
        with mock.patch.multiple(__name__ + '.localcomplete',
                vim=vim_mock,
                get_current_buffer_index=index_mock,
                zip_flatten_longest=zip_mock):
            yield zip_mock

    def test_generating_a_sequence(self):
        with self._isolate_sut(
                buffer_count=9,
                current_index=5,
                zip_result_list=[11, 22]):

            actual_result = list(localcomplete.generate_buffers_search_order())
        self.assertEqual(actual_result, [5, 11, 22])

    def test_zip_range_arguments_correct_with_buffers_before_and_after(self):
        with self._isolate_sut(
                buffer_count=5,
                current_index=2,
                zip_result_list=[11, 22]) as zip_mock:

            list(localcomplete.generate_buffers_search_order())
        zip_mock.assert_called_once_with([1, 0], [3, 4])

    def test_zip_range_arguments_correct_with_only_one_buffer(self):
        with self._isolate_sut(
                buffer_count=1,
                current_index=0,
                zip_result_list=[11, 22]) as zip_mock:

            list(localcomplete.generate_buffers_search_order())
        zip_mock.assert_called_once_with([], [])


class TestGenerateBufferLines(unittest.TestCase):

    @contextlib.contextmanager
    def _mock_out_vim_buffers(self, buffers_content, search_order):
        vim_mock = mock.Mock(spec_set=['buffers'])
        vim_mock.buffers = buffers_content
        search_order_mock = mock.Mock(return_value=search_order)
        with mock.patch.multiple(__name__ + '.localcomplete',
                vim=vim_mock,
                generate_buffers_search_order=search_order_mock):
            yield vim_mock

    def test_lines_of_buffers_become_one_sequence(self):
        with self._mock_out_vim_buffers([
                "a b c".split(),
                "one".split(),
                "x y z".split(),
                ],
                search_order=[0,1,2]):
            actual_result = list(localcomplete.generate_all_buffer_lines())
        self.assertEqual(actual_result, "a b c one x y z".split())

    def test_current_buffer_in_the_middle(self):
        with self._mock_out_vim_buffers([
                "a b c".split(),
                "one".split(),
                "x y z".split(),
                ],
                search_order=[1,0,2]):
            actual_result = list(localcomplete.generate_all_buffer_lines())
        self.assertEqual(actual_result, "one a b c x y z".split())


class TestTransmitAllBufferResultToVim(unittest.TestCase):

    def test_argument_is_passed_through(self):
        produce_mock = mock.Mock(side_effect=lambda matches, origin : matches)
        vim_mock = VimMockFactory.get_mock()
        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock,
                vim=vim_mock):
            localcomplete.transmit_all_buffer_result_to_vim(1)
        vim_command_string = localcomplete.VIM_COMMAND_BUFFERCOMPLETE % 1
        vim_mock.command.assert_called_once_with(vim_command_string)


class TestCompleteAllBufferMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_buffer_matches(self,
            buffers_contents,
            keyword_base,
            encoding='utf-8',
            keyword_chars='',
            min_len_all_buffer=0,
            want_ignorecase=False):

        case_mock_retval = re.IGNORECASE if want_ignorecase else 0

        chars_mock = mock.Mock(spec_set=[], return_value=keyword_chars)
        case_mock = mock.Mock(spec_set=[], return_value=case_mock_retval)
        buffers_mock = mock.Mock(spec_set=[], return_value=buffers_contents)
        transmit_result_mock = mock.Mock(spec_set=[], return_value=[])

        vim_mock = VimMockFactory.get_mock(
                min_len_all_buffer=min_len_all_buffer,
                encoding=encoding,
                keyword_base=keyword_base)

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                generate_all_buffer_lines=buffers_mock,
                transmit_all_buffer_result_to_vim=transmit_result_mock,
                vim=vim_mock):
            yield transmit_result_mock

    def _helper_completion_tests(self,
            result_list,
            **isolation_args):
        """
        Use the isolation helper to set up the environment and compare the
        results from complete_local_matches with the given result_list.
        """
        with self._helper_isolate_buffer_matches(**isolation_args
                ) as transmit_result_mock:

            localcomplete.complete_all_buffer_matches()

        transmit_result_mock.assert_called_once_with(result_list)

    def test_find_in_all_buffers(self):
        self._helper_completion_tests(
                buffers_contents=[
                        " priory prize ",
                        " none prized none primary  ",
                        "Priority number",
                        "number Prime   principal skinner",
                        ],
                keyword_base="pri",
                min_len_all_buffer = 3,
                result_list=(u"priory prize prized primary principal".split()))

    def test_find_nothing_if_min_length_limit_not_reached(self):
        self._helper_completion_tests(
                buffers_contents=[
                        " priory prize ",
                        " none prized none primary  ",
                        "Priority number",
                        "number Prime   principal skinner",
                        ],
                keyword_base="pri",
                min_len_all_buffer=4,
                result_list=[])

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
