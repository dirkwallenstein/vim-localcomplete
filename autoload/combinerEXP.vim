" This program is free software: you can redistribute it and/or modify
" it under the terms of the GNU Lesser General Public License as published by
" the Free Software Foundation, either version 3 of the License, or
" (at your option) any later version.
"
" This program is distributed in the hope that it will be useful,
" but WITHOUT ANY WARRANTY; without even the implied warranty of
" MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
" GNU General Public License for more details.
"
" You should have received a copy of the GNU Lesser General Public License
" along with this program.  If not, see <http://www.gnu.org/licenses/>.

if (exists("g:loaded_combinerEXP") && g:loaded_combinerEXP)
    finish
endif
let g:loaded_combinerEXP = 1

if ! exists( "g:combinerEXP#WantCursorShowsError" )
    " When there are completion errors encountered (currently only Rope),
    " change the 'Cursor' highlight to indicate erroneous states.  The color
    " will be restored when leaving the insert mode.
    let g:combinerEXP#WantCursorShowsError = 1
endif

if ! exists( "g:combinerEXP#CursorColorNormal" )
    " Use this color to link the Cursor color with in the normal case
    let g:combinerEXP#CursorColorNormal = 'Cursor'
endif

if ! exists( "g:combinerEXP#CursorColorError" )
    " Use this color to link the Cursor color with in case of an error
    let g:combinerEXP#CursorColorError = 'Error'
endif

" ----------------------------------------------

" Autocomands
" -----------
if g:combinerEXP#WantCursorShowsError
    augroup localcompleteautocommands
        " delete all autocommands for this group only...
        autocmd!
        " restore Cursor color when leaving insert mode
        autocmd InsertLeave * execute "hi! link Cursor "
                    \ . g:combinerEXP#CursorColorNormal
    augroup END
endif

" Combiners
" ---------

function combinerEXP#completeCombinerABSTRACT(findstart, keyword_base,
            \ all_completers, findstarter_index)
    " A completion function combiner.  Pass completion functions in a list as
    " third argument and the results will be combined in order.  Specify an
    " index into all_completers to select the completion function to be used
    " during the findstart mode.
    if a:findstart
        return eval(a:all_completers[a:findstarter_index] .
                    \ "(a:findstart, a:keyword_base)")
    else
        let l:combined_result = []
        for l:completer in a:all_completers
            let l:next_matches = eval(completer
                        \ . "(a:findstart, a:keyword_base)")
            let l:combined_result = extend(l:combined_result, l:next_matches)
        endfor
        return l:combined_result
    endif
endfunction

function s:is_known_rope_bug()
    " Check for known rope errors.
    " If there are multibyte characters before the keyword, ropevim returns
    " the wrong column.  Check the whole line anyway.
    let l:current_line = getline('.')
    if len(l:current_line) != strwidth(l:current_line)
        return 1
    endif
    " Inside comments rope always returns the current column
    let l:comment_index = match(getline('.'), '#')
    if l:comment_index < 0
        return 0
    endif
    let l:current_index = col('.') - 1
    if l:comment_index <= l:current_index
        return 1
    endif
    return 0
endfunction

function combinerEXP#RopeOmniSilenced(findstart, keyword_base)
    " If you encounter errors during RopeOmni that you want to suppress, use
    " this function.
    try
        return RopeOmni(a:findstart, a:keyword_base)
    catch /.*/
        echomsg "error caught in rope"
    endtry
    if a:findstart
        let l:message_prefix = "caught exeception (rope/findstart) "
    else
        let l:message_prefix = "caught exeception (rope/suggestions) "
    endif
    redraw | echohl WarningMsg |
                \ echomsg l:message_prefix
                \ . v:exception | echohl None
    if g:combinerEXP#WantCursorShowsError
        execute "hi! link Cursor " . g:combinerEXP#CursorColorError
    endif
    if a:findstart
        " Special return values:
        " -1 If no completion can be done, the completion will be cancelled
        "    with an error message.
        " -2 To cancel silently and stay in completion mode.
        " -3 To cancel silently and leave completion mode.
        return -2
    else
        return []
    endif
endfunction

function combinerEXP#ropeCombiner(
            \ findstart,
            \ keyword_base,
            \ before_rope,
            \ after_rope,
            \ findstarter_index)
    " A completion combiner for Python that works around issues combining
    " RopeOmni with other completion functions.  It always calls RopeOmni
    " during findstart mode (which is required) and uses RopeOmniSilenced just
    " in case any errors reach us here.
    " Pass in the completion functions that should be attempted before/after
    " rope as lists in before_rope and after_rope.
    " The findstarter_index is an index into the concatenation of the before and
    " after lists and is passed to combinerEXP#completeCombinerABSTRACT.  If
    " you pass in -1, the starting column from RopeOmni is used.
    if a:findstart
        " This call is necessary.  I think rope expects the two calls in tandem.
        let l:rope_column = combinerEXP#RopeOmniSilenced(
                    \ a:findstart, a:keyword_base)
        if a:findstarter_index == -1
            return l:rope_column
        endif
        " Return the column of the requested completion function
        let l:all_other_completers = a:before_rope + a:after_rope
        if len(l:all_other_completers) < 1
            throw "You need at least one additional completer here"
        endif
        return combinerEXP#completeCombinerABSTRACT(
                    \ a:findstart,
                    \ a:keyword_base,
                    \ l:all_other_completers,
                    \ a:findstarter_index)
    else
        let l:before_rope_results = []
        let l:after_rope_results = []
        for l:bcompleter in a:before_rope
            let l:next_results = eval(l:bcompleter
                        \ . "(a:findstart, a:keyword_base)")
            let l:before_rope_results = l:before_rope_results + l:next_results
        endfor
        for l:acompleter in a:after_rope
            let l:next_results = eval(l:acompleter
                        \ . "(a:findstart, a:keyword_base)")
            let l:after_rope_results = l:after_rope_results + l:next_results
        endfor
        if s:is_known_rope_bug()
            let l:rope_result = []
        else
            let l:rope_result = combinerEXP#RopeOmniSilenced(a:findstart,
                        \ a:keyword_base)
        endif
        return l:before_rope_results + l:rope_result + l:after_rope_results
    endif
endfunction

function combinerEXP#completeCombinerPython(findstart, keyword_base)
    " A completion function combiner example that searches locally and in all
    " buffers after RopeOmni.
    let l:before_rope = []
    let l:after_rope = [
                \ 'localcomplete#localMatches',
                \ 'localcomplete#allBufferMatches',
                \ ]
    return combinerEXP#ropeCombiner(
                \ a:findstart,
                \ a:keyword_base,
                \ l:before_rope,
                \ l:after_rope,
                \ 0)
endfunction

function combinerEXP#completeCombinerTextish(findstart, keyword_base)
    " A completion function combiner that searches local, buffer and
    " dictionary matches.  Note that you can add the dictionary matches much
    " later by configuring the minimum prefix length and checkpoints.
    let l:all_completers = [
                \ 'localcomplete#localMatches',
                \ 'localcomplete#allBufferMatches',
                \ 'localcomplete#dictMatches',
                \ ]
    return combinerEXP#completeCombinerABSTRACT(
                \ a:findstart,
                \ a:keyword_base,
                \ l:all_completers,
                \ 0)
endfunction
