from __future__ import annotations

import random
from dataclasses import dataclass
from typing import NotRequired, TypedDict


RANDOM_MODE_WILD29 = "wild29"
RANDOM_MODE_DICE = "randomdice"


class RandomContext(TypedDict, total=False):
    mode: str
    modeName: str
    poolId: str
    poolVersion: int
    entryId: str
    entryName: str
    variant: str
    chess960: bool
    weight: int
    rulesVersion: str
    previousEntryId: NotRequired[str]
    previousGameId: NotRequired[str]


@dataclass(frozen=True)
class RandomModeEntry:
    entry_id: str
    display_name: str
    variant: str
    chess960: bool = False
    weight: int = 1
    rules_version: str = "fairy-stockfish"


@dataclass(frozen=True)
class RandomModePool:
    mode: str
    display_name: str
    pool_id: str
    version: int
    entries: tuple[RandomModeEntry, ...]


class RandomModeError(ValueError):
    pass


WILD29_UNIMPLEMENTED_ICC_ENTRIES: tuple[tuple[str, int], ...] = (
    ("wild3", 1),
    ("wild4", 1),
    ("wild5", 2),
    ("wild8", 1),
    ("wild9", 1),
    ("wild18", 1),
)

WILD29_POOL = RandomModePool(
    mode=RANDOM_MODE_WILD29,
    display_name="Wild 29",
    pool_id="icc-wild29-supported",
    version=1,
    entries=(
        RandomModeEntry("icc-wild17", "ICC Wild 17 - Losers", "losers", weight=3),
        RandomModeEntry("icc-wild22", "ICC Wild 22 - Chess960", "chess", chess960=True, weight=2),
        RandomModeEntry("icc-wild23", "ICC Wild 23 - Crazyhouse", "crazyhouse", weight=3),
        RandomModeEntry("icc-wild25", "ICC Wild 25 - Three-check", "3check", weight=3),
        RandomModeEntry("icc-wild26", "ICC Wild 26 - Giveaway", "giveaway", weight=3),
        RandomModeEntry("icc-wild27", "ICC Wild 27 - Atomic", "atomic", weight=3),
    ),
)

RANDOM_DICE_POOL = RandomModePool(
    mode=RANDOM_MODE_DICE,
    display_name="Random Dice",
    pool_id="random-dice-supported",
    version=1,
    entries=(
        RandomModeEntry("dice-atomic", "Atomic", "atomic"),
        RandomModeEntry("dice-orda", "Orda", "orda"),
        RandomModeEntry("dice-losers", "Losers", "losers"),
        RandomModeEntry("dice-3check", "Three-check", "3check"),
        RandomModeEntry("dice-kingofthehill", "King of the Hill", "kingofthehill"),
        RandomModeEntry("dice-chess960", "Chess960", "chess", chess960=True),
    ),
)

RANDOM_MODE_POOLS: dict[str, RandomModePool] = {
    RANDOM_MODE_WILD29: WILD29_POOL,
    RANDOM_MODE_DICE: RANDOM_DICE_POOL,
}
RANDOM_MODE_VARIANTS = frozenset(RANDOM_MODE_POOLS)


def is_random_mode(variant: str | None) -> bool:
    return bool(variant) and variant in RANDOM_MODE_POOLS


def random_mode_display_name(mode: str) -> str:
    pool = RANDOM_MODE_POOLS.get(mode)
    return mode if pool is None else pool.display_name


def random_mode_seek_context(mode: str) -> RandomContext:
    pool = _pool(mode)
    return {
        "mode": pool.mode,
        "modeName": pool.display_name,
        "poolId": pool.pool_id,
        "poolVersion": pool.version,
    }


def previous_entry_id_from_context(context: RandomContext | dict[str, object] | None) -> str | None:
    if context is None:
        return None
    previous_entry_id = context.get("previousEntryId") or context.get("entryId")
    return str(previous_entry_id) if previous_entry_id else None


def select_random_mode_entry(
    mode: str, previous_entry_id: str | None = None
) -> RandomModeEntry:
    pool = _pool(mode)
    candidates = [
        entry for entry in pool.entries if previous_entry_id is None or entry.entry_id != previous_entry_id
    ]
    if not candidates:
        candidates = list(pool.entries)
    if not candidates:
        raise RandomModeError("Random mode pool has no entries: %s" % mode)
    return random.choices(candidates, weights=[entry.weight for entry in candidates], k=1)[0]


def random_context_for_entry(
    mode: str,
    entry: RandomModeEntry,
    *,
    previous_entry_id: str | None = None,
    previous_game_id: str | None = None,
) -> RandomContext:
    pool = _pool(mode)
    context: RandomContext = {
        "mode": pool.mode,
        "modeName": pool.display_name,
        "poolId": pool.pool_id,
        "poolVersion": pool.version,
        "entryId": entry.entry_id,
        "entryName": entry.display_name,
        "variant": entry.variant,
        "chess960": entry.chess960,
        "weight": entry.weight,
        "rulesVersion": entry.rules_version,
    }
    if previous_entry_id:
        context["previousEntryId"] = previous_entry_id
    if previous_game_id:
        context["previousGameId"] = previous_game_id
    return context


def rematch_context_for_game(
    context: RandomContext | dict[str, object] | None, game_id: str
) -> RandomContext | None:
    if context is None:
        return None
    mode = str(context.get("mode", ""))
    if not is_random_mode(mode):
        return None
    rematch_context = random_mode_seek_context(mode)
    previous_entry_id = context.get("entryId")
    if previous_entry_id:
        rematch_context["previousEntryId"] = str(previous_entry_id)
    rematch_context["previousGameId"] = game_id
    return rematch_context


def _pool(mode: str) -> RandomModePool:
    try:
        return RANDOM_MODE_POOLS[mode]
    except KeyError as exc:
        raise RandomModeError("Unknown random mode: %s" % mode) from exc
