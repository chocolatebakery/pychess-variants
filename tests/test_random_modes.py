from __future__ import annotations

import unittest
from collections import Counter
from dataclasses import replace
from unittest.mock import patch

from random_modes import (
    RANDOM_DICE_POOL,
    RANDOM_MODE_DICE,
    RANDOM_MODE_POOLS,
    RANDOM_MODE_WILD29,
    WILD29_POOL,
    WILD29_UNIMPLEMENTED_ICC_ENTRIES,
    RandomModeError,
    is_random_mode,
    previous_entry_id_from_context,
    random_context_for_entry,
    rematch_context_for_game,
    select_random_mode_entry,
)


class RandomModesTestCase(unittest.TestCase):
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

    def test_secure_draw_does_not_prevent_revisiting_older_results(self) -> None:
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
        for version in (1, 2):
            with self.subTest(version=version):
                old_context: dict[str, object] = {
                    "mode": RANDOM_MODE_DICE,
                    "poolId": RANDOM_DICE_POOL.pool_id,
                    "poolVersion": version,
                    "entryId": "dice-chess960",
                }

                rematch_context = rematch_context_for_game(old_context, "oldgame")

                assert rematch_context is not None
                self.assertEqual(rematch_context["poolVersion"], 3)
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
                "racingkings",
                "fogofwar",
                "alice",
                "makruk",
                "shogi",
                "xiangqi",
                "janggi",
            },
        )
        self.assertEqual(len(RANDOM_DICE_POOL.entries), 21)
        self.assertEqual(len({entry.entry_id for entry in RANDOM_DICE_POOL.entries}), 21)
        self.assertTrue(all(entry.weight == 1 for entry in RANDOM_DICE_POOL.entries))

    def test_new_dice_variants_use_native_rules_and_can_make_a_move(self) -> None:
        from fairy import FairyBoard

        for variant in (
            "atomar",
            "racingkings",
            "fogofwar",
            "alice",
            "makruk",
            "shogi",
            "xiangqi",
            "janggi",
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
