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
        self.assertEqual({entry.entry_id for entry in WILD29_POOL.entries}, {
            "icc-wild17",
            "icc-wild22",
            "icc-wild23",
            "icc-wild25",
            "icc-wild26",
            "icc-wild27",
        })
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
