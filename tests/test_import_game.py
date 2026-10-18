import unittest
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import test_logger
from aiohttp.test_utils import AioHTTPTestCase
from compress import encode_move_standard
from fairy import FairyBoard
from fsx import fsx_available
from mongomock_motor import AsyncMongoMockClient
from pychess_global_app_state_utils import get_app_state
from utils import _encode_import_moves

from server import make_app

test_logger.init_test_logger()


class ImportGameMoveEncodingTestCase(unittest.TestCase):
    def test_ignores_extra_whitespace(self):
        moves, error = _encode_import_moves(
            "e2e4   e7e5  ",
            move_encoding=encode_move_standard,
            grand_variant=False,
        )
        self.assertIsNone(error)
        self.assertEqual(len(moves), 2)

    def test_rejects_invalid_standard_move(self):
        moves, error = _encode_import_moves(
            "e2e4 bad",
            move_encoding=encode_move_standard,
            grand_variant=False,
        )
        self.assertEqual(moves, [])
        self.assertEqual(error, "Invalid move 'bad' at ply 2 in imported PGN.")

    def test_rejects_invalid_grand_move(self):
        moves, error = _encode_import_moves(
            "a10a9 a",
            move_encoding=encode_move_standard,
            grand_variant=True,
        )
        self.assertEqual(moves, [])
        self.assertEqual(error, "Invalid move 'a' at ply 2 in imported PGN.")


class ImportGameCleanupTestCase(AioHTTPTestCase):
    async def get_application(self):
        return make_app(db_client=AsyncMongoMockClient(tz_aware=True))

    async def tearDownAsync(self):
        await self.client.close()

    async def test_import_game_cancels_temporary_clock(self):
        class DummyGame:
            instances: ClassVar[list[object]] = []

            def __init__(
                self,
                app_state,
                game_id,
                variant,
                initial_fen,
                wplayer,
                bplayer,
                rated,
                chess960,
                create,
            ):
                self.server_variant = SimpleNamespace(code="n")
                self.byoyomi_period = 0
                self.level = 0
                self.initial_fen = initial_fen
                self.chess960 = chess960
                self.stopwatch = SimpleNamespace(cancel=AsyncMock())
                DummyGame.instances.append(self)

        with (
            patch("utils.Game", DummyGame),
            patch("utils.new_id", AsyncMock(return_value="import123")),
        ):
            resp = await self.client.post(
                "/import",
                data={
                    "username": "Importer",
                    "White": "Importer",
                    "Black": "Opponent",
                    "Variant": "Chess",
                    "Result": "1-0",
                    "Status": "1",
                    "Date": "2026.04.01",
                    "TimeControl": "60+0",
                    "final_fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                    "moves": "e2e4 e7e5",
                },
            )

        self.assertEqual(resp.status, 200)
        self.assertEqual(len(DummyGame.instances), 1)
        DummyGame.instances[0].stopwatch.cancel.assert_awaited_once()

    async def test_import_game_rejects_missing_username(self):
        resp = await self.client.post("/import", data={"moves": "e2e4"})

        self.assertEqual(resp.status, 200)
        self.assertEqual(await resp.json(), {"error": "Missing username."})

    @unittest.skipUnless(fsx_available(), "Requires FSX extension")
    async def test_import_uses_fsx_and_preserves_spell_tokens(self):
        for variant in ("rifle-chess", "brotherhood", "spell-chess"):
            with self.subTest(variant=variant):
                board = FairyBoard(variant)
                move = "f@e7,e2e4" if variant == "spell-chess" else "e2e4"
                initial = board.fen
                board.push(move)
                resp = await self.client.post(
                    "/import",
                    data={
                        "username": "Importer",
                        "White": "Importer",
                        "Black": "Opponent",
                        "Variant": variant,
                        "FEN": initial,
                        "Result": "*",
                        "Status": "-1",
                        "final_fen": board.fen,
                        "moves": move,
                    },
                )
                body = await resp.json()
                self.assertIn("gameId", body)
                state = get_app_state(self.app)
                document = await state.db.game.find_one({"_id": body["gameId"]})
                self.assertEqual(document["v"], variant)
                self.assertEqual(document["f"], board.fen)
                if variant == "spell-chess":
                    self.assertEqual(document["m"], [move])

    async def test_import_bpgn_rejects_missing_pgn(self):
        resp = await self.client.post("/import_bpgn", data={})

        self.assertEqual(resp.status, 200)
        self.assertEqual(await resp.json(), {"error": "Missing pgn."})

    async def test_import_bpgn_rejects_corrupt_fen(self):
        bpgn = (
            '[Event "Import test"]\n'
            '[Variant "Bughouse"]\n'
            '[WhiteA "Alice"]\n'
            '[BlackA "Bob"]\n'
            '[WhiteB "Carol"]\n'
            '[BlackB "Dave"]\n'
            '[FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR[] w KQkq - 0 1"]\n'
            "\n"
            "*\n"
        )

        resp = await self.client.post("/import_bpgn", data={"pgn": bpgn})

        self.assertEqual(resp.status, 200)
        self.assertEqual(await resp.json(), {"error": "Invalid BPGN: fen corrupt."})

    async def test_import_bpgn_rejects_missing_bughouse_player_headers(self):
        bpgn = "[Event “Import test”]\n\n*\n"

        resp = await self.client.post("/import_bpgn", data={"pgn": bpgn})

        self.assertEqual(resp.status, 200)
        self.assertEqual(
            await resp.json(),
            {"error": "Invalid BPGN: missing bughouse player headers."},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
