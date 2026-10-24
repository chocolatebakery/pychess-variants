from __future__ import annotations

import json
import unittest
from collections import Counter
from dataclasses import replace
from unittest.mock import patch

from random_modes import (
    RANDOM_DICE_POOL,
    RANDOM_MODE_DICE,
    RANDOM_MODE_POOLS,
    RANDOM_MODE_WILD29,
    RECENT_ENTRY_LIMIT,
    WILD29_POOL,
    WILD29_UNIMPLEMENTED_ICC_ENTRIES,
    RandomModeError,
    is_random_mode,
    previous_entry_id_from_context,
    random_context_for_entry,
    recent_entry_ids_from_context,
    rematch_context_for_game,
    select_random_mode_entry,
)


class RandomModesTestCase(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("random_modes.fsx_available", return_value=True))

    def test_missing_fsx_excludes_only_its_entries(self):
        with (
            patch("random_modes.fsx_available", return_value=False),
            patch("random_modes.secrets.randbelow", return_value=22) as draw,
        ):
            self.assertEqual(select_random_mode_entry("randomdice").variant, "torpedo")
        draw.assert_called_once_with(24)

    def test_modes_are_registered(self) -> None:
        self.assertTrue(is_random_mode(RANDOM_MODE_WILD29))
        self.assertTrue(is_random_mode(RANDOM_MODE_DICE))
        self.assertFalse(is_random_mode("atomic"))

    def test_wild29_pool_uses_supported_icc_entries_only(self) -> None:
        self.assertEqual(
            {entry.entry_id for entry in WILD29_POOL.entries},
            {
                "icc-wild17",
                "icc-wild22",
                "icc-wild23",
                "icc-wild25",
                "icc-wild26",
                "icc-wild27",
            },
        )
        self.assertIn(("wild3", 1), WILD29_UNIMPLEMENTED_ICC_ENTRIES)

    def test_random_dice_includes_chess960(self) -> None:
        self.assertIn(
            ("chess", True),
            {(entry.variant, entry.chess960) for entry in RANDOM_DICE_POOL.entries},
        )

    def test_atomic960_is_distinct_from_atomic_and_replaces_racing_kings(self) -> None:
        entries = {entry.entry_id: entry for entry in RANDOM_DICE_POOL.entries}
        atomic, atomic960 = entries["dice-atomic"], entries["dice-atomic960"]
        self.assertEqual((atomic.variant, atomic.chess960), ("atomic", False))
        self.assertEqual((atomic960.variant, atomic960.chess960), ("atomic", True))
        self.assertNotIn("dice-racingkings", entries)
        self.assertFalse(any(entry.variant == "racingkings" for entry in entries.values()))
        pool = replace(RANDOM_DICE_POOL, entries=(atomic, atomic960))
        with (
            patch.dict(RANDOM_MODE_POOLS, {pool.mode: pool}),
            patch("random_modes.secrets.randbelow", return_value=0),
        ):
            self.assertEqual(
                select_random_mode_entry(
                    pool.mode, atomic.entry_id, recent_entry_ids=[atomic.entry_id]
                ),
                atomic960,
            )

    def test_atomic960_uses_randomized_starts_and_atomic_captures(self) -> None:
        from fairy import FairyBoard
        from fairy.chess960 import CHESS960_FENS

        board = FairyBoard("atomic", chess960=True)
        self.assertIn(board.initial_fen.split("/", 1)[0], CHESS960_FENS)
        self.assertTrue(board.chess960)
        self.assertTrue(board.legal_moves())
        board = FairyBoard("atomic", "7k/8/8/8/8/8/pr6/R6K w - - 0 1", chess960=True)
        self.assertIn("a1a2", board.legal_moves())
        board.push("a1a2")
        self.assertEqual(board.fen.split()[0], "7k/8/8/8/8/8/8/7K")

    def test_select_excludes_previous_entry_when_possible(self) -> None:
        previous_entry = WILD29_POOL.entries[0]
        expected_entry = WILD29_POOL.entries[1]

        with patch("random_modes.secrets.randbelow", return_value=0) as randbelow:
            selected = select_random_mode_entry(RANDOM_MODE_WILD29, previous_entry.entry_id)

        self.assertEqual(selected, expected_entry)
        randbelow.assert_called_once_with(
            sum(entry.weight for entry in WILD29_POOL.entries) - previous_entry.weight
        )

    def test_secure_draw_maps_every_ticket_to_the_original_weighted_intervals(self) -> None:
        for pool in RANDOM_MODE_POOLS.values():
            expected = [entry for entry in pool.entries for _ in range(entry.weight)]
            with self.subTest(mode=pool.mode), patch("random_modes.secrets.randbelow") as randbelow:
                for ticket, entry in enumerate(expected):
                    randbelow.return_value = ticket
                    self.assertEqual(select_random_mode_entry(pool.mode), entry)
                    randbelow.assert_called_with(len(expected))
                self.assertEqual(randbelow.call_count, len(expected))

    def test_context_round_trips_previous_entry_for_rematch(self) -> None:
        entry = WILD29_POOL.entries[0]
        context = random_context_for_entry(RANDOM_MODE_WILD29, entry)

        rematch_context = rematch_context_for_game(context, "game123")

        self.assertIsNotNone(rematch_context)
        assert rematch_context is not None
        self.assertEqual(rematch_context["mode"], RANDOM_MODE_WILD29)
        self.assertEqual(previous_entry_id_from_context(rematch_context), entry.entry_id)
        self.assertEqual(rematch_context["previousGameId"], "game123")

    def test_random_mode_rematches_keep_weights_and_exclude_each_previous_result(self) -> None:
        for pool in RANDOM_MODE_POOLS.values():
            for previous_entry in pool.entries:
                with self.subTest(mode=pool.mode, variant=previous_entry.variant):
                    context = random_context_for_entry(pool.mode, previous_entry)
                    rematch_context = rematch_context_for_game(context, "randomgame")
                    assert rematch_context is not None
                    expected = {
                        entry.entry_id: entry.weight
                        for entry in pool.entries
                        if entry != previous_entry
                    }
                    total_weight = sum(expected.values())

                    with patch("random_modes.secrets.randbelow") as randbelow:
                        selected = Counter()
                        for ticket in range(total_weight):
                            randbelow.return_value = ticket
                            entry = select_random_mode_entry(
                                pool.mode, previous_entry_id_from_context(rematch_context)
                            )
                            selected[entry.entry_id] += 1
                            randbelow.assert_called_with(total_weight)
                        self.assertEqual(selected, expected)
                        self.assertEqual(randbelow.call_count, total_weight)

    def test_legacy_inputs_only_remember_the_previous_result(self) -> None:
        first, second = RANDOM_DICE_POOL.entries[:2]
        with patch("random_modes.secrets.randbelow", return_value=0):
            self.assertEqual(select_random_mode_entry(RANDOM_MODE_DICE), first)
            self.assertEqual(select_random_mode_entry(RANDOM_MODE_DICE, first.entry_id), second)
            self.assertEqual(select_random_mode_entry(RANDOM_MODE_DICE, second.entry_id), first)

    def test_secure_draw_works_with_real_system_randomness(self) -> None:
        for pool in RANDOM_MODE_POOLS.values():
            with self.subTest(mode=pool.mode):
                self.assertIn(select_random_mode_entry(pool.mode), pool.entries)
                for previous in pool.entries:
                    selected = select_random_mode_entry(pool.mode, previous.entry_id)
                    self.assertIn(selected, pool.entries)
                    self.assertNotEqual(selected.entry_id, previous.entry_id)

    def test_unknown_previous_entry_does_not_change_the_pool(self) -> None:
        for pool in RANDOM_MODE_POOLS.values():
            with self.subTest(mode=pool.mode):
                with patch("random_modes.secrets.randbelow", return_value=0) as randbelow:
                    selected = select_random_mode_entry(pool.mode, "old-removed-entry")
                self.assertEqual(selected, pool.entries[0])
                randbelow.assert_called_once_with(sum(entry.weight for entry in pool.entries))

    def test_single_entry_pool_retains_the_previous_result_fallback(self) -> None:
        entry = WILD29_POOL.entries[0]
        pool = replace(WILD29_POOL, entries=(entry,))
        with (
            patch.dict(RANDOM_MODE_POOLS, {pool.mode: pool}),
            patch("random_modes.secrets.randbelow", return_value=entry.weight - 1) as randbelow,
        ):
            self.assertEqual(select_random_mode_entry(pool.mode, entry.entry_id), entry)
        randbelow.assert_called_once_with(entry.weight)

    def test_invalid_pools_fail_before_requesting_randomness(self) -> None:
        entry = WILD29_POOL.entries[0]
        pools = (
            replace(WILD29_POOL, entries=()),
            replace(WILD29_POOL, entries=(replace(entry, weight=0),)),
            replace(WILD29_POOL, entries=(replace(entry, weight=-1),)),
        )
        for pool in pools:
            with (
                self.subTest(entries=pool.entries),
                patch.dict(RANDOM_MODE_POOLS, {pool.mode: pool}),
                patch("random_modes.secrets.randbelow") as randbelow,
            ):
                with self.assertRaises(RandomModeError):
                    select_random_mode_entry(pool.mode)
                randbelow.assert_not_called()

    def test_unknown_mode_fails_before_requesting_randomness(self) -> None:
        with patch("random_modes.secrets.randbelow") as randbelow:
            with self.assertRaisesRegex(RandomModeError, "Unknown random mode"):
                select_random_mode_entry("unknown-mode")
            randbelow.assert_not_called()

    def test_random_dice_rematch_upgrades_old_pool_context(self) -> None:
        for version in (1, 2, 3, 4, 5, 6, 7, 8):
            with self.subTest(version=version):
                old_context: dict[str, object] = {
                    "mode": RANDOM_MODE_DICE,
                    "poolId": RANDOM_DICE_POOL.pool_id,
                    "poolVersion": version,
                    "entryId": "dice-chess960",
                }

                rematch_context = rematch_context_for_game(old_context, "oldgame")

                assert rematch_context is not None
                self.assertEqual(rematch_context["poolVersion"], 9)
                self.assertEqual(rematch_context["previousEntryId"], "dice-chess960")
                self.assertEqual(old_context["poolVersion"], version)

    def test_random_dice_has_all_requested_variants_with_equal_weights(self) -> None:
        self.assertEqual(
            {entry.variant for entry in RANDOM_DICE_POOL.entries},
            {
                "atomic",
                "orda",
                "losers",
                "3check",
                "kingofthehill",
                "chess",
                "crazyhouse",
                "horde",
                "seirawan",
                "capablanca",
                "knightmate",
                "duck",
                "hoppelpoppel",
                "atomar",
                "fogofwar",
                "alice",
                "makruk",
                "berolina",
                "extinction",
                "kinglet",
                "threekings",
                "torpedo",
                "rifle-chess",
                "brotherhood",
                "spell-chess",
                "monster",
                "spartan",
                "cylinder",
            },
        )
        self.assertEqual(len(RANDOM_DICE_POOL.entries), 29)
        self.assertEqual(len({entry.entry_id for entry in RANDOM_DICE_POOL.entries}), 29)
        self.assertTrue(all(entry.weight == 1 for entry in RANDOM_DICE_POOL.entries))

    def test_new_dice_variants_use_native_rules_and_can_make_a_move(self) -> None:
        from fairy import FairyBoard

        for variant in (
            "atomar",
            "fogofwar",
            "alice",
            "makruk",
            "berolina",
            "extinction",
            "kinglet",
            "threekings",
            "torpedo",
            "spartan",
        ):
            with self.subTest(variant=variant):
                board = FairyBoard(variant)
                moves = board.legal_moves()
                self.assertTrue(moves)
                self.assertEqual(board.variant, variant)
                initial_fen = board.fen
                board.push(moves[0])
                self.assertEqual(board.ply, 1)
                self.assertNotEqual(board.fen, initial_fen)

    def test_random_dice_knightmate_uses_native_engine_rules(self) -> None:
        import pyffish as sf

        entry = next(entry for entry in RANDOM_DICE_POOL.entries if entry.variant == "knightmate")
        fen = sf.start_fen(entry.variant)

        self.assertEqual(sf.validate_fen(fen, entry.variant, entry.chess960), sf.FEN_OK)
        moves = sf.legal_moves(entry.variant, fen, [], entry.chess960)
        self.assertIn("e1d3", moves)
        self.assertIn("e1f3", moves)

    def test_rematch_sequence_excludes_last_five_and_releases_the_oldest(self):
        for pool in RANDOM_MODE_POOLS.values():
            history = []
            context = None
            with (
                self.subTest(mode=pool.mode),
                patch("random_modes.secrets.randbelow", return_value=0),
            ):
                for index in range(14):
                    previous = recent_entry_ids_from_context(context)
                    previous_id = previous_entry_id_from_context(context)
                    entry = select_random_mode_entry(
                        pool.mode, previous_id, recent_entry_ids=previous
                    )
                    self.assertNotIn(entry.entry_id, history[-RECENT_ENTRY_LIMIT:])
                    history.append(entry.entry_id)
                    game_context = random_context_for_entry(
                        pool.mode,
                        entry,
                        previous_entry_id=previous_id,
                        recent_entry_ids=previous,
                    )
                    self.assertEqual(game_context["recentEntryIds"], history[-RECENT_ENTRY_LIMIT:])
                    saved = json.loads(json.dumps(game_context))
                    context = rematch_context_for_game(saved, f"game{index}")
                    self.assertEqual(context["recentEntryIds"], saved["recentEntryIds"])
                self.assertEqual(history[0], history[6])

    def test_recent_exclusions_preserve_remaining_weights(self):
        recent = [entry.entry_id for entry in WILD29_POOL.entries[:3]]
        expected = [entry for entry in WILD29_POOL.entries[3:] for _ in range(entry.weight)]
        with patch("random_modes.secrets.randbelow") as draw:
            for ticket, entry in enumerate(expected):
                draw.return_value = ticket
                self.assertEqual(
                    select_random_mode_entry("wild29", recent[-1], recent_entry_ids=recent), entry
                )
                draw.assert_called_with(len(expected))

    def test_small_pool_releases_oldest_without_repeating_immediately(self):
        first, second = WILD29_POOL.entries[:2]
        pool = replace(WILD29_POOL, entries=(first, second))
        with (
            patch.dict(RANDOM_MODE_POOLS, {pool.mode: pool}),
            patch("random_modes.secrets.randbelow", return_value=0),
        ):
            self.assertEqual(
                select_random_mode_entry(
                    pool.mode, second.entry_id, recent_entry_ids=[first.entry_id, second.entry_id]
                ),
                first,
            )

    def test_unavailable_fsx_entries_do_not_block_the_session(self):
        recent = [entry.entry_id for entry in RANDOM_DICE_POOL.entries[-5:]]
        with (
            patch("random_modes.fsx_available", return_value=False),
            patch("random_modes.secrets.randbelow", return_value=0),
        ):
            self.assertEqual(
                select_random_mode_entry("randomdice", recent[-1], recent_entry_ids=recent),
                RANDOM_DICE_POOL.entries[0],
            )

    def test_history_is_bounded_sanitized_and_does_not_mutate_saved_context(self):
        raw = {"recentEntryIds": ["old", "a", 3, "b", "a", "c"], "entryId": "d"}
        original = json.loads(json.dumps(raw))
        self.assertEqual(recent_entry_ids_from_context(raw), ["b", "a", "c", "d"])
        self.assertEqual(raw, original)
        for invalid in (None, "bad", 3, {}):
            self.assertEqual(
                recent_entry_ids_from_context({"recentEntryIds": invalid, "entryId": "latest"}),
                ["latest"],
            )
        legacy = rematch_context_for_game(
            {"mode": "randomdice", "entryId": "dice-atomic"}, "legacy"
        )
        self.assertEqual(legacy["recentEntryIds"], ["dice-atomic"])
        self.assertEqual(
            random_context_for_entry("randomdice", RANDOM_DICE_POOL.entries[0])["recentEntryIds"],
            ["dice-atomic"],
        )

    def test_random_pool_real_variant_keys_are_expected(self) -> None:
        self.assertEqual(
            {(entry.variant, entry.chess960) for entry in WILD29_POOL.entries},
            {
                ("losers", False),
                ("chess", True),
                ("crazyhouse", False),
                ("3check", False),
                ("giveaway", False),
                ("atomic", False),
            },
        )


if __name__ == "__main__":
    unittest.main()
