vim-localcomplete
=================

Combinable completion functions for Vim.

This repository contains functions that can be used in combination with
[AutoComplPop](https://github.com/dirkwallenstein/vim-autocomplpop) to combine
multiple completion sources into one PopUp Menu.  One use case is to
augment `RopeOmni` from [python-mode](https://github.com/klen/python-mode) with
completions for a small area around the current line or the whole current buffer.
There is some example code included for this use case.

There are two files of interest:

localcomplete.vim
-----------------
Here you find three completion functions:

    localcomplete#localMatches

It searches through the configured area of the current buffer only.  All of the
configuration in the first section of the source file applies to it.  Please
read through that section.  There is no documentation file.

    localcomplete#allBufferMatches

This function searches through all buffers.  It respects the case and
keyword-char configuration.

    localcomplete#dictMatches

Search the dictionary configured in Vim's 'dictionary' setting for matches.
All matches are done case-insensitively.  It is a very simple function.  The
dictionary has to be utf-8 encoded.

All three functions can have individual minimum leading word lengths configured
after which they start to produce results.  This makes only sense in
combination with ACP.

combinerEXP.vim
---------------
This is a pretty rough and hardcoded module for demonstration purposes.
