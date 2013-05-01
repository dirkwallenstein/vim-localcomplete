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


import itertools
import os
import re
import string
import thirdparty
import vim

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

def join_buffer_lines(above_lines, current_lines, below_lines):
    """
    Join the lines passed as arguments in three lists in the order requested in
    the configuration.
    """
    want_reversed = int(vim.eval("g:localcomplete#WantReversedOrder"))
    want_centered = int(vim.eval("g:localcomplete#WantCenteredOrder"))
    if want_centered:
        above_reversed = reversed(above_lines)
        zipped_center = zip_flatten_longest(above_reversed, below_lines)
        ordered_lines = current_lines + list(zipped_center)
    else:
        ordered_lines = above_lines +  current_lines + below_lines
        if want_reversed:
            ordered_lines = list(reversed(ordered_lines))
    return os.linesep.join(ordered_lines)

def get_buffer_indexes():
    """
    Calculate the (first, current, last) indexes of buffer lines requested
    through the configuration and return that tuple.
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

    return (first_index, current_index, last_index)

def get_haystack(first_index, current_index, last_index):
    """
    Return the string that should be searched according to the indexes.

    Let join_buffer_lines do the ordering.
    """
    above_lines = vim.current.buffer[first_index:current_index]
    current_lines = [vim.current.buffer[current_index]]
    below_lines = vim.current.buffer[(current_index+1):(last_index+1)]

    haystack = join_buffer_lines(
            above_lines=above_lines,
            current_lines=current_lines,
            below_lines=below_lines)
    return haystack

def produce_result_value(matches_list, origin_note):
    """
    Translate the list of matches passed as argument, into a list of
    dictionaries accepted as completion function result.

    For possible entries see the Vim documentation *complete-items*
    """
    want_show_origin = int(vim.eval("g:localcomplete#ShowOriginNote"))
    result_list = []
    for match in matches_list:
        new_match_dict = {"word": thirdparty.PythonToVimStr(match)}
        if want_show_origin:
            new_match_dict["menu"] = origin_note
        result_list.append(new_match_dict)
    return result_list

def get_additional_keyword_chars():
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

def get_casematch_flag():
    """
    Return the re.IGNORECASE or 0 depending on the config request
    """
    if int(vim.eval("g:localcomplete#WantIgnoreCase")):
        return re.IGNORECASE
    else:
        return 0

def complete_local_matches():
    """
    Return a local completion result for a:keyword_base
    """
    encoding = vim.eval("&encoding")
    keyword_base = vim.eval("a:keyword_base").decode(encoding)
    punctuation_chars = get_additional_keyword_chars().decode(encoding)
    casematch_flag = get_casematch_flag()

    # Note: theoretically there could be a non-alphanumerical character at the
    # leftmost position.
    needle = re.compile(r'\b%s[\w%s]+' % (keyword_base, punctuation_chars),
            re.UNICODE|casematch_flag)

    buffer_indexes = get_buffer_indexes()
    haystack = get_haystack(*buffer_indexes).decode(encoding)
    found_matches = needle.findall(haystack)

    if os.environ.get("LOCALCOMPLETE_DEBUG") is not None:
        fake_matches = found_matches[:]
        fake_matches += [str(item + 1) for item in buffer_indexes]
        fake_matches.append(haystack)
        found_matches = fake_matches

    vim.command('silent let s:__localcomplete_lookup_result = %s'
            % repr(produce_result_value(found_matches, "<< localcomplete")))


def complete_dictionary_matches():
    """
    Return a dictionary completion result for a:keyword_base
    """
    encoding = vim.eval("&encoding")
    keyword_base = vim.eval("a:keyword_base").decode(encoding)

    dictionary_file = vim.eval("&dictionary")
    if dictionary_file:
        # Case insensitive matches are useless here, unless reordered first.
        # Would find all the uppercase names before the normal words
        needle = re.compile(r'^%s\w+' % keyword_base, re.UNICODE|re.MULTILINE)
        try:
            with open(dictionary_file, "r") as fr:
                haystack = fr.read()
        except IOError as err:
            vim.command('echoerr "Error reading dictionary: %s"' % str(err))
            haystack = ''
        haystack = haystack.decode(encoding)
        found_matches = needle.findall(haystack)
    else:
        found_matches = []

    vim.command('silent let s:__dictcomplete_lookup_result = %s'
            % repr(produce_result_value(found_matches, "<* dict")))
