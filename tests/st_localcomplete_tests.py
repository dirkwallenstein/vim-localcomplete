import contextlib
import mock
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
            want_ignorecase=False,
            show_origin=False,
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
                result_list=[u'p-ick', u'P-imary', u'p-ize', u'p-iory'],
                buffer_content=(
                        "p-iory p-ize P-imary "
                        "primel Priest p-ick".split()),
                current_line_index=3,
                keyword_base='p-i',
                above_count=100,
                below_count=100,
                match_result_order=(
                        localcomplete.MATCH_ORDER_REVERSE),
                want_ignorecase=True,
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
