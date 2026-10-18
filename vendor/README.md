# FSX local engines

Exported from the user's Ubuntu 24.04 WSL build on 2026-10-18. Corresponding
source and build instructions are also in the sibling Fairy-Stockfish-X-master
and fsfx_linux_components directories. No Git revision was available in WSL.

- ffish-fsx-es6 contains the matching ES6 JS/WASM build, declarations and GPL.
  Emscripten 1.39.16, largeboards=yes all=yes es6=yes.
- pyffish-fsx contains the corresponding C++ sources, build files and GPL.
  setup.py defaults to the separately named pyffish_fsx module. The only
  packaging changes are that default and the pinned PEP 517 build requirements.
  Build flags, engine rules and C++ code are unchanged.

The server extension is built on the target Linux host, avoiding dependency on
the WSL wheel's glibc. It requires a C++17 compiler and CPython 3.14 headers.
Keep these sources with the distributed engines to preserve GPL provenance.
Official and Alice packages remain separate, unmodified dependencies.
