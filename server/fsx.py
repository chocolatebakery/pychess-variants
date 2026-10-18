import re
from pathlib import Path
from typing import Any

FSX_VARIANTS = frozenset(("rifle-chess", "brotherhood", "spell-chess", "monster"))

try:
    import pyffish_fsx as _fsx
except ModuleNotFoundError as exc:
    if exc.name != "pyffish_fsx":
        raise
    _fsx = None

if _fsx is not None:
    _fsx.load_variant_config(
        (Path(__file__).resolve().parent.parent / "variants-fsx.ini").read_text(encoding="utf-8")
    )


def fsx_available() -> bool:
    return _fsx is not None


def fsx_engine() -> Any:
    if _fsx is None:
        raise ValueError("FSX is not installed. Run the site in Linux/WSL with uv sync.")
    return _fsx


def fsx_san(variant: str, move: str, san: str) -> str:
    if variant == "monster" and move == "0000":
        return "--"
    if variant == "spell-chess" and move.startswith(("f@", "j@")) and "," in move:
        # Native SAN only writes /F or /J, losing the target and making PGN ambiguous.
        cast = move.split(",", 1)[0]
        return cast + "," + re.sub(r"/[FJ](?=[+#]*$)", "", san)
    return san
