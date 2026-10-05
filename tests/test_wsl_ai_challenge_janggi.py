import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import test_logger
from const import AI_OFFLINE_MESSAGE
from utils import join_seek
from variants import register_catalogued_server_variant, unregister_catalogued_server_variant
from wsl import handle_accept_seek, handle_create_ai_challenge

test_logger.init_test_logger()


class DummyUser:
    def __init__(self, username: str, *, bot: bool = False) -> None:
        self.username = username
        self.anon = False
        self.bot = bot
        self.blocked: set[str] = set()
        self.title = ""
        self.game_in_progress = None

    def get_rating_value(self, _variant: str, _chess960: bool | None) -> int:
        return 1500


def create_ai_payload(variant: str = "janggi") -> dict[str, object]:
    return {
        "type": "create_ai_challenge",
        "rm": False,
        "user": "tester",
        "variant": variant,
        "fen": "",
        "minutes": 5,
        "increment": 3,
        "byoyomiPeriod": 1,
        "rated": False,
        "level": 2,
        "chess960": False,
        "color": "b",
        "profileid": "Fairy-Stockfish",
    }


class CataloguedAiJoinSeekAccessTestCase(unittest.IsolatedAsyncioTestCase):
    variant_name = "privatebotai"

    def setUp(self) -> None:
        register_catalogued_server_variant(self.variant_name, "Private Bot AI")

    def tearDown(self) -> None:
        unregister_catalogued_server_variant(self.variant_name)

    def _app_state(self) -> SimpleNamespace:
        return SimpleNamespace(
            catalogued_variants={
                self.variant_name: {
                    "name": self.variant_name,
                    "author": "owner",
                    "visibility": "private",
                    "enabled": True,
                    "archived": False,
                }
            }
        )

    def _seek(self, owner: DummyUser) -> SimpleNamespace:
        return SimpleNamespace(
            id="seek1",
            creator=owner,
            variant=self.variant_name,
            chess960=False,
            day=0,
            target="",
            fen="",
            player1=owner,
            player2=None,
            is_expired=lambda: False,
        )

    async def test_internal_bot_can_join_private_catalogued_seek_for_owner_ai_game(self):
        owner = DummyUser("owner")
        bot = DummyUser("Random-Mover", bot=True)
        seek = self._seek(owner)
        new_game = AsyncMock(return_value={"type": "new_game", "gameId": "game1"})

        with patch("utils.new_game", new=new_game):
            response = await join_seek(self._app_state(), bot, seek)

        self.assertEqual(response, {"type": "new_game", "gameId": "game1"})
        self.assertIs(seek.player2, bot)
        new_game.assert_awaited_once()

    async def test_human_non_owner_still_cannot_join_private_catalogued_seek(self):
        owner = DummyUser("owner")
        other = DummyUser("other")
        seek = self._seek(owner)
        new_game = AsyncMock(return_value={"type": "new_game", "gameId": "game1"})

        with patch("utils.new_game", new=new_game):
            response = await join_seek(self._app_state(), other, seek)

        self.assertEqual(
            response, {"type": "error", "message": "This user-defined variant is not available."}
        )
        self.assertIsNone(seek.player2)
        new_game.assert_not_awaited()


class WslCreateAiChallengeJanggiTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_variant_forces_random_mover(self):
        fairy_engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        random_mover = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        app_state = SimpleNamespace(
            users={"Fairy-Stockfish": fairy_engine, "Random-Mover": random_mover},
            games={"g1": SimpleNamespace(id="g1", variant="jieqi", game_start={"type": "gs"})},
            db=None,
        )
        seek_ctor = Mock(return_value=object())
        join_seek = AsyncMock(return_value={"type": "new_game", "gameId": "g1"})

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch("wsl.join_seek", new=join_seek),
            patch("wsl.Seek", new=seek_ctor),
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload("jieqi")
            )

        join_seek.assert_awaited_once()
        self.assertIs(join_seek.await_args.args[1], random_mover)
        self.assertEqual(seek_ctor.call_args.kwargs["level"], 0)

    async def test_alice_without_capable_fishnet_worker_forces_random_mover(self):
        fairy_engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        random_mover = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        app_state = SimpleNamespace(
            users={"Fairy-Stockfish": fairy_engine, "Random-Mover": random_mover},
            games={"g1": SimpleNamespace(id="g1", variant="alice", game_start={"type": "gs"})},
            db=None,
        )
        join_seek = AsyncMock(return_value={"type": "new_game", "gameId": "g1"})

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch("wsl.join_seek", new=join_seek),
            patch("wsl.Seek", return_value=object()),
            patch("wsl.has_available_fishnet_worker", return_value=False) as availability,
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload("alice")
            )

        availability.assert_called_once_with(app_state, variant="alice")
        self.assertIs(join_seek.await_args.args[1], random_mover)

    async def test_alice_with_capable_fishnet_worker_uses_alice_stockfish_bot(self):
        fairy_engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        alice_engine = SimpleNamespace(
            username="Alice-Stockfish",
            bot=True,
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        random_mover = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        app_state = SimpleNamespace(
            users={
                "Fairy-Stockfish": fairy_engine,
                "Alice-Stockfish": alice_engine,
                "Random-Mover": random_mover,
            },
            games={"g1": SimpleNamespace(id="g1", variant="alice", game_start={"type": "gs"})},
            db=None,
        )
        join_seek = AsyncMock(return_value={"type": "new_game", "gameId": "g1"})

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch("wsl.join_seek", new=join_seek),
            patch("wsl.Seek", return_value=object()),
            patch("wsl.has_available_fishnet_worker", return_value=True) as availability,
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload("alice")
            )

        availability.assert_called_once_with(app_state, variant="alice")
        self.assertIs(join_seek.await_args.args[1], alice_engine)

    async def test_alice_with_capable_worker_but_no_bot_account_forces_random_mover(self):
        fairy_engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        random_mover = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=AsyncMock()),
            game_queues={},
            active_game_streams=set(),
        )
        app_state = SimpleNamespace(
            users={"Fairy-Stockfish": fairy_engine, "Random-Mover": random_mover},
            games={"g1": SimpleNamespace(id="g1", variant="alice", game_start={"type": "gs"})},
            db=None,
        )
        join_seek = AsyncMock(return_value={"type": "new_game", "gameId": "g1"})

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch("wsl.join_seek", new=join_seek),
            patch("wsl.Seek", return_value=object()),
            patch("wsl.has_available_fishnet_worker", return_value=True),
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload("alice")
            )

        self.assertIs(join_seek.await_args.args[1], random_mover)

    async def test_janggi_pending_setup_does_not_start_bot(self):
        bot_put = AsyncMock()
        engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=bot_put),
            game_queues={},
            active_game_streams=set(),
        )
        game = SimpleNamespace(
            id="g1", variant="janggi", bsetup=True, wsetup=False, game_start={"type": "gs"}
        )
        app_state = SimpleNamespace(
            users={"Fairy-Stockfish": engine, "Random-Mover": engine},
            games={"g1": game},
            db=None,
        )

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch(
                "wsl.join_seek", new=AsyncMock(return_value={"type": "new_game", "gameId": "g1"})
            ),
            patch("wsl.Seek", return_value=object()),
            patch("wsl.has_available_fishnet_worker", return_value=True),
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload()
            )

        self.assertIn("g1", engine.game_queues)
        bot_put.assert_not_awaited()

    async def test_janggi_after_setup_starts_bot(self):
        bot_put = AsyncMock()
        engine = SimpleNamespace(
            online=True,
            event_queue=SimpleNamespace(put=bot_put),
            game_queues={},
            active_game_streams=set(),
        )
        game = SimpleNamespace(
            id="g1", variant="janggi", bsetup=False, wsetup=False, game_start={"type": "gs"}
        )
        app_state = SimpleNamespace(
            users={"Fairy-Stockfish": engine, "Random-Mover": engine},
            games={"g1": game},
            db=None,
        )

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=AsyncMock()),
            patch(
                "wsl.join_seek", new=AsyncMock(return_value={"type": "new_game", "gameId": "g1"})
            ),
            patch("wsl.Seek", return_value=object()),
            patch("wsl.has_available_fishnet_worker", return_value=True),
        ):
            await handle_create_ai_challenge(
                app_state, object(), DummyUser("tester"), create_ai_payload()
            )

        bot_put.assert_awaited_once_with(game.game_start)

    async def test_accept_seek_janggi_pending_setup_does_not_start_bot(self):
        bot_put = AsyncMock()
        engine = SimpleNamespace(
            bot=True,
            online=True,
            event_queue=SimpleNamespace(put=bot_put),
            game_queues={},
            active_game_streams=set(),
        )
        seek = SimpleNamespace(
            id="seek1",
            creator=engine,
            variant="janggi",
            chess960=False,
            target="bot",
        )
        game = SimpleNamespace(
            id="g1", variant="janggi", bsetup=True, wsetup=False, game_start={"type": "gs"}
        )
        app_state = SimpleNamespace(
            seeks={"seek1": seek},
            games={"g1": game},
            lobby=SimpleNamespace(lobby_broadcast_seeks=AsyncMock()),
        )

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch(
                "wsl.join_seek", new=AsyncMock(return_value={"type": "new_game", "gameId": "g1"})
            ),
            patch("wsl.ws_send_json", new=AsyncMock()),
        ):
            await handle_accept_seek(
                app_state,
                object(),
                DummyUser("tester"),
                {"type": "accept_seek", "seekID": "seek1"},
            )

        self.assertIn("g1", engine.game_queues)
        bot_put.assert_not_awaited()

    async def test_accept_seek_janggi_after_setup_starts_bot(self):
        bot_put = AsyncMock()
        engine = SimpleNamespace(
            bot=True,
            online=True,
            event_queue=SimpleNamespace(put=bot_put),
            game_queues={},
            active_game_streams=set(),
        )
        seek = SimpleNamespace(
            id="seek1",
            creator=engine,
            variant="janggi",
            chess960=False,
            target="bot",
        )
        game = SimpleNamespace(
            id="g1", variant="janggi", bsetup=False, wsetup=False, game_start={"type": "gs"}
        )
        app_state = SimpleNamespace(
            seeks={"seek1": seek},
            games={"g1": game},
            lobby=SimpleNamespace(lobby_broadcast_seeks=AsyncMock()),
        )

        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch(
                "wsl.join_seek", new=AsyncMock(return_value={"type": "new_game", "gameId": "g1"})
            ),
            patch("wsl.ws_send_json", new=AsyncMock()),
        ):
            await handle_accept_seek(
                app_state,
                object(),
                DummyUser("tester"),
                {"type": "accept_seek", "seekID": "seek1"},
            )

        bot_put.assert_awaited_once_with(game.game_start)


class RandomModeAiChallengeTestCase(unittest.IsolatedAsyncioTestCase):
    async def challenge(
        self, mode, *, worker=True, online=True, rm=False, profile="Fairy-Stockfish"
    ):
        def bot(name):
            return SimpleNamespace(
                username=name,
                bot=True,
                online=online,
                event_queue=SimpleNamespace(put=AsyncMock()),
                game_queues={},
                active_game_streams=set(),
            )

        fairy = bot("Fairy-Stockfish")
        random_mover = bot("Random-Mover")
        random_mover.online = True
        app_state = SimpleNamespace(
            users={fairy.username: fairy, random_mover.username: random_mover},
            games={"g1": SimpleNamespace(id="g1", variant="chess", game_start="game-start")},
            db=None,
        )
        join = AsyncMock(return_value={"type": "new_game", "gameId": "g1"})
        send = AsyncMock()
        with (
            patch("wsl.send_game_in_progress_if_any", new=AsyncMock(return_value=False)),
            patch("wsl.new_id", new=AsyncMock(return_value="seek1")),
            patch("wsl.ws_send_json", new=send),
            patch("wsl.join_seek", new=join),
            patch("wsl.has_available_fishnet_worker", return_value=worker),
        ):
            await handle_create_ai_challenge(
                app_state,
                object(),
                DummyUser("tester"),
                create_ai_payload(mode)
                | {
                    "rm": rm,
                    "profileid": profile,
                    "rated": True,
                    "fen": "ignored",
                    "chess960": True,
                },
            )
        return fairy, random_mover, join, send

    async def test_random_modes_use_fairy_stockfish_and_keep_the_seek_unresolved(self):
        for mode in ("wild29", "randomdice"):
            with self.subTest(mode=mode):
                fairy, _, join, _ = await self.challenge(mode)
                self.assertIs(join.await_args.args[1], fairy)
                seek = join.await_args.args[2]
                self.assertEqual(seek.variant, mode)
                self.assertEqual(seek.random_context["mode"], mode)
                self.assertEqual(seek.level, 2)
                self.assertFalse(seek.rated)
                self.assertFalse(seek.chess960)
                self.assertEqual(seek.fen, "")
                self.assertIn("g1", fairy.game_queues)
                fairy.event_queue.put.assert_awaited_once_with("game-start")

    async def test_offline_ai_is_reported_without_a_silent_random_mover_fallback(self):
        for mode in ("wild29", "randomdice"):
            for worker, online in ((False, True), (True, False)):
                with self.subTest(mode=mode, worker=worker, online=online):
                    fairy, random_mover, join, send = await self.challenge(
                        mode, worker=worker, online=online
                    )
                    join.assert_not_awaited()
                    self.assertEqual(
                        send.await_args.args[1], {"type": "error", "message": AI_OFFLINE_MESSAGE}
                    )
                    self.assertFalse(fairy.game_queues)
                    self.assertFalse(random_mover.game_queues)

    async def test_explicit_random_mover_works_without_fishnet(self):
        for mode in ("wild29", "randomdice"):
            with self.subTest(mode=mode):
                _, random_mover, join, _ = await self.challenge(mode, worker=False, rm=True)
                self.assertIs(join.await_args.args[1], random_mover)
                self.assertEqual(join.await_args.args[2].level, 0)
                random_mover.event_queue.put.assert_awaited_once_with("game-start")

    async def test_random_modes_do_not_accept_arbitrary_external_bot_profiles(self):
        _, _, join, send = await self.challenge("wild29", profile="external-bot")
        join.assert_not_awaited()
        self.assertEqual(send.await_args.args[1]["type"], "error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
