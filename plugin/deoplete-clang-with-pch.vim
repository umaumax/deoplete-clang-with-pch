if exists('g:loaded_deoplete_clang_with_pch')
	finish
endif
let g:loaded_deoplete_clang_with_pch = 1

let g:deoplete#sources#clang_with_pch#include_pathes =
			\ get(g:, 'deoplete#sources#clang_with_pch#include_pathes', [])

let g:deoplete#sources#clang_with_pch#pch_pathes =
			\ get(g:, 'deoplete#sources#clang_with_pch#pch_pathes', [])

let g:deoplete#sources#clang_with_pch#flags =
			\ get(g:, 'deoplete#sources#clang_with_pch#flags', [])

let g:deoplete#sources#clang_with_pch#max_completion_n =
			\ get(g:, 'deoplete#sources#clang_with_pch#max_completion_n', 512)
