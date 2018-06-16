# deoplete-clang-with-pch

C++ source for [Shougo/deoplete\.nvim: Dark powered asynchronous completion framework for neovim/Vim8]( https://github.com/Shougo/deoplete.nvim )

## TODO
* 設定項目を増やす
	* `-std`のオプション
	* localなプロジェクトに対する設定(e.g. 設定ファイルの自動読込)
* 他の`deoplete-xxx`を参考にリファクタリング
* 無駄な補完処理が走らないように，キャッシュを有効利用
* 自動pch作成機能

## overview
vimのカレントディレクトリに，`*.pch`が存在するときに，補完を行う

[Precompiled Header and Modules Internals — Clang 7 documentation]( https://clang.llvm.org/docs/PCHInternals.html )

## install example
```
Plug 'umaumax/deoplete-clang-with-pch', {'for': ['c','cpp','cmake']}
```

## setting example
```
let g:deoplete#sources#clang_with_pch#include_pathes = ['/usr/local/Cellar/llvm/6.0.0/include']
let g:deoplete#sources#clang_with_pch#pch_pathes = []
```

----

## FYI
## PCHの作成と利用について
1. `#include`のみのヘッダファイルを作成
	* 例えば，対象cppファイルに対して，`grep '#include' | grep -v '//'`
1. pch作成
	* ```clang++ -cc1 -x c++-header -emit-pch -std=c++11 -stdlib=libc++ header.h -o header.h.pch```
1. 利用
	* build: ```clang++ -cc1 -include-pch header.h.pch -std=c++11 test.cpp -o test```
	* 補完: ```clang++ -cc1 -include-pch header.h.pch -fsyntax-only -code-completion-at=test:<line>:<col> -std=c++11 test.cpp```

* `-cc1`は位置に注意(`clang++`の直後が安全)
* `-v`オプションを利用するとよい
* `-cc1`の場合には`-stdlin=libc++`を付加しないと，C++11ヘッダ群が見つからない(`-Xclang`利用時は不要)
* `-std`オプションはPCH作成時と利用時に一致させること

ちなみに，PCHを利用しない補完では，`-Xclang`オプションで利用可能
```
clang++ -Xclang -fsyntax-only -Xclang -code-completion-at=test.cpp:<line>:<col> -std=c++11 test.cpp -c
```

----

ちなみに，Ubuntu16.04では，`-cc1`のオプション利用時にinclude pathを別途追加する必要がある

e.g.
```
clang++ -cc1 -emit-pch -x c++-header -std=c++11 -stdlib=libstdc++ $target -o $target.pch \
	-I/usr/include/clang/5.0.0/include \
	-I/usr/include \
	-I/usr/include/c++/5.4.0 \
	-I/usr/include/x86_64-linux-gnu/c++/5.4.0
```

上記のinclude pathは下記の`-Xclang`コマンド版を参考するとよい

`-Xclang`版では余計なオプションが軒を連ねるので，確認後`-cc1`で生成し直す

```
clang++ -Xclang -emit-pch -x c++-header -std=c++11 header.h -o header.h.pch
```

なお，補完時に必要なinclude pathは減っていた

```
clang++ -cc1 -include-pch $target.pch -fsyntax-only -code-completion-at=$target:$line:$col -std=c++11 $target \
	-I/usr/include/c++/5.4.0
```
