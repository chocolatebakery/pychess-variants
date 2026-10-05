from __future__ import annotations

import unittest
from unittest.mock import patch

from random_modes import (
    RANDOM_DICE_POOL,
    RANDOM_MODE_DICE,
    RANDOM_MODE_WILD29,
    WILD29_POOL,
    WILD29_UNIMPLEMENTED_ICC_ENTRIES,
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

        with patch("random_modes.random.choices", return_value=[expected_entry]) as choices:
            selected = select_random_mode_entry(RANDOM_MODE_WILD29, previous_entry.entry_id)

        self.assertEqual(selected, expected_entry)
        population = choices.call_args.args[0]
        self.assertNotIn(previous_entry, population)

    def test_context_round_trips_previous_entry_for_rematch(self) -> None:
        entry = WILD29_POOL.entries[0]
        context = random_context_for_entry(RANDOM_MODE_WILD29, entry)

        rematch_context = rematch_context_for_game(context, "game123")

        self.assertIsNotNone(rematch_context)
        assert rematch_context is not None
        self.assertEqual(rematch_context["mode"], RANDOM_MODE_WILD29)
        self.assertEqual(previous_entry_id_from_context(rematch_context), entry.entry_id)
        self.assertEqual(rematch_context["previousGameId"], "game123")

    def test_random_dice_rematches_exclude_each_previous_result(self) -> None:
        for previous_entry in RANDOM_DICE_POOL.entries:
            with self.subTest(variant=previous_entry.variant):
                context = random_context_for_entry(RANDOM_MODE_DICE, previous_entry)
                rematch_context = rematch_context_for_game(context, "dicegame")
                assert rematch_context is not None

                with patch(
                    "random_modes.random.choices", side_effect=lambda pool, **_: [pool[0]]
                ) as choices:
                    selected = select_random_mode_entry(
                        RANDOM_MODE_DICE, previous_entry_id_from_context(rematch_context)
                    )

                self.assertNotEqual(selected.entry_id, previous_entry.entry_id)
                population = choices.call_args.args[0]
                self.assertEqual(
                    {entry.entry_id for entry in population},
                    {entry.entry_id for entry in RANDOM_DICE_POOL.entries}
                    - {previous_entry.entry_id},
                )
                self.assertEqual(
                    choices.call_args.kwargs["weights"], [1] * (len(RANDOM_DICE_POOL.entries) - 1)
                )

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
