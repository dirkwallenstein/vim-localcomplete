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
This module implements the completions and a findstart mode for the completions
in the Vim-Script file of the same name.
"""

import codecs
import itertools
import os
import re
import string
import thirdparty
import vim

VIM_COMMAND_LOCALCOMPLETE = 'silent let s:__localcomplete_lookup_result = %s'
VIM_COMMAND_BUFFERCOMPLETE = 'silent let s:__buffercomplete_lookup_result = %s'
VIM_COMMAND_DICTCOMPLETE = 'silent let s:__dictcomplete_lookup_result = %s'
VIM_COMMAND_FINDSTART = (
        'silent let s:__localcomplete_lookup_result_findstart = %d')

SPECIAL_VALUE_SELECT_VIM_KEYWORDS = "&iskeyword"

# Constants that describe the requested result order
MATCH_ORDER_CENTERED = 1
MATCH_ORDER_NORMAL = 2
MATCH_ORDER_REVERSE = 3
MATCH_ORDER_NORMAL_BELOW_FIRST = 4
MATCH_ORDER_REVERSE_ABOVE_FIRST = 5


class LocalCompleteError(Exception):
    """
    The base exception for this module.
    """

def zip_flatten_longest(above_lines, below_lines):
    """
    Generate items from both argument lists in alternating order plus the items
    from the tail of the longer one.
    """
    for above, below in itertools.izip_longest(above_lines, below_lines):
        if above is not None:
            yield above
        if below is not None:
            yield below

def generate_haystack():
    match_result_order = int(vim.eval("localcomplete#getMatchResultOrder()"))
    above_indexes, current_index, below_indexes = get_buffer_ranges()

    # an alias for Vim's current buffer
    buf = vim.current.buffer

    if match_result_order == MATCH_ORDER_CENTERED:
        yield buf[current_index]
        for i in zip_flatten_longest(reversed(above_indexes), below_indexes):
            yield buf[i]

    elif match_result_order == MATCH_ORDER_REVERSE_ABOVE_FIRST:
        yield buf[current_index]
        for i in reversed(above_indexes):
            yield buf[i]
        for i in reversed(below_indexes):
            yield buf[i]

    elif match_result_order == MATCH_ORDER_REVERSE:
        for i in reversed(below_indexes):
            yield buf[i]
        yield buf[current_index]
        for i in reversed(above_indexes):
            yield buf[i]

    elif match_result_order == MATCH_ORDER_NORMAL:
        for i in above_indexes:
            yield buf[i]
        yield buf[current_index]
        for i in below_indexes:
            yield buf[i]

    elif match_result_order == MATCH_ORDER_NORMAL_BELOW_FIRST:
        yield buf[current_index]
        for i in below_indexes:
            yield buf[i]
        for i in above_indexes:
            yield buf[i]

    else:
        raise LocalCompleteError(
                "localcomplete: Invalid result order specified")

def get_buffer_ranges():
    """
    Calculate the (above_indexes, current_index, below_indexes) index and
    index-lists of buffer lines requested through the configuration and return
    that tuple.
    """
    prev_line_count = int(vim.eval("localcomplete#getLinesAboveCount()"))
    ahead_line_count = int(vim.eval("localcomplete#getLinesBelowCount()"))

    current_index = int(vim.eval("line('.')")) - 1
    last_line_index = int(vim.eval("line('$')")) - 1

    if prev_line_count < 0:
        first_index = 0
    else:
        first_index = max(0, current_index - prev_line_count)

    if ahead_line_count < 0:
        last_index = last_line_index
    else:
        last_index = min(last_line_index, current_index + ahead_line_count)

    return (range(first_index, current_index),
            current_index,
            range(current_index + 1, last_index + 1))

def produce_result_value(matches_list, origin_note):
    """
    Translate the list of matches passed as argument, into a list of
    dictionaries accepted as completion function result.

    For possible entries see the Vim documentation *complete-items*
    """
    want_show_origin = int(vim.eval("localcomplete#getWantOriginNote()"))
    result_list = []
    for match in matches_list:
        new_match_dict = {"word": thirdparty.PythonToVimStr(match)}
        if want_show_origin:
            new_match_dict["menu"] = origin_note
        result_list.append(new_match_dict)
    return result_list

def get_additional_keyword_chars_from_vim():
    """
    Scan &iskeyword for single char entries that are punctuation and return
    them as one string.

    Not perfect but works.
    """
    iskeyword_option = vim.eval("&iskeyword")
    punctuation_set = set(string.punctuation)
    found_chars = []
    for keyword_spec in iskeyword_option.split(","):
        if len(keyword_spec) != 1:
            continue
        if keyword_spec in punctuation_set:
            found_chars.append(keyword_spec)
    return ''.join(found_chars)

def get_additional_keyword_chars():
    keyword_spec = vim.eval("localcomplete#getAdditionalKeywordChars()")
    if keyword_spec == SPECIAL_VALUE_SELECT_VIM_KEYWORDS:
        return get_additional_keyword_chars_from_vim()
    return keyword_spec

def get_casematch_flag():
    """
    Return the re.IGNORECASE or 0 depending on the config request
    """
    if int(vim.eval("localcomplete#getWantIgnoreCase()")):
        return re.IGNORECASE
    else:
        return 0

def transmit_local_matches_result_to_vim(found_matches):
    origin_note = vim.eval("g:localcomplete#OriginNoteLocalcomplete")
    vim.command(VIM_COMMAND_LOCALCOMPLETE
            % repr(produce_result_value(
                    found_matches,
                    origin_note)))

def complete_local_matches():
    """
    Return a local completion result for a:keyword_base
    """
    encoding = vim.eval("&encoding")
    keyword_base = vim.eval("a:keyword_base").decode(encoding)
    min_length_keyword_base = int(vim.eval(
            "localcomplete#getLocalMinPrefixLength()"))
    if len(keyword_base) < min_length_keyword_base:
        transmit_local_matches_result_to_vim([])
        return

    punctuation_chars = get_additional_keyword_chars().decode(encoding)
    casematch_flag = get_casematch_flag()

    # Note: theoretically there could be a non-alphanumerical character at the
    # leftmost position.
    needle = re.compile(r'\b%s[\w%s]+' % (keyword_base, punctuation_chars),
            re.UNICODE|casematch_flag)

    found_matches = []
    for buffer_line in generate_haystack():
        found_matches.extend(needle.findall(buffer_line.decode(encoding)))

    if os.environ.get("LOCALCOMPLETE_DEBUG") is not None:
        fake_matches = found_matches[:]
        fake_matches.append(keyword_base)
        found_matches = fake_matches

    transmit_local_matches_result_to_vim(found_matches)

def findstart_get_line_up_to_cursor():
    encoding = vim.eval("&encoding")
    cursor_byte_index = vim.current.window.cursor[1]
    return vim.current.line[:cursor_byte_index].decode(encoding)

def findstart_get_index_of_trailing_keyword(keyword_chars, line_start):
    needle = re.compile(r'[\w%s]+$' % (keyword_chars),
            re.UNICODE|re.IGNORECASE)
    match_object = needle.search(line_start)
    if match_object is None:
        return None
    else:
        return match_object.start()

def findstart_get_starting_column_index():
    encoding = vim.eval("&encoding")
    punctuation_chars = get_additional_keyword_chars().decode(encoding)
    line_start = findstart_get_line_up_to_cursor()

    index_result = findstart_get_index_of_trailing_keyword(
            punctuation_chars, line_start)

    if index_result is None:
        return len(line_start)
    else:
        return index_result

def findstart_translate_to_byte_index(column_index):
    """
    Quick (meaning slow) workaround for findstart

    I thought Vim is looking for a visible column index into the line, but it
    wants the byte index.
    """
    encoding = vim.eval("&encoding")
    visible_line = findstart_get_line_up_to_cursor()[:column_index]
    return len(visible_line.encode(encoding))

def findstart_local_matches():
    vim.command(VIM_COMMAND_FINDSTART
            % findstart_translate_to_byte_index(
                    findstart_get_starting_column_index()))

def read_file_contents(file_path):
    with codecs.open(file_path, "r", encoding="utf-8") as fr:
        return fr.read()

def get_casematch_flag_for_dictionary_lookup():
    """
    Return the re.IGNORECASE or 0 depending on the configuration request for
    the dictionary lookup.
    """
    if int(vim.eval("localcomplete#getWantIgnoreCaseDict()")):
        return re.IGNORECASE
    else:
        return 0

def complete_dictionary_matches():
    """
    Return a dictionary completion result for a:keyword_base
    """
    encoding = vim.eval("&encoding")
    keyword_base = vim.eval("a:keyword_base").decode(encoding)

    dictionary_file = vim.eval("&dictionary")
    if dictionary_file:
        casematch_flag = get_casematch_flag_for_dictionary_lookup()
        needle = re.compile(r'^%s\w+' % keyword_base,
                re.UNICODE|re.MULTILINE|casematch_flag)
        try:
            haystack = read_file_contents(dictionary_file)
        except IOError as err:
            vim.command('echoerr "Error reading dictionary: %s"' % str(err))
            haystack = u''
        found_matches = needle.findall(haystack)
    else:
        found_matches = []

    origin_note = vim.eval("g:localcomplete#OriginNoteDictionary")
    vim.command(VIM_COMMAND_DICTCOMPLETE
            % repr(produce_result_value(
                    found_matches,
                    origin_note)))

def get_current_buffer_index():
    current_buffer_number = vim.current.buffer.number
    for index, vimbuffer in enumerate(vim.buffers):
        if vimbuffer.number == current_buffer_number:
            return index

def generate_buffers_search_order():
    current_buffer_index = get_current_buffer_index()
    yield current_buffer_index
    for i in zip_flatten_longest(
            range(current_buffer_index - 1, -1, -1),
            range(current_buffer_index + 1, len(vim.buffers))):
        yield i

def generate_all_buffer_lines():
    for index in generate_buffers_search_order():
        for line in vim.buffers[index]:
            yield line

def transmit_all_buffer_result_to_vim(found_matches):
    origin_note = vim.eval("g:localcomplete#OriginNoteAllBuffers")
    vim.command(VIM_COMMAND_BUFFERCOMPLETE
            % repr(produce_result_value(
                    found_matches,
                    origin_note)))

def complete_all_buffer_matches():
    """
    Return a completion result for a:keyword_base searched in all buffers
    """
    encoding = vim.eval("&encoding")
    keyword_base = vim.eval("a:keyword_base").decode(encoding)
    min_length_keyword_base = int(vim.eval(
            "localcomplete#getAllBufferMinPrefixLength()"))
    if len(keyword_base) < min_length_keyword_base:
        transmit_all_buffer_result_to_vim([])
        return

    punctuation_chars = get_additional_keyword_chars().decode(encoding)
    casematch_flag = get_casematch_flag()

    # Note: theoretically there could be a non-alphanumerical character at the
    # leftmost position.
    needle = re.compile(r'\b%s[\w%s]+' % (keyword_base, punctuation_chars),
            re.UNICODE|casematch_flag)

    found_matches = []
    for buffer_line in generate_all_buffer_lines():
        found_matches.extend(needle.findall(buffer_line.decode(encoding)))

    transmit_all_buffer_result_to_vim(found_matches)
