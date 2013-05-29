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
import mock
import os
import unittest


# Import Test Utils
from tests.lc_testutils import VimMockFactory
from tests.lc_testutils import fix_vim_module

# Import localcomplete
fix_vim_module()
from pylibs import localcomplete


class SystemTestCompleteLocalMatches(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_sut(self,
            buffer_content,
            current_line_index,
            keyword_base,
            **further_vim_mock_args):

        vim_mock_defaults = dict(
            above_count=-1,
            below_count=-1,
            match_result_order=localcomplete.MATCH_ORDER_CENTERED,
            want_ignorecase=0,
            vim_ignorecase=1,
            vim_infercase=1,
            show_origin=0,
            origin_note_local='undertest',
            min_len_local=0,
            encoding='utf-8',
            iskeyword='',
            keyword_chars='',
            )

        vim_mock_args = dict(vim_mock_defaults)
        vim_mock_args.update(further_vim_mock_args)

        produce_mock = mock.Mock(spec_set=[], return_value=[])
        vim_mock = VimMockFactory.get_mock(
                buffer_content=buffer_content,
                current_line_index=current_line_index,
                keyword_base=keyword_base,
                **vim_mock_args)

        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock,
                vim=vim_mock):
            yield produce_mock

    def _helper_completion_tests(self,
            result_list,
            **isolation_args):

        with self._helper_isolate_sut(**isolation_args
                ) as produce_mock:
            localcomplete.complete_local_matches()
        produce_mock.assert_called_once_with(result_list, mock.ANY)

    def test_system_multiline_matches_of_the_whole_file(self):
        self._helper_completion_tests(
                result_list=[u'prize', u'prized', u'priory', u'primary'],
                buffer_content="priory prize none prized none primary".split(),
                current_line_index=2,
                keyword_base='pri')

    def test_system_reverse_above_first_with_limited_range(self):
        self._helper_completion_tests(
                result_list=[u'primary', u'prized', u'prize',
                        u'priest' ,u'primel'],
                buffer_content=(
                        "priory prize prized primary "
                        "primel priest prick".split()),
                current_line_index=3,
                keyword_base='pri',
                above_count=2,
                below_count=2,
                match_result_order=(
                        localcomplete.MATCH_ORDER_REVERSE_ABOVE_FIRST))

    def test_adding_special_chars_ignoring_case(self):
        self._helper_completion_tests(
                result_list=[u'p-ick', u'p-imary', u'p-ize', u'p-iory'],
                buffer_content=(
                        "P-Iory p-ize P-imary "
                        "primel Priest p-ick".split()),
                current_line_index=3,
                keyword_base='p-i',
                above_count=100,
                below_count=100,
                match_result_order=(
                        localcomplete.MATCH_ORDER_REVERSE),
                want_ignorecase=1,
                keyword_chars='-')

    def test_additional_keywords_from_vim(self):
        self._helper_completion_tests(
                result_list=u"priory pri:e pri:ed primary ".split(),
                buffer_content=("priory pri:e pri:ed primary ".split()),
                current_line_index=3,
                keyword_base='pri',
                match_result_order=(localcomplete.MATCH_ORDER_NORMAL),
                keyword_chars=localcomplete.SPECIAL_VALUE_SELECT_VIM_KEYWORDS,
                iskeyword='@,48-57,:,192-255')


class SystemTestFindstart(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_sut(self,
            line_up_to_cursor,
            encoding='utf-8',
            keyword_chars=''):

        line_mock = mock.Mock(spec_set=[], return_value=line_up_to_cursor)
        vim_mock = VimMockFactory.get_mock(
                keyword_chars=keyword_chars,
                encoding=encoding)

        with mock.patch.multiple(__name__ + '.localcomplete',
                findstart_get_line_up_to_cursor=line_mock,
                vim=vim_mock):
            yield vim_mock

    def _helper_completion_tests(self,
            byte_index_result,
            **isolation_args):

        with self._helper_isolate_sut(**isolation_args
                ) as vim_mock:
            localcomplete.findstart_local_matches()
        expected_result = (
                localcomplete.VIM_COMMAND_FINDSTART % byte_index_result)
        vim_mock.command.assert_called_once_with(expected_result)

    def test_findstart_simple(self):
        self._helper_completion_tests(
                byte_index_result=9,
                line_up_to_cursor="complete thi")

    def test_findstart_multibytes(self):
        self._helper_completion_tests(
                byte_index_result=10,
                line_up_to_cursor=u"\u00fc\u00fc\u00fcber \u00fcberfu\u00df")


class SystemTestDictionarySearch(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_sut(self,
            dict_content,
            keyword_base,
            **further_vim_mock_args):
        """
        dict_content is one string that will be split at whitespace to
        replicate the format of a Vim dictionary.
        """

        # merge arguments
        vim_mock_defaults = dict(
                encoding='utf-8',
                show_origin=0,
                want_ignorecase_dict=0,
                vim_ignorecase=1,
                vim_infercase=1,
                origin_note_dict="undertest",
                dictionary="nonempty-valid",
                )

        vim_mock_args = dict(vim_mock_defaults)
        vim_mock_args.update(further_vim_mock_args)

        # prepare mocks
        translated_content = os.linesep.join(dict_content.split())
        codecs_open_mock = mock.mock_open(read_data=translated_content)

        vim_mock = VimMockFactory.get_mock(
                keyword_base=keyword_base,
                **vim_mock_args)

        # patch and yield
        with mock.patch(__name__ + '.localcomplete.codecs.open',
                codecs_open_mock,
                create=True):
            with mock.patch.multiple(__name__ + '.localcomplete',
                    vim=vim_mock):
                yield vim_mock

    def test_standard_case_sensitive_search(self):
        produce_mock = mock.Mock(spec_set=[], return_value=[])
        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock):
            with self._helper_isolate_sut(
                    dict_content=u"priory prize none Priority primary",
                    keyword_base="pri") as vim_mock:
                localcomplete.complete_dictionary_matches()

        result_list=u"priory prize primary".split()
        produce_mock.assert_called_once_with(result_list, mock.ANY)
        self.assertEqual(vim_mock.command.call_count, 1)

    def test_case_insensitive_search_with_infercase(self):
        produce_mock = mock.Mock(spec_set=[], return_value=[])
        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock):
            with self._helper_isolate_sut(
                    dict_content=u"priory PRIze none Priority prIMary",
                    keyword_base="PrI",
                    want_ignorecase_dict=1) as vim_mock:
                localcomplete.complete_dictionary_matches()

        result_list=u"PrIory PrIze PrIority PrIMary".split()
        produce_mock.assert_called_once_with(result_list, mock.ANY)
        self.assertEqual(vim_mock.command.call_count, 1)



class SystemTestAllBufferSearch(unittest.TestCase):

    @contextlib.contextmanager
    def _helper_isolate_sut(self,
            buffers_content,
            current_buffer_index,
            keyword_base,
            **further_vim_mock_args):

        vim_mock_defaults = dict(
            want_ignorecase=0,
            vim_ignorecase=1,
            vim_infercase=1,
            show_origin=0,
            origin_note_all_buffers="undertest",
            encoding='utf-8',
            min_len_all_buffer=0,
            iskeyword='',
            keyword_chars='',
            )

        # setup a vim mock with explicit and default arguments

        vim_mock_args = dict(vim_mock_defaults)
        vim_mock_args.update(further_vim_mock_args)

        vim_mock = VimMockFactory.get_mock(
                keyword_base=keyword_base,
                **vim_mock_args)

        # Mock out vim_mock.buffers

        class VimBufferFake(list):
            number = None

        mock_buffers = []
        for index, content in enumerate(buffers_content):
            new_buffer = VimBufferFake(content)
            new_buffer.number = index
            mock_buffers.append(new_buffer)
            if index == current_buffer_index:
                vim_mock.current = mock.Mock()
                vim_mock.current.buffer = new_buffer
        vim_mock.buffers = mock_buffers

        # patch and yield

        with mock.patch.multiple(__name__ + '.localcomplete',
                vim=vim_mock):
            yield vim_mock

    def test_standard_search_across_multiple_buffers(self):
        isolation_args = dict(
                buffers_content = [
                        "ONEa two".split(),
                        "",
                        "x y onez".split(),
                        "",
                        "a oneb c".split(),
                        ""
                        ],
                want_ignorecase=1,
                current_buffer_index=2,
                keyword_base="one")
        result_list = u"onez onea oneb".split()

        produce_mock = mock.Mock(spec_set=[], return_value=[])
        with mock.patch.multiple(__name__ + '.localcomplete',
                produce_result_value=produce_mock):
            with self._helper_isolate_sut(
                    **isolation_args) as vim_mock:
                localcomplete.complete_all_buffer_matches()

        produce_mock.assert_called_once_with(result_list, mock.ANY)
        self.assertEqual(vim_mock.command.call_count, 1)

    def test_final_vim_result_command_without_origin_note(self):
        isolation_args = dict(
            buffers_content = [
                    "onea two".split(),
                    "x y onez".split(),
                    "",
                    "a oneb c".split(),
                    ],
            current_buffer_index=0,
            show_origin=0,
            keyword_base="one")
        result_value = ("""[{'word': "onea"}, """
                """{'word': "onez"}, {'word': "oneb"}]""")

        with self._helper_isolate_sut(
                **isolation_args
                ) as vim_mock:
            localcomplete.complete_all_buffer_matches()

        result_command = (localcomplete.VIM_COMMAND_BUFFERCOMPLETE
                % result_value)
        vim_mock.command.assert_called_once_with(result_command)
