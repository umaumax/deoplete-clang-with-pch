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

        self.include_pathes = vars.get('deoplete#sources#clang_with_pch#include_pathes', [])
        self.pch_pathes = vars.get('deoplete#sources#clang_with_pch#pch_pathes', [])

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

    def get_completion(self, line, column, buf):
        column += 1
        # NOTE: delete means : no auto delete
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
            [tmp_file_path]

        result = []
        include_pathes = self.include_pathes
        for include_path in include_pathes:
            cmds.append('-I' + include_path)

        self.cnt += 1
#         print('[debug]:{0} {1}'.format(self.cnt, cmds))

        try:
            d = subprocess.check_output(
                cmds,
                stderr=subprocess.STDOUT,
                shell=False)
            for line in str(d).split("\\n"):
                line = line.split('COMPLETION: ', 1).pop()
                tmp = line.split(' : ')
                if len(tmp) == 2:
                    result.append({'dup': 1, 'word': tmp[0], 'menu': tmp[1]})
        except subprocess.CalledProcessError as e:
            # TODO: error handling
            result = [
                #                 'error',
                #                 e.returncode,
                #                 e.cmd,
                #                 e.output,
            ]
        fp.close()
        return result

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
