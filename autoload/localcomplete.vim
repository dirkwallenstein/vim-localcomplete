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

if (exists("g:loaded_localcomplete") && g:loaded_localcomplete)
    finish
endif
let g:loaded_localcomplete = 1

if ! exists( "g:localcomplete#LinesAboveToSearchCount" )
    " The count of lines before the cursor position to inspect
    " Negative values to search up to the beginning of the buffer
    " Override buffer local with b:LocalCompleteLinesAboveToSearchCount
    let g:localcomplete#LinesAboveToSearchCount = -1
endif

if ! exists( "g:localcomplete#LinesBelowToSearchCount" )
    " The count of lines before the cursor position to inspect
    " Negative values to search up to the end of the buffer
    " Override buffer local with b:LocalCompleteLinesBelowToSearchCount
    let g:localcomplete#LinesBelowToSearchCount = 10
endif

if ! exists( "g:localcomplete#WantIgnoreCase" )
    " Ignore case when looking for matches
    let g:localcomplete#WantIgnoreCase = 0
endif

if ! exists( "g:localcomplete#WantReversedOrder" )
    " Search lines for matches from the bottom of the searched area upwards.
    let g:localcomplete#WantReversedOrder = 1
endif

if ! exists( "g:localcomplete#WantCenteredOrder" )
    " Suggest matches starting at the current cursor position.  Search lines
    " for matches alternately above and below.  This overrides the reversed
    " order, if that is set, too.
    let g:localcomplete#WantCenteredOrder = 1
endif

if ! exists( "g:localcomplete#ShowOriginNote" )
    " Add a sign in the completion menu that shows that an entry originates
    " from localcomplete.
    let g:localcomplete#ShowOriginNote = 1
endif

" =============================================================================

" XXX Note that all the length variables take effect _after_ the ACP-meets
" function restrictions.  So there is a minimum specified by ACP, too.

" XXX Each of the variables in this section can be overridden by buffer
" local variables of the same name without the hash sign and capitalized

if ! exists( "g:localcomplete#DictMinPrefixLength" )
    " Add dictionary matches if the prefix has this lenght minimum
    let g:localcomplete#DictMinPrefixLength = 5
endif

if ! exists( "g:localcomplete#LocalMinPrefixLength" )
    " Add local matches if the prefix has this lenght minimum
    let g:localcomplete#LocalMinPrefixLength = 1
endif

" =============================================================================

" Variable Fallbacks
" ------------------

function s:numericVariableFallback(variableList, wantEnforceNonNegative)
    for l:variable in a:variableList
        if exists(l:variable)
            let l:result_number = eval(l:variable)
            if a:wantEnforceNonNegative && l:result_number < 0
                throw "Variable " . l:variable . "less than zero"
            endif
            return l:result_number
        endif
    endfor
    throw "None of the variables exists: " . string(a:variableList)
endfunction

function localcomplete#getLinesBelowCount()
    let l:variableList = [
                \ "b:LocalCompleteLinesBelowToSearchCount",
                \ "g:localcomplete#LinesBelowToSearchCount"
                \ ]
    return s:numericVariableFallback(l:variableList, 0)
endfunction

function localcomplete#getLinesAboveCount()
    let l:variableList = [
                \ "b:LocalCompleteLinesAboveToSearchCount",
                \ "g:localcomplete#LinesAboveToSearchCount"
                \ ]
    return s:numericVariableFallback(l:variableList, 0)
endfunction

function localcomplete#getDictMinPrefixLength()
    let l:variableList = [
                \ "b:LocalCompleteDictMinPrefixLength",
                \ "g:localcomplete#DictMinPrefixLength"
                \ ]
    return s:numericVariableFallback(l:variableList, 1)
endfunction

function localcomplete#getLocalMinPrefixLength()
    let l:variableList = [
                \ "b:LocalCompleteLocalMinPrefixLength",
                \ "g:localcomplete#LocalMinPrefixLength"
                \ ]
    return s:numericVariableFallback(l:variableList, 1)
endfunction


" =============================================================================

" Helpers
" -------

function s:getLineUpToCursor()
    return strpart(getline('.'), 0, col('.') - 1)
endfunction

function s:getCurrentKeyword()
    return matchstr(s:getLineUpToCursor(), '\k*$')
endfunction

function s:getCurrentKeywordColumnIndex()
    " Note : return a zero based column index
    let l:start_col = col('.') - len(s:getCurrentKeyword()) - 1
    return max([l:start_col, 0])
endfunction

" Completion functions
" --------------------

function localcomplete#localMatches(findstart, keyword_base)
    " Suggest matches looking at the region around the current cursor position
    " or the whole file.  The configuration at the top of this file applies.
    if a:findstart
        return s:getCurrentKeywordColumnIndex()
    else
        if strwidth(a:keyword_base) < localcomplete#getLocalMinPrefixLength()
            return []
        endif
        LCPython import localcomplete
        LCPython localcomplete.complete_local_matches()
        return s:__localcomplete_lookup_result
    endif
endfunction

function localcomplete#dictMatches(findstart, keyword_base)
    " Search the file specified in the dictionary option for matches
    if a:findstart
        return s:getCurrentKeywordColumnIndex()
    else
        if strwidth(a:keyword_base) < localcomplete#getDictMinPrefixLength()
            return []
        endif
        LCPython import localcomplete
        LCPython localcomplete.complete_dictionary_matches()
        return s:__dictcomplete_lookup_result
    endif
endfunction

" Combiners
" ---------

function localcomplete#completeCombinerABSTRACT(findstart, keyword_base, all_completers)
    " completion combiner implementor.  Pass 2 or more completers in a list as
    " third argument and the results will be combined.  All completers have to
    " find the same column in the findstart mode.  Pick one to compute the
    " column in your own wrapper if that is not wanted.
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

" Ropevim has a bug.  Use the concrete one below
function localcomplete#completeCombinerPythonABS(findstart, keyword_base)
    let l:all_completers = ['localcomplete#localMatches', 'RopeOmni']
    return localcomplete#completeCombinerABSTRACT(a:findstart, a:keyword_base, l:all_completers)
endfunction

" Check for known rope errors
function s:is_known_rope_bug()
    " Inside comments rope always returns the current column
    " XXX Check again later if this bug still exists
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

" A completion combiner for Python that works around the ropevim bug.
function localcomplete#completeCombinerPython(findstart, keyword_base)
    if a:findstart
        let l:dc_column = localcomplete#localMatches(a:findstart, a:keyword_base)
        let l:rope_column = RopeOmni(a:findstart, a:keyword_base)
        " If there is a mismatch, check if it is a known rope bug
        if l:dc_column != l:rope_column
            if !s:is_known_rope_bug()
                throw "completeCombinerPython: unequal columns computed: dc("
                        \ . l:dc_column . ") rope(" . l:rope_column . ")"
            endif
        endif
        return l:dc_column
    else
        let l:dc_result = localcomplete#localMatches(a:findstart, a:keyword_base)
        " ropevim returns invalid results inside a comment
        if s:is_known_rope_bug()
            let l:rope_result = []
        else
            let l:rope_result = RopeOmni(a:findstart, a:keyword_base)
        endif
        return extend(l:dc_result, l:rope_result)
    endif
endfunction

function localcomplete#completeCombinerTextish(findstart, keyword_base)
    " A completion function combiner that searches local and dictionary
    " matches.  Note that you can add the dictionary matches much later by
    " configuring the minimum prefix length.
    if a:findstart
        return s:getCurrentKeywordColumnIndex()
    else
        let l:all_completers = [
                    \ 'localcomplete#localMatches',
                    \ 'localcomplete#dictMatches',
                    \ ]
        return localcomplete#completeCombinerABSTRACT(
                    \ a:findstart,
                    \ a:keyword_base,
                    \ l:all_completers
                    \ )
    endif
endfunction

" ----------- Python prep

if has('python')
    command! -nargs=1 LCPython python <args>
elseif has('python3')
    command! -nargs=1 LCPython python3 <args>
else
    echoerr "No Python support found"
end

LCPython << PYTHONEOF
import sys, os, vim
sys.path.insert(0, os.path.join(vim.eval("expand('<sfile>:p:h:h')"), 'pylibs'))
PYTHONEOF
