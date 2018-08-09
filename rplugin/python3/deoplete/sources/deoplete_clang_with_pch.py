import re
from .base import Base
import tempfile
import os.path
import subprocess
from pathlib import Path


class Source(Base):
    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = 'pch'
        self.mark = '[PCH]'
        self.filetypes = ['cpp']
#         self.min_pattern_length = 0
        self.rank = 500
        # TODO:
#         self.sort_algo = ''

        self.input_pattern = (r'[^. \t0-9]\.\w*|'
                              r'[^. \t0-9]->\w*|'
                              r'[a-zA-Z_]\w*::\w*')

        self.cache = []
        self.cnt = 0

    def on_init(self, context):
        vars = context['vars']

        tmp_flags = vars.get('deoplete#sources#clang#flags', [])
        tmp_flags = vars.get('deoplete#sources#clang_with_pch#flags', tmp_flags)
        # NOTE: drop flags
        drop_pattern_list = [
            '-fuse-ld=.*',
            '-g1',
            '-Wl,.*',
            '-Wno.*',
            '-fno-exceptions',
            '-L.*',
            '-l.*',
            '-fPIC',
            '-fpic',
        ]
        self.flags = list(filter(lambda x: x if len(list(filter(lambda pattern: re.compile(pattern).match(x), drop_pattern_list))) == 0 else None, tmp_flags))
        self.include_pathes = vars.get('deoplete#sources#clang_with_pch#include_pathes', [])
        self.pch_pathes = vars.get('deoplete#sources#clang_with_pch#pch_pathes', [])
        self.max_completion_n = vars.get('deoplete#sources#clang_with_pch#max_completion_n', 512)

        try:
            # init(load suorce) only work
            pass
        except Exception:
            # Ignore the error
            pass

    def on_event(self, context):
        try:
            #                 if context['event'] == 'BufRead':
            # vim autocmd event based works
            # NOTE: 他の補完機能例えば，lookに上書きされないように?
            #             self.gather_candidates(context)
            if context["event"] == "BufWritePost":
                self.gather_candidates(context, refresh=True)
            else:
                # Note: Dummy call to make cache
                self.gather_candidates(context)
        except Exception:
            # Ignore the error
            pass

    def get_current_buffer(self, b):
        return '\n'.join(b[:])

    def get_complete_position(self, context):
        m = re.search(r'\w*$', context['input'])
        return m.start() if m else -1

    def parse_clang_output_line(self, line):
        completion_prefix = 'COMPLETION: '
        if completion_prefix not in line:
            return None
        strip_left = (lambda text, prefix: text if not text.startswith(prefix) else text[len(prefix):])
        strip_right = (lambda text, suffix: text if not text.endswith(suffix) else text[:len(text) - len(suffix)])
        strip = (lambda text, prefix, suffix: strip_right(strip_left(text, prefix), suffix))
        line = strip_left(line, completion_prefix)
        line = strip_right(line, '\n')
        name = line.split(' : ')[0]
        name = strip_right(name, ' (HIDDEN)')
        m = re.search(r"(\[#.*?#\])(([^\[\]]|\[[^#])*)(\[#(.*)#\])?$", line)
        ret = {}
        if m:
            ret_type = strip(m.group(1), '[#', '#]')
            args_type = m.group(2)
            args_type = args_type.replace('<#', '')
            args_type = args_type.replace('#>', '')
            method_source_info = strip(m.group(4) if m.group(4) else '', '[# ', '#]')
            method_source_info = strip_right(method_source_info, ':' + name)
            ret = {'dup': 1, 'word': name, 'abbr': args_type, 'kind': ret_type, 'menu': method_source_info}
        return ret

    def get_completion(self, line, column, buf):
        column += 1
        # NOTE: delete:False means : no auto delete
        fp = tempfile.NamedTemporaryFile(mode='w+t', encoding='utf-8', suffix='.cpp', delete=False)
        fp.write(buf)
        fp.flush()
        tmp_file_path = fp.name

        p = Path(".")
        pch_filepathes = p.glob("*.pch")
        pch_cmds = []
        for pch_filepath in pch_filepathes:
            pch_cmds.extend(['-include-pch', str(pch_filepath)])
        for pch_filepath in self.pch_pathes:
            pch_cmds.extend(['-include-pch', pch_filepath])
        if len(pch_cmds) == 0:
            return []

        cmds = [] +\
            ['clang++'] +\
            ['-cc1'] + pch_cmds +\
            ['-fsyntax-only', '-code-completion-at=' + tmp_file_path + ':' + str(line) + ':' + str(column)] +\
            ['-std=c++11'] +\
            self.flags +\
            [tmp_file_path]

        default_include_path = '.'
        include_pathes = self.include_pathes
        if default_include_path not in include_pathes:
            include_pathes.append(default_include_path)
        for include_path in include_pathes:
            cmds.append('-I' + include_path)

        self.cnt += 1
#         print('[debug]:{0} {1}'.format(self.cnt, cmds))

        strip_right = (lambda text, suffix: text if not text.endswith(suffix) else text[:len(text) - len(suffix)])
        strip_left = (lambda text, prefix: text if not text.startswith(prefix) else text[len(prefix):])
        result = []
        error_result = []
        try:
            d = subprocess.check_output(
                cmds,
                stderr=subprocess.STDOUT,
                shell=False)
            binary_data = d
            # e.g.
            # COMPLETION: Context() : [#clang::ASTContext *const#]
            # COMPLETION: MatchResult(const BoundNodes &Nodes, clang::ASTContext *Context) : [#MatchResult#]
            # COMPLETION: Nodes() : [#const BoundNodes#]
            # COMPLETION: SourceManager() : [#clang::SourceManager *const#]
#             for line in d.decode('utf-8').splitlines():
#                 ret = self.parse_clang_output_line(line)
#                 if ret:
#                     result.append(ret)
        except subprocess.CalledProcessError as e:
            log_fp = tempfile.NamedTemporaryFile(mode='w+t', encoding='utf-8', suffix='.log', delete=False)
            log_fp.write(' '.join(e.cmd) + "\nexit code:" + str(e.returncode) + "\n")
            log_fp.write(e.output.decode('utf-8'))
            log_fp.close()
            error_result = [{'dup': 1, 'word': log_fp.name, 'abbr': '<error log file path>', 'kind': '', 'menu': 'clang-with-pch parse error'}]
            binary_data = e.output
        fp.close()
        # NOTE: 異常終了しても補完候補はリストアップされている
        self.max_completion_n = 256
        n = 0
        for line in binary_data.decode('utf-8').splitlines():
            ret = self.parse_clang_output_line(line)
            if ret:
                result.append(ret)
                n += 1
                if len(result) >= self.max_completion_n:
                    break
        return result + error_result

    def gather_candidates(self, context, refresh=False):
        if refresh and len(self.cache) > 0:
            return self.cache
        line = context['position'][1]
        col = (context['complete_position']
               if 'complete_position' in context
               else context['position'][2]) + 1
        buf = self.vim.current.buffer
        # buf.name
        complete = self.get_completion(line, col, self.get_current_buffer(buf))
        if complete is None:
            return []
        self.cache = complete
        return complete

#         if self.sort_algo == 'priority':
#             def get_priority(x):
#                 return x.string.priority
#             results = sorted(complete.results, key=get_priority)
#         elif self.sort_algo == 'alphabetical':
#             def get_abbrevation(x):
#                 return self.get_abbr(x.string).lower()
#             results = sorted(complete.results, key=get_abbrevation)
#         else:
#             results = complete.results
#         return list(map(self.parse_candidates, results))
