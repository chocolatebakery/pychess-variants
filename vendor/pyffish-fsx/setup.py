# -*- coding: utf-8 -*-

from setuptools import setup, Extension
from glob import glob
import platform
import io
import os


fsx_package = True
module_name = "pyffish_fsx" if fsx_package else "pyffish"

if platform.python_compiler().startswith("MSC"):
    args = ["/std:c++17"]
else:
    args = ["-std=c++17", "-Wno-date-time"]
    # VERY_LARGE_BOARDS widens PieceSet to two words, whose loops trip a GCC 11
    # LTO internal compiler error (compute_live_loop_exits) in the link-time
    # optimizer. VLB pyffish is a developer/test configuration (no CI wheels),
    # so build it without LTO. Native make builds are unaffected.
    very_large = "VERY_LARGE_BOARDS" in (os.environ.get("CXXFLAGS", "")
                                         + os.environ.get("CFLAGS", ""))
    if "clang" not in os.environ.get("CXX", "").lower() and not very_large:
        args.append("-flto")

args.extend(["-DLARGEBOARDS", "-DALLVARS", "-DPRECOMPUTED_MAGICS", "-DNNUE_EMBEDDING_OFF"])

if "64bit" in platform.architecture() and not platform.python_compiler().startswith("MSC"):
    args.append("-DIS_64BIT")

CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Operating System :: OS Independent",
]

with io.open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read().strip()

sources = glob("src/*.cpp") + glob("src/syzygy/*.cpp") + glob("src/nnue/*.cpp") + glob("src/nnue/features/*.cpp")
headers = glob("src/*.h") + glob("src/syzygy/*.h") + glob("src/nnue/*.h") + glob("src/nnue/features/*.h")
for f in ["src/ffishjs.cpp", "src/main.cpp", "src/ffishdll.cpp"]:
    try:
        sources.remove(os.path.normcase(f))
    except ValueError:
        pass

pyffish_module = Extension(
    module_name,
    sources=sources,
    depends=headers,
    define_macros=[("PYFFISH_FSX", "1")] if fsx_package else [],
    extra_compile_args=args)

setup(name="pyffish-fsx" if fsx_package else "pyffish", version="0.0.88",
      description="Fairy-Stockfish Python wrapper",
      long_description=long_description,
      long_description_content_type="text/markdown",
      author="Bajusz Tamás",
      author_email="gbtami@gmail.com",
      license="GPL3",
      classifiers=CLASSIFIERS,
      url="https://github.com/gbtami/Fairy-Stockfish",
      python_requires=">=3.9",
      ext_modules=[pyffish_module],
      data_files=[] if fsx_package else [("", ["pyffish.pyi"])]
      )
