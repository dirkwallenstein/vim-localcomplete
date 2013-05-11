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

if (exists("g:loaded_combinerEXP") && g:loaded_combinerEXP)
    finish
endif
let g:loaded_combinerEXP = 1

if ! exists( "g:combinerEXP#WantCursorShowsError" )
    " When there are completion errors encountered (currently only Rope), use
    " the cursor color configuration to switch between normal an erroneous
    " states.
    let g:combinerEXP#WantCursorShowsError = 0
endif

if ! exists( "g:combinerEXP#CursorColorNormal" )
    " Use this color to link the Cursor color with in the normal case
    let g:combinerEXP#CursorColorNormal = 'Cursor'
endif

if ! exists( "g:combinerEXP#CursorColorError" )
    " Use this color to link the Cursor color with in case of an error
    let g:combinerEXP#CursorColorError = 'Error'
endif

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

function combinerEXP#completeCombinerABSTRACT(findstart, keyword_base, all_completers)
    " completion combiner implementor.  Pass 2 or more completers in a list as
    " third argument and the results will be combined.  All completers have to
    " find the same column in the findstart mode.  Pick one to compute the
    " column in your own wrapper if that is not possible.
    if len(a:all_completers) < 2
        throw "Called with less than 2 completers"
    endif
    if a:findstart
        let l:result_column = -1
        for l:completer in a:all_completers
            let l:next_column = eval(completer . "(a:findstart, a:keyword_base)")
            if l:result_column == -1
                let l:result_column = l:next_column
            else
                if l:next_column != l:result_column
                    throw l:completer . " completion result(" . l:next_column
                                \. ") not equal to previous result("
                                \. l:result_column . ")"
                endif
            endif
        endfor
        return l:result_column
    else
        let l:combined_result = []
        for l:completer in a:all_completers
            let l:next_matches = eval(completer . "(a:findstart, a:keyword_base)")
            let l:combined_result = extend(l:combined_result, l:next_matches)
        endfor
        return l:combined_result
    endif
endfunction

" Check for known rope errors
function s:is_known_rope_bug()
    " if there are mb-character before the keyword, ropevim returns the wrong
    " column.  Check the whole line anyway.
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

" A completion combiner for Python that works around ropevim bugs
function combinerEXP#completeCombinerPython(findstart, keyword_base)
    if a:findstart
        let l:dc_column = localcomplete#localMatches(a:findstart, a:keyword_base)
        try
            let l:rope_column = RopeOmni(a:findstart, a:keyword_base)
        catch /.*/
            redraw | echohl WarningMsg |
                        \ echomsg "caught exeception (rope/findstart)"
                        \ . v:exception | echohl None
            return l:dc_column
        endtry
        " If there is a mismatch, check if it is a known rope bug
        " XXX Uncomment if you want to be informed about ropevim errors
        "if l:dc_column != l:rope_column
        "    if !s:is_known_rope_bug()
        "        throw "completeCombinerPython: unequal columns computed: dc("
        "                \ . l:dc_column . ") rope(" . l:rope_column . ")"
        "    endif
        "endif
        return l:dc_column
    else
        " ropevim returns invalid results under some conditions.
        if s:is_known_rope_bug()
            let l:rope_result = []
        else
            try
                let l:rope_result = RopeOmni(a:findstart, a:keyword_base)
            catch /.*/
                redraw | echohl WarningMsg |
                            \ echomsg "caught exeception (rope/suggestions)"
                            \ . v:exception | echohl None
                if g:combinerEXP#WantCursorShowsError
                    execute "hi! link Cursor " . g:combinerEXP#CursorColorError
                endif
                let l:rope_result = []
            endtry
        endif
        let l:dc_result = localcomplete#localMatches(
                \ a:findstart, a:keyword_base)
        let l:all_bufer_result = localcomplete#allBufferMatches(
                \ a:findstart, a:keyword_base)
        return extend(l:rope_result, l:dc_result, l:all_bufer_result)
    endif
endfunction

function combinerEXP#completeCombinerTextish(findstart, keyword_base)
    " A completion function combiner that searches local and dictionary
    " matches.  Note that you can add the dictionary matches much later by
    " configuring the minimum prefix length.
    if a:findstart
        return localcomplete#getCurrentKeywordColumnIndex()
    else
        let l:all_completers = [
                    \ 'localcomplete#localMatches',
                    \ 'localcomplete#allBufferMatches',
                    \ 'localcomplete#dictMatches',
                    \ ]
        return combinerEXP#completeCombinerABSTRACT(
                    \ a:findstart,
                    \ a:keyword_base,
                    \ l:all_completers
                    \ )
    endif
endfunction
