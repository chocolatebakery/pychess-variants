import json
import unittest
from typing import cast
from unittest.mock import AsyncMock, patch

import test_logger
from catalogued_variants import (
    FSF_CATALOGUED_BUILTIN_VARIANTS,
    _build_fsf_builtin_doc,
    register_catalogued_variant_doc,
)
from const import AI_OFFLINE_MESSAGE, CASUAL
from game import Game
from mongomock_motor import AsyncMongoMockClient
from newid import id8
from pychess_global_app_state_utils import get_app_state
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from random_modes import RANDOM_DICE_POOL, RANDOM_MODE_POOLS, random_context_for_entry
from seek import Seek
from user import User
from utils import MAX_CUSTOM_FEN_LENGTH, join_seek, sanitize_fen
from variants import unregister_catalogued_server_variant
from wsl import handle_create_ai_challenge
from wsr import handle_rematch

from server import init_state, make_app

test_logger.init_test_logger()


class RematchTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = make_app(db_client=cast(AsyncMongoClient, AsyncMongoMockClient(tz_aware=True)))
        await init_state(self.app)
        self.state = get_app_state(self.app)
        self.player = User(self.state, username="rematch-player")
        self.opponent = User(self.state, username="rematch-opponent")
        for user in (self.player, self.opponent):
            self.state.users[user.username] = user
        self.bot = self.state.users["Fairy-Stockfish"]
        self.bot.online = True
        self.state.users["Alice-Stockfish"] = User(
            self.state, username="Alice-Stockfish", bot=True, title="BOT"
        )
        self.bot_start = self.enterContext(
            patch("wsr.send_bot_game_start_unless_streaming", new_callable=AsyncMock)
        )

    async def asyncTearDown(self):
        await self.state.server_shutdown()

    def register_kingless_variants(self):
        register_catalogued_variant_doc(
            self.state, _build_fsf_builtin_doc("joust", FSF_CATALOGUED_BUILTIN_VARIANTS["joust"])
        )
        register_catalogued_variant_doc(
            self.state,
            {
                "name": "rematch_way",
                "ini": """[rematch_way]
maxRank = 8
maxFile = 8
startFen = 8/8/8/8/8/8/8/8[PPPPPPPPpppppppp] w - - 0 1
pieceDrops = true
doubleStep = false
castling = false
immobilityIllegal = false
connectN = 5
connectPieceTypes = p
customPiece1 = p:mKmDmA
""",
                "startFen": "8/8/8/8/8/8/8/8[PPPPPPPPpppppppp] w - - 0 1",
                "enabled": True,
                "visibility": "public",
            },
        )
        self.addCleanup(unregister_catalogued_server_variant, "rematch_way")

    async def finished_game(self, variant, opponent):
        current = Game(self.state, id8(), variant, "", self.player, opponent)
        self.state.games[current.id] = current
        await current.game_ended(self.player, "resign")
        if not opponent.bot:
            current.rematch_offers.add(opponent.username)
        return current

    async def rematch(self, current, ws):
        return await handle_rematch(
            self.state,
            ws,
            self.player,
            {"type": "rematch", "gameId": current.id, "handicap": False},
            current,
        )

    async def test_kingless_community_rematches_preserve_saved_start(self):
        self.register_kingless_variants()
        oversized_pocket = "8/8/8/8/8/8/8/8[" + "P" * 17 + "] w - - 0 1"
        self.assertFalse(sanitize_fen("rematch_way", oversized_pocket, False)[0])
        for variant in ("joust", "rematch_way"):
            for opponent in (self.bot, self.opponent):
                with self.subTest(variant=variant, bot=opponent.bot):
                    current = await self.finished_game(variant, opponent)
                    self.assertTrue(current.initial_fen)
                    response = await self.rematch(current, AsyncMock())
                    self.assertEqual(response["type"], "new_game")
                    rematch = self.state.games[response["gameId"]]
                    self.assertEqual(rematch.initial_fen, current.initial_fen)
                    self.assertEqual(current.rematch_id, rematch.id)
                    self.assertIs(rematch.wplayer, opponent)
                    self.assertIs(rematch.bplayer, self.player)
                    await rematch.game_ended(self.player, "resign")
        self.assertEqual(self.bot_start.await_count, 2)

    async def test_failed_rematches_clean_up_and_can_be_retried(self):
        for opponent in (self.bot, self.opponent):
            with self.subTest(bot=opponent.bot):
                current = await self.finished_game("chess", opponent)
                existing_games = set(self.state.games)
                existing_seeks = set(self.state.seeks)
                existing_queues = set(self.bot.game_queues)
                opponent.blocked.add(self.player.username)
                ws = AsyncMock()
                with patch("wsr.round_broadcast", new_callable=AsyncMock) as broadcast:
                    for _ in range(2):
                        response = await self.rematch(current, ws)
                        self.assertEqual(response["type"], "error")
                        self.assertEqual(response["message"], "You cannot accept this seek.")
                        self.assertEqual(json.loads(ws.send_str.await_args.args[0]), response)
                        self.assertIsNone(current.rematch_id)
                        self.assertEqual(set(self.state.games), existing_games)
                        self.assertEqual(set(self.state.seeks), existing_seeks)
                        self.assertEqual(set(self.bot.game_queues), existing_queues)
                    broadcast.assert_not_awaited()
                opponent.blocked.remove(self.player.username)
                response = await self.rematch(current, ws)
                self.assertEqual(response["type"], "new_game")
                self.assertEqual(current.rematch_id, response["gameId"])
                await self.state.games[response["gameId"]].game_ended(self.player, "resign")

    async def test_community_fen_validation_still_rejects_invalid_input(self):
        register_catalogued_variant_doc(
            self.state, _build_fsf_builtin_doc("joust", FSF_CATALOGUED_BUILTIN_VARIANTS["joust"])
        )
        for fen in (
            "not a FEN",
            "8/8/8/4n3/3N4/8/8/8 x - - 0 1",
            "8" * (MAX_CUSTOM_FEN_LENGTH + 1),
        ):
            with self.subTest(fen=fen[:50]):
                self.assertFalse(sanitize_fen("joust", fen, False)[0])

    async def ai_challenge_entry(self, mode, entry, *, rm=False):
        ws = AsyncMock()
        with (
            patch("utils.select_random_mode_entry", return_value=entry) as select,
            patch("wsl.has_available_fishnet_worker", return_value=True),
        ):
            await handle_create_ai_challenge(
                self.state,
                ws,
                self.player,
                {
                    "type": "create_ai_challenge",
                    "variant": mode,
                    "profileid": "Fairy-Stockfish",
                    "rm": rm,
                    "fen": "",
                    "color": "w",
                    "minutes": 5,
                    "increment": 3,
                    "byoyomiPeriod": 0,
                    "rated": False,
                    "chess960": False,
                    "level": 4,
                },
            )
        select.assert_called_once_with(mode, None)
        return json.loads(ws.send_str.await_args.args[0])

    async def test_random_mode_ai_games_resolve_every_supported_pool_entry(self):
        alice = self.state.users["Alice-Stockfish"]
        alice.online = True
        with (
            patch("fishnet.has_available_fishnet_worker", return_value=True),
            patch("wsl.send_bot_game_start_unless_streaming", new_callable=AsyncMock) as start,
        ):
            for mode, pool in RANDOM_MODE_POOLS.items():
                for entry in pool.entries:
                    if entry.variant == "fogofwar":
                        continue
                    with self.subTest(mode=mode, entry=entry.entry_id):
                        response = await self.ai_challenge_entry(mode, entry)
                        self.assertEqual(response["type"], "new_game")
                        created = self.state.games[response["gameId"]]
                        self.assertEqual(created.variant, entry.variant)
                        self.assertEqual(created.board.variant, entry.variant)
                        self.assertEqual(created.chess960, entry.chess960)
                        self.assertEqual(created.random_context["entryId"], entry.entry_id)
                        self.assertEqual(created.level, 4)
                        self.assertEqual(created.rated, CASUAL)
                        expected_bot = alice if entry.variant == "alice" else self.bot
                        self.assertIs(created.bplayer, expected_bot)
                        self.assertIn(created.id, expected_bot.game_queues)
                        start.assert_awaited_with(expected_bot, created)
                        await created.game_ended(self.player, "resign")

    async def test_every_dice_result_is_playable_by_humans_and_random_mover(self):
        random_mover = self.state.users["Random-Mover"]
        with patch("wsl.send_bot_game_start_unless_streaming", new_callable=AsyncMock):
            for entry in RANDOM_DICE_POOL.entries:
                with self.subTest(variant=entry.variant):
                    seek = Seek(id8(), self.player, "randomdice", color="w", player1=self.player)
                    with patch("utils.select_random_mode_entry", return_value=entry):
                        response = await join_seek(self.state, self.opponent, seek)
                    self.assertEqual(response["type"], "new_game")
                    created = self.state.games[response["gameId"]]
                    self.assertEqual(created.variant, entry.variant)
                    self.assertEqual(created.random_context["poolVersion"], 3)
                    self.assertIs(created.bplayer, self.opponent)
                    self.assertTrue(created.board.legal_moves())
                    if entry.variant == "janggi":
                        self.assertTrue(created.wsetup)
                        self.assertTrue(created.bsetup)
                    if entry.variant == "fogofwar":
                        self.assertTrue(created.fow)
                        for color in (None, 0, 1):
                            self.assertNotEqual(
                                created.get_board(persp_color=color)["fen"], created.board.fen
                            )
                    await created.game_ended(self.player, "resign")

                    response = await self.ai_challenge_entry("randomdice", entry, rm=True)
                    self.assertEqual(response["type"], "new_game")
                    created = self.state.games[response["gameId"]]
                    self.assertEqual(created.variant, entry.variant)
                    self.assertIs(created.bplayer, random_mover)
                    self.assertEqual(created.level, 0)
                    self.assertEqual(created.byoyomi_period, 0)
                    await created.game_ended(self.player, "resign")

    async def test_dice_reports_unsupported_fog_and_unavailable_alice_without_creating_games(self):
        alice = self.state.users["Alice-Stockfish"]
        for variant, worker, online in (
            ("fogofwar", True, True),
            ("alice", False, True),
            ("alice", True, False),
        ):
            with self.subTest(variant=variant, worker=worker, online=online):
                alice.online = online
                entry = next(
                    entry for entry in RANDOM_DICE_POOL.entries if entry.variant == variant
                )
                games = set(self.state.games)
                queues = (set(self.bot.game_queues), set(alice.game_queues))
                with (
                    patch("fishnet.has_available_fishnet_worker", return_value=worker),
                    patch(
                        "wsl.send_bot_game_start_unless_streaming", new_callable=AsyncMock
                    ) as start,
                ):
                    response = await self.ai_challenge_entry("randomdice", entry)
                self.assertEqual(response["type"], "error")
                self.assertIn("Random-Mover", response["message"])
                self.assertEqual(set(self.state.games), games)
                self.assertEqual((set(self.bot.game_queues), set(alice.game_queues)), queues)
                start.assert_not_awaited()

    async def test_dice_ai_rematches_switch_between_alice_and_fairy_stockfish(self):
        alice = self.state.users["Alice-Stockfish"]
        alice.online = True
        entries = {entry.variant: entry for entry in RANDOM_DICE_POOL.entries}
        for previous, selected, old_bot, new_bot in (
            ("atomic", "alice", self.bot, alice),
            ("alice", "makruk", alice, self.bot),
        ):
            with self.subTest(previous=previous, selected=selected):
                current = await self.finished_game(previous, old_bot)
                current.random_context = random_context_for_entry("randomdice", entries[previous])
                with (
                    patch("utils.select_random_mode_entry", return_value=entries[selected]),
                    patch("wsr.has_available_fishnet_worker", return_value=True),
                    patch("fishnet.has_available_fishnet_worker", return_value=True),
                ):
                    response = await self.rematch(current, AsyncMock())
                self.assertEqual(response["type"], "new_game")
                rematch = self.state.games[response["gameId"]]
                self.assertEqual(rematch.variant, selected)
                self.assertIs(rematch.wplayer, new_bot)
                self.assertIs(rematch.bplayer, self.player)
                self.assertIn(rematch.id, new_bot.game_queues)
                self.bot_start.assert_awaited_with(new_bot, rematch)
                await rematch.game_ended(self.player, "resign")

    async def test_dice_alice_requires_a_bot_account(self):
        del self.state.users["Alice-Stockfish"]
        entry = next(entry for entry in RANDOM_DICE_POOL.entries if entry.variant == "alice")
        with patch("fishnet.has_available_fishnet_worker", return_value=True):
            response = await self.ai_challenge_entry("randomdice", entry)
        self.assertEqual(response["type"], "error")
        self.assertIn("Alice-Stockfish is offline", response["message"])
        self.assertFalse(self.state.games)

    async def test_failed_dice_ai_rematches_leave_no_seek_or_queue(self):
        entries = {entry.variant: entry for entry in RANDOM_DICE_POOL.entries}
        current = await self.finished_game("atomic", self.bot)
        current.random_context = random_context_for_entry("randomdice", entries["atomic"])
        games = set(self.state.games)
        seeks = set(self.state.seeks)
        queues = set(self.bot.game_queues)
        for variant in ("fogofwar", "alice"):
            with self.subTest(variant=variant):
                with (
                    patch("utils.select_random_mode_entry", return_value=entries[variant]),
                    patch("wsr.has_available_fishnet_worker", return_value=True),
                    patch("fishnet.has_available_fishnet_worker", return_value=False),
                ):
                    response = await self.rematch(current, AsyncMock())
                self.assertEqual(response["type"], "error")
                self.assertIsNone(current.rematch_id)
                self.assertEqual(set(self.state.games), games)
                self.assertEqual(set(self.state.seeks), seeks)
                self.assertEqual(set(self.bot.game_queues), queues)
                self.bot_start.assert_not_awaited()

    async def test_random_ai_rematch_rerolls_and_reports_an_offline_worker(self):
        for mode, pool in RANDOM_MODE_POOLS.items():
            with self.subTest(mode=mode):
                previous = pool.entries[0]
                current = Game(
                    self.state,
                    id8(),
                    previous.variant,
                    "",
                    self.player,
                    self.bot,
                    level=4,
                    random_context=random_context_for_entry(mode, previous),
                )
                self.state.games[current.id] = current
                await current.game_ended(self.player, "resign")
                before = set(self.state.games)
                with patch("wsr.has_available_fishnet_worker", return_value=False):
                    response = await self.rematch(current, AsyncMock())
                self.assertEqual(response, {"type": "error", "message": AI_OFFLINE_MESSAGE})
                self.assertIsNone(current.rematch_id)
                self.assertEqual(set(self.state.games), before)

                with (
                    patch("wsr.has_available_fishnet_worker", return_value=True),
                    patch("utils.select_random_mode_entry", return_value=pool.entries[1]),
                ):
                    response = await self.rematch(current, AsyncMock())
                self.assertEqual(response["type"], "new_game")
                rematch = self.state.games[response["gameId"]]
                self.assertEqual(rematch.random_context["mode"], mode)
                self.assertNotEqual(rematch.random_context["entryId"], previous.entry_id)
                self.assertEqual(rematch.random_context["previousGameId"], current.id)
                self.assertEqual(rematch.level, 4)
                self.assertIs(rematch.wplayer, self.bot)
                await rematch.game_ended(self.player, "resign")
