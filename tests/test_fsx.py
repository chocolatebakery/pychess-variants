import unittest
from unittest.mock import Mock, patch

from compress import decode_move_spell, encode_move_spell
from fairy.fairy_board import (
    FairyBoard,
    engine_for_variant,
    get_san_moves,
    sf,
    sf_alice,
    validate_fen,
)
from fsx import FSX_VARIANTS, fsx_available, fsx_engine
from variants import RATED_VARIANTS, get_server_variant


class EngineRoutingTest(unittest.TestCase):
    def test_official_and_alice_keep_their_engines(self):
        for variant in ("chess", "atomic", "berolina", "kinglet", "torpedo"):
            self.assertIs(engine_for_variant(variant), sf)
        self.assertIs(engine_for_variant("alice"), sf_alice)

    def test_fsx_routes_only_explicit_keys(self):
        engine = Mock()
        with patch("fairy.fairy_board.fsx_engine", return_value=engine):
            for variant in FSX_VARIANTS:
                self.assertIs(engine_for_variant(variant), engine)

    def test_missing_fsx_never_falls_back_to_chess(self):
        with patch("fsx._fsx", None):
            self.assertFalse(fsx_available())
            with self.assertRaisesRegex(ValueError, "FSX is not installed"):
                FairyBoard("rifle-chess")

    def test_fsx_has_no_independent_ratings(self):
        for variant in FSX_VARIANTS:
            self.assertNotIn(variant, RATED_VARIANTS)
            self.assertFalse(get_server_variant(variant, False).rating_enabled)

    def test_spell_codec_preserves_the_complete_compound_move(self):
        for move in ("e2e4", "f@e7,e2e4", "j@e5,e2e6", "f@h8,a7a8q"):
            self.assertEqual(decode_move_spell(encode_move_spell(move)), move)
            codec = get_server_variant("spell-chess", False)
            self.assertEqual(codec.move_decoding(codec.move_encoding(move)), move)

    def test_spell_codec_rejects_malformed_import_tokens(self):
        for move in ("bad", "f@a9,e2e4", "j@e5,e2e4,f@a1", "e7e8k"):
            with self.subTest(move=move), self.assertRaises(ValueError):
                encode_move_spell(move)


@unittest.skipUnless(fsx_available(), "FSX extension not installed on this platform")
class FsxRulesTest(unittest.TestCase):
    def test_monster_requires_a_black_pass_between_white_moves(self):
        board = FairyBoard("monster")
        initial = board.fen
        for move in ("e2e4", "0000", "d2d4", "e7e5"):
            self.assertIn(move, board.legal_moves())
            if move == "0000":
                self.assertEqual(board.legal_moves(), ["0000"])
                self.assertEqual(board.get_san(move), "--")
            board.push(move)
        self.assertEqual(board.color, 0)
        self.assertEqual(
            get_san_moves("monster", initial, board.move_stack, False, board.notation),
            ["e4", "--", "d4", "e5"],
        )
        codec = get_server_variant("monster", False)
        for move in board.move_stack:
            self.assertEqual(codec.move_decoding(codec.move_encoding(move)), move)
        for _ in range(4):
            board.pop()
        self.assertEqual(board.fen, initial)

    def test_monster_allows_exposed_king_and_ends_on_king_capture(self):
        board = FairyBoard("monster", "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1")
        self.assertIn("e1d2", board.legal_moves())
        board = FairyBoard("monster", "8/8/8/8/8/8/4k3/4K3 w - - 0 1")
        self.assertIn("e1e2", board.legal_moves())
        board.push("e1e2")
        self.assertTrue(board.is_immediate_game_end()[0])

    def test_every_fsx_variant_supports_moves_notation_fen_and_undo(self):
        for variant in sorted(FSX_VARIANTS):
            with self.subTest(variant=variant):
                board = FairyBoard(variant)
                self.assertIs(board.sf, fsx_engine())
                initial = board.fen
                self.assertEqual(validate_fen(initial, variant, False), board.sf.FEN_OK)
                move = board.legal_moves()[0]
                self.assertTrue(board.get_san(move))
                self.assertTrue(get_san_moves(variant, initial, [move], False, board.notation))
                board.push(move)
                self.assertNotEqual(board.fen, initial)
                self.assertTrue(board.legal_moves())
                self.assertFalse(board.is_immediate_game_end()[0])
                board.pop()
                self.assertEqual(board.fen, initial)

    def test_rifle_capture_leaves_attacker_on_origin(self):
        board = FairyBoard("rifle-chess", "7k/8/8/8/8/8/p7/R6K w - - 0 1")
        self.assertIn("a1a2", board.legal_moves())
        board.push("a1a2")
        self.assertEqual(board.fen.split()[0], "7k/8/8/8/8/8/8/R6K")

    def test_brotherhood_blocks_same_type_capture(self):
        fen = "7k/8/8/8/8/8/r7/R6K w - - 0 1"
        self.assertIn("a1a2", FairyBoard("chess", fen).legal_moves())
        self.assertNotIn("a1a2", FairyBoard("brotherhood", fen).legal_moves())

    def test_freeze_is_one_turn_and_survives_fen_roundtrip(self):
        from utils import sanitize_fen

        board = FairyBoard("spell-chess")
        initial = board.fen
        move = "f@e7,e2e4"
        self.assertIn(move, board.legal_moves())
        self.assertEqual(board.get_san(move), "f@e7,e4")
        self.assertEqual(
            get_san_moves("spell-chess", initial, [move], False, board.notation), ["f@e7,e4"]
        )
        board.push(move)
        self.assertEqual(board.ply, 1)
        self.assertEqual(board.fen.split()[1], "b")
        self.assertNotIn("e7e6", board.legal_moves())
        self.assertEqual(sanitize_fen("spell-chess", board.fen, False), (True, board.fen))
        restored = FairyBoard("spell-chess", board.fen)
        self.assertEqual(set(restored.legal_moves()), set(board.legal_moves()))
        board.pop()
        self.assertEqual(board.fen, initial)

    def test_jump_cast_and_promotion_use_the_complete_move(self):
        board = FairyBoard("spell-chess", "7k/8/8/p7/8/p7/8/R3K3[J] w - - 0 1")
        self.assertIn("j@a3,a1a5", board.legal_moves())
        board.push("j@a3,a1a5")
        self.assertIn("R7", board.fen)
        self.assertEqual(board.ply, 1)
