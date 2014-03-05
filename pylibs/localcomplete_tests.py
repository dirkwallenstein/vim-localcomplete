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


class TestGetCasematchFlag(unittest.TestCase):

    def _helper_execute_casematch_flag_test(self,
            want_ignorecase_local,
            want_ignorecase_dict,
            casematch_config,
            result_flag):

        vim_mock = VimMockFactory.get_mock(
                want_ignorecase_local=want_ignorecase_local,
                want_ignorecase_dict=want_ignorecase_dict)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            obtained_flag = localcomplete.get_casematch_flag(casematch_config)
        self.assertEqual(obtained_flag, result_flag)

    def test_casematch_flag_local_requested_returns_the_python_constant(self):
        self._helper_execute_casematch_flag_test(
            want_ignorecase_local=1,
            want_ignorecase_dict=0,
            casematch_config=localcomplete.CASEMATCH_CONFIG_LOCAL,
            result_flag=re.IGNORECASE)

    def test_casematch_flag_local_not_requested_returns_zero(self):
        self._helper_execute_casematch_flag_test(
            want_ignorecase_local=0,
            want_ignorecase_dict=1,
            casematch_config=localcomplete.CASEMATCH_CONFIG_LOCAL,
            result_flag=0)

    def test_casematch_flag_dict_requested_returns_the_python_constant(self):
        self._helper_execute_casematch_flag_test(
            want_ignorecase_local=0,
            want_ignorecase_dict=1,
            casematch_config=localcomplete.CASEMATCH_CONFIG_DICT,
            result_flag=re.IGNORECASE)

    def test_casematch_flag_dict_not_requested_returns_zero(self):
        self._helper_execute_casematch_flag_test(
            want_ignorecase_local=1,
            want_ignorecase_dict=0,
            casematch_config=localcomplete.CASEMATCH_CONFIG_DICT,
            result_flag=0)

    def test_invalid_casematch_config_raises_exception(self):
        with self.assertRaises(localcomplete.LocalCompleteError):
            self._helper_execute_casematch_flag_test(
                want_ignorecase_local=0,
                want_ignorecase_dict=0,
                casematch_config=object(),
                result_flag=0)


class TestApplyInfercaseToMatchesCond(unittest.TestCase):

    def _helper_execute_infercase_test(self,
            vim_ignorecase,
            vim_infercase,
            keyword_base,
            matches_input,
            matches_result):

        vim_mock = VimMockFactory.get_mock(
                vim_ignorecase=vim_ignorecase,
                vim_infercase=vim_infercase)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            actual_result = list(localcomplete.apply_infercase_to_matches_cond(
                    keyword_base=keyword_base,
                    found_matches=matches_input))
        self.assertEqual(actual_result, matches_result)

    def test_matches_are_transformed_if_conditions_are_met(self):
        """
        If both ignorecase and infercase are set, all matches are transformed
        to start with the case of the leading word.
        """
        self._helper_execute_infercase_test(
                vim_ignorecase=1,
                vim_infercase=1,
                keyword_base="pri",
                matches_input=u"PrIory prize PrIority priMary".split(),
                matches_result=u"priory prize priority priMary".split())

        self._helper_execute_infercase_test(
                vim_ignorecase=1,
                vim_infercase=1,
                keyword_base="PrI",
                matches_input=u"PrIory prize PrIority priMary".split(),
                matches_result=u"PrIory PrIze PrIority PrIMary".split())

    def test_no_transformation_happens_if_the_conditions_arent_met(self):

        self._helper_execute_infercase_test(
                vim_ignorecase=1,
                vim_infercase=0,
                keyword_base="pri",
                matches_input=u"PrIory prize PrIority priMary".split(),
                matches_result=u"PrIory prize PrIority priMary".split())

        self._helper_execute_infercase_test(
                vim_ignorecase=0,
                vim_infercase=1,
                keyword_base="pri",
                matches_input=u"PrIory prize PrIority priMary".split(),
                matches_result=u"PrIory prize PrIority priMary".split())

        self._helper_execute_infercase_test(
                vim_ignorecase=0,
                vim_infercase=0,
                keyword_base="pri",
                matches_input=u"PrIory prize PrIority priMary".split(),
                matches_result=u"PrIory prize PrIority priMary".split())

    def test_non_ascii_chars_are_transformed_if_conditions_are_met(self):

        self._helper_execute_infercase_test(
                vim_ignorecase=1,
                vim_infercase=1,
                keyword_base=u"\u00fcb",
                matches_input=u"\u00dcber \u00fcberfu\u00df".split(),
                matches_result=u"\u00fcber \u00fcberfu\u00df".split())

        self._helper_execute_infercase_test(
                vim_ignorecase=1,
                vim_infercase=1,
                keyword_base=u"\u00dcb",
                matches_input=u"\u00dcber \u00fcberfu\u00df".split(),
                matches_result=u"\u00dcber \u00dcberfu\u00df".split())


class TestGenerateHaystack(unittest.TestCase):

    def _helper_isolate_sut(self,
            match_result_order,
            expected_result_lines,
            buffer_content=("0", "1", "2", "3", "4", "5", "6"),
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
                expected_result_lines=["3", "2", "1", "5", "4"])

    def test_reversed_order(self):
        self._helper_isolate_sut(
                match_result_order=localcomplete.MATCH_ORDER_REVERSE,
                expected_result_lines=["5", "4", "3", "2", "1"])

    def test_forward_order(self):
        self._helper_isolate_sut(
                match_result_order=localcomplete.MATCH_ORDER_NORMAL,
                expected_result_lines=["1", "2", "3", "4", "5"])

    def test_forward_below_first_order(self):
        self._helper_isolate_sut(
                match_result_order=(
                        localcomplete.MATCH_ORDER_NORMAL_BELOW_FIRST),
                expected_result_lines=["3", "4", "5", "1", "2"])

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

    def test_empty_input_list_creates_an_empty_output_list(self):
        vim_mock = VimMockFactory.get_mock(show_origin=1)
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            actual_result = localcomplete.produce_result_value(
                    [], 'testorigin')
        expected_result = []
        self.assertEqual(actual_result, expected_result)

    def test_nonempty_with_origin_note(self):
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

    def test_nonempty_without_origin_note(self):
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

    def test_diverse_single_char_entries_in_iskeyword_are_found(self):
        vim_mock = VimMockFactory.get_mock(
                iskeyword='@,48-57,_,#,:,$%!,192-255')
        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            actual_result = (
                    localcomplete.get_additional_keyword_chars_from_vim())
        self.assertEqual(actual_result, '@_#:')

    def test_empty_result_without_single_char_entries_in_iskeyword(self):
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

    def test_non_empty_configuration_returned_as_is(self):
        self._helper_isolate_test_subject(
                expected_result=':#',
                keyword_chars=':#')

    def test_empty_configuration_returned_as_is(self):
        self._helper_isolate_test_subject(
                expected_result='',
                keyword_chars='')

    def test_special_configuration_value_delegates_char_obtainment(self):
        self._helper_isolate_test_subject(
                expected_result='.#',
                keyword_chars=self._select_from_vim,
                keyword_chars_from_vim='.#')


class TestTransmitLocalMatchResultToVim(unittest.TestCase):

    def test_argument_is_passed_through(self):
        produce_mock = mock.Mock(side_effect=lambda matches, origin : matches)
        vim_mock = VimMockFactory.get_mock(origin_note_local="undertest")
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
        infercase_mock = mock.Mock(
                side_effect=lambda keyword, matches : matches)
        transmit_result_mock = mock.Mock(spec_set=[], return_value=[])

        vim_mock = VimMockFactory.get_mock(
                encoding=encoding,
                min_len_local=min_len_local,
                keyword_base=keyword_base)

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                generate_haystack=haystack_mock,
                apply_infercase_to_matches_cond=infercase_mock,
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

    def test_find_additional_keyword_char_needing_escape(self):
        self._helper_completion_tests(
                haystack=" prize-money  prior\\art ",
                keyword_chars="-\\",
                keyword_base="pri",
                result_list=u"prize-money prior\\art".split())

    def test_find_keyword_base_needing_escape(self):
        self._helper_completion_tests(
                haystack=" pri$ze  pri$or ",
                keyword_base="pri$",
                result_list=u"pri$ze pri$or".split())

    def test_find_unicode_matches(self):
        self._helper_completion_tests(
                haystack=u"  \u00fcber \u00fcberfu\u00df  ".encode('utf-8'),
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())

    def test_find_matches_with_debugging_info(self):
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
        # The cursor_index can be after the full_line
        if cursor_index > len(full_line):
            raise LocalCompleteTestsError("cursor index not within line")
        vim_mock = VimMockFactory.get_mock(encoding="utf-8")
        vim_mock.current.line = full_line
        vim_mock.current.window.cursor = (0, cursor_index)

        with mock.patch(__name__ + '.localcomplete.vim', vim_mock):
            yield

    def test_helper__exception_raised_if_index_more_than_one_beyond_line(self):
        with self.assertRaises(LocalCompleteTestsError):
            self._helper_mock_current("x", 2).__enter__()

    def test_helper__exception_not_raised_if_index_one_beyond_line(self):
        self._helper_mock_current("x", 1).__enter__()

    def test_findstart_up_to_cursor(self):
        with self._helper_mock_current("abba", 2):
            actual_result = localcomplete.findstart_get_line_up_to_cursor()
        self.assertEqual(actual_result, u"ab")

    def test_findstart_in_an_empty_line(self):
        with self._helper_mock_current("", 0):
            actual_result = localcomplete.findstart_get_line_up_to_cursor()
        self.assertEqual(actual_result, u"")


class TestFindstartGetIndexOfTrailingKeyword(unittest.TestCase):

    def test_normal_keyword_in_the_middle(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                '', "abba yuhu")
        self.assertEqual(actual_index, 5)

    def test_return_None_if_there_is_no_keyword_before_the_cursor(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                '', "abba ")
        self.assertEqual(actual_index, None)

    def test_find_the_visible_index_when_unicode_characters_are_involved(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                u'', u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df")
        self.assertEqual(actual_index, 7)

    def test_when_there_are_additional_keyword_chars_involved(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                ':@', "abba y:u@hu")
        self.assertEqual(actual_index, 5)

    def test_when_escaping_is_needed(self):
        actual_index = localcomplete.findstart_get_index_of_trailing_keyword(
                '-\\', "abba y-u\\hu")
        self.assertEqual(actual_index, 5)


class TestFindstartGetStartingColumnIndex(unittest.TestCase):

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

    def test_normal_case_with_a_trailing_keyword(self):
        with self._helper_isolate_column_getter(line_start="ab b"):
            self.assertEqual(3,
                    localcomplete.findstart_get_starting_column_index())

    def test_trailing_space_returns_the_current_cursor_position(self):
        # The cursor is behind the string
        with self._helper_isolate_column_getter(line_start="ab b "):
            self.assertEqual(5,
                    localcomplete.findstart_get_starting_column_index())

    def test_unicode_keyword_after_nonunicode_start(self):
        line = u"uuuber \u00fcberfu\u00df"
        with self._helper_isolate_column_getter(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_unicode_linestart_with_nonunicode_keyword(self):
        line = u"\u00fc\u00fc\u00fcber uberfus"
        with self._helper_isolate_column_getter(line_start=line):
            self.assertEqual(7,
                    localcomplete.findstart_get_starting_column_index())

    def test_unicode_linestart_with_unicode_keyword(self):
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

    def test_translate_unicode_keywords_with_leading_multibytes(self):
        line = u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df"
        with self._helper_isolate_column_translator(line_start=line):
            self.assertEqual(10,
                    localcomplete.findstart_translate_to_byte_index(7))

    def test_translate_unicode_keyword_without_leading_multibytes(self):
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
            origin_note_dict='undertest',
            want_ignorecase=False,
            is_dictionary_configured=True,
            is_dictionary_path_valid=True):

        translated_content = os.linesep.join(dict_content.split())

        dictionary_path = 'test:nonempty' if is_dictionary_configured else ''

        content_mock = mock.Mock(spec_set=[], return_value=translated_content)

        case_mock_retval = re.IGNORECASE if want_ignorecase else 0
        case_mock = mock.Mock(spec_set=[], return_value=case_mock_retval)
        infercase_mock = mock.Mock(
                side_effect=lambda keyword, matches : matches)

        if not is_dictionary_path_valid:
            content_mock.side_effect = IOError("undertest")
        produce_mock = mock.Mock(spec_set=[], return_value=[])
        vim_mock = VimMockFactory.get_mock(
                origin_note_dict=origin_note_dict,
                encoding=encoding,
                keyword_base=keyword_base,
                dictionary=dictionary_path)

        with mock.patch.multiple(__name__ + '.localcomplete',
                read_file_contents=content_mock,
                produce_result_value=produce_mock,
                get_casematch_flag=case_mock,
                apply_infercase_to_matches_cond=infercase_mock,
                vim=vim_mock):

            yield (vim_mock, produce_mock)

    def _helper_completion_tests(self, result_list, **isolation_args):
        with self._helper_isolate_dict_matches(**isolation_args) as (
                vim_mock, produce_mock):

            localcomplete.complete_dictionary_matches()

        produce_mock.assert_called_once_with(result_list, mock.ANY)
        vim_mock.command.assert_called_once_with(mock.ANY)

    def test_find_dict_case_sensitive_matches(self):
        self._helper_completion_tests(
                dict_content=u"  priory prize none   Priority   primary  ",
                keyword_base="pri",
                want_ignorecase=False,
                result_list=u"priory prize primary".split())

    def test_find_dict_case_insensitive_matches(self):
        self._helper_completion_tests(
                dict_content=u"  priory prize none   Priority   primary  ",
                keyword_base="pri",
                want_ignorecase=True,
                result_list=u"priory prize Priority primary".split())

    def test_find_dict_unicode_matches(self):
        self._helper_completion_tests(
                dict_content=u" \u00fcber \u00fcberfu\u00df  ",
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())

    def test_find_dict_needing_escape(self):
        self._helper_completion_tests(
                dict_content=u"  pri$ory pri$ze none   Priority   primary  ",
                keyword_base="pri$",
                result_list=u"pri$ory pri$ze".split())

    def test_find_no_matches_without_a_configured_dictionary(self):
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


class TestGetAllBuffersInSearchOrder(unittest.TestCase):

    def _test_helper(self, buffer_numbers, current_index, ordered_numbers):

        if current_index < 0 or current_index >= len(buffer_numbers):
            raise LocalCompleteTestsError("current buffer index out of bounds")

        class VimBufferFake:
            def __init__(self, number):
                self.number = number
            def __eq__(self, number):
                return self.number == number
            def __repr__(self):
                return str(self.number)

        vim_mock = mock.Mock()
        vim_mock.buffers = []

        for idx, number in enumerate(buffer_numbers):
            vim_mock.buffers.append(VimBufferFake(number))
            if idx == current_index:
                vim_mock.current.buffer.number = number

        with mock.patch.multiple(__name__ + '.localcomplete',
                vim=vim_mock):
            buffer_list = localcomplete.get_all_buffers_in_search_order()
        self.assertEqual(buffer_list, ordered_numbers)

    def test_buffer_in_the_middle_first(self):
        self._test_helper(
                buffer_numbers=[3, 4, 5, 6, 7],
                current_index=2,
                ordered_numbers=[5, 4, 6, 3, 7])

    def test_first_buffer_is_current(self):
        self._test_helper(
                buffer_numbers=[3, 4, 5],
                current_index=0,
                ordered_numbers=[3, 4, 5])

    def test_last_buffer_is_current(self):
        self._test_helper(
                buffer_numbers=[5, 6, 7],
                current_index=2,
                ordered_numbers=[7, 6, 5])


class TestGenerateBufferLines(unittest.TestCase):

    @contextlib.contextmanager
    def _mock_out_search_order(self, buffers_content):

        search_order_mock = mock.Mock(return_value=buffers_content)

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_all_buffers_in_search_order=search_order_mock):
            yield

    def test_lines_of_buffers_become_one_sequence(self):
        with self._mock_out_search_order([
                "a b c".split(),
                "one".split(),
                "x y z".split(),
                ]):
            actual_result = list(localcomplete.generate_all_buffer_lines())
        self.assertEqual(actual_result, "a b c one x y z".split())


class TestTransmitAllBufferResultToVim(unittest.TestCase):

    def test_argument_is_passed_through(self):
        produce_mock = mock.Mock(side_effect=lambda matches, origin : matches)
        vim_mock = VimMockFactory.get_mock(origin_note_all_buffers="test")
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
        infercase_mock = mock.Mock(
                side_effect=lambda keyword, matches : matches)

        vim_mock = VimMockFactory.get_mock(
                min_len_all_buffer=min_len_all_buffer,
                encoding=encoding,
                keyword_base=keyword_base)

        with mock.patch.multiple(__name__ + '.localcomplete',
                get_additional_keyword_chars=chars_mock,
                get_casematch_flag=case_mock,
                generate_all_buffer_lines=buffers_mock,
                apply_infercase_to_matches_cond=infercase_mock,
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

    def test_find_matches_at_exactly_the_min_length_requirement(self):
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

    def test_find_additional_keyword_char_needing_escape(self):
        self._helper_completion_tests(
                buffers_contents=[" prize-money  prior\\art "],
                keyword_chars="-\\",
                keyword_base="pri",
                result_list=u"prize-money prior\\art".split())

    def test_find_keyword_base_needing_escape(self):
        self._helper_completion_tests(
                buffers_contents=[" pri$ze  pri$or "],
                keyword_base="pri$",
                result_list=u"pri$ze pri$or".split())

    def test_find_unicode_matches(self):
        self._helper_completion_tests(
                buffers_contents=[
                        u"  \u00fcber \u00fcberfu\u00df  ".encode('utf-8')
                        ],
                keyword_base=u"\u00fcb".encode('utf-8'),
                result_list=u"\u00fcber \u00fcberfu\u00df".split())

    def test_find_matches_with_debugging_info(self):
        isolation_args = dict(
                buffers_contents=["  priory prize none prized none primary  "],
                keyword_base="pri")
        result_list = u"priory prize prized primary".split()
        result_list.append(isolation_args['keyword_base'])
        with mock.patch.dict('os.environ', LOCALCOMPLETE_DEBUG="yes-nonempty"):
            self._helper_completion_tests(
                    result_list=result_list,
                    **isolation_args)
