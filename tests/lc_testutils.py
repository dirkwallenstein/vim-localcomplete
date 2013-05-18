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

"""
Testing utilities that help working with the vim module.
"""

import mock
import sys


class LCTestUtilsError(Exception):
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
            side_effect=LCTestUtilsError(
            "ERROR: no mock provided for the module 'vim'"))
    type(message_mock).current = attribute_exception
    type(message_mock).command = attribute_exception
    type(message_mock).eval = attribute_exception
    sys.modules['vim'] = message_mock


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
        min_len_all_buffer = "localcomplete#getAllBufferMinPrefixLength()",
        min_len_local = "localcomplete#getLocalMinPrefixLength()",
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
                spec_set=['eval', 'command', 'current', 'buffers'])
        vim_mock.eval = mock.Mock(spec_set=[],
                side_effect=factory_instance.eval_mocker)
        vim_mock.command = mock.Mock(spec_set=[])
        vim_mock.current = mock.NonCallableMock(
                spec_set=['buffer', 'line', 'window'])
        if buffer_content is None:
            type(vim_mock.current).buffer = mock.PropertyMock(
                    side_effect=LCTestUtilsError(
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
            raise LCTestUtilsError("Invalid config keys: %s"
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
            return "%s" % str(self.eval_results[expression])
        except KeyError:
            raise LCTestUtilsError("No eval result recorded for '%s'"
                    % expression)
