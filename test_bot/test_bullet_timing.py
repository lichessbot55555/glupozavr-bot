"""Tests for the dedicated 30+0 Stockfish time controls."""
import chess
from types import SimpleNamespace

from lib.config import Configuration
from lib.engine_wrapper import (bullet_clock_time, first_move_time, game_clock_time, move_time, uses_bullet_clock)
from lib.timer import Timer, msec, seconds


def bullet_game() -> SimpleNamespace:
    """Return the game fields used by the time manager."""
    return SimpleNamespace(variant_name="Standard",
                           speed="bullet",
                           clock_initial=msec(30000),
                           clock_increment=msec(0),
                           state={"wtime": 30000, "btime": 30000, "winc": 0, "binc": 0},
                           id="test-game")


def adaptive_config() -> Configuration:
    """Return the engine config used by the adaptive bullet clock."""
    return Configuration({"bullet_adaptive": True,
                          "bullet_horizon": 64,
                          "bullet_move_time": 50,
                          "bullet_max_move_time": 900,
                          "bullet_time_reserve": 2000,
                          "bullet_move_overhead": 100})


def test_30_second_bullet_caps_search_time() -> None:
    """A fixed bullet time is used when the adaptive clock is off."""
    game = bullet_game()
    board = chess.Board()
    board.push_uci("e2e4")
    config = Configuration({"bullet_move_time": 250, "bullet_time_reserve": 2000})

    limit = game_clock_time(board, game, Timer(), msec(200), config)

    assert limit.time == 0.25


def test_30_second_bullet_protects_clock_reserve() -> None:
    """The reserve is never spent by the fixed rule."""
    game = bullet_game()
    game.state["btime"] = 2100
    board = chess.Board()
    board.push_uci("e2e4")
    config = Configuration({"bullet_move_time": 250, "bullet_time_reserve": 2000})

    assert game_clock_time(board, game, Timer(), msec(200), config).time == 0.025
    assert first_move_time(game, config).time == 0.25


def test_adaptive_bullet_applies_to_every_bullet_game() -> None:
    """Every bullet game uses the adaptive allocator, including the variant arenas."""
    config = adaptive_config()
    game = bullet_game()
    assert uses_bullet_clock(game, config)

    game.variant_name = "Atomic"
    assert uses_bullet_clock(game, config)

    game.variant_name = "Standard"
    game.speed = "blitz"
    assert not uses_bullet_clock(game, config)

    game.speed = "bullet"
    assert not uses_bullet_clock(game, Configuration({"bullet_move_time": 150}))


def test_variant_bullet_uses_the_shorter_horizon() -> None:
    """Variants end much faster, so they spend a bigger share of the clock per move."""
    config = Configuration({"bullet_adaptive": True,
                            "bullet_horizon": 64,
                            "bullet_variant_horizon": 32,
                            "bullet_move_time": 50,
                            "bullet_max_move_time": 900,
                            "bullet_time_reserve": 2000,
                            "bullet_move_overhead": 100})
    board = chess.Board()
    board.push_uci("e2e4")

    standard = bullet_clock_time(board, bullet_game(), Timer(), msec(200), config)
    atomic_game = bullet_game()
    atomic_game.variant_name = "Atomic"
    atomic = bullet_clock_time(board, atomic_game, Timer(), msec(200), config)

    assert atomic.time > standard.time * 1.8
    assert atomic.time <= 0.9


def test_adaptive_bullet_spends_more_time_than_the_fixed_rule() -> None:
    """The adaptive clock searches longer than the old fixed rule."""
    game = bullet_game()
    board = chess.Board()
    board.push_uci("e2e4")

    fixed = game_clock_time(board, game, Timer(), msec(200), Configuration({"bullet_move_time": 150,
                                                                           "bullet_time_reserve": 2000}))
    adaptive = bullet_clock_time(board, game, Timer(), msec(200), adaptive_config())

    assert fixed.time == 0.15
    assert adaptive.time > fixed.time * 2
    assert adaptive.time <= 0.9


def test_adaptive_bullet_never_spends_the_clock_down() -> None:
    """The allocator never spends the clock below the guard."""
    config = adaptive_config()
    board = chess.Board()
    board.push_uci("e2e4")

    for clock in (30000, 15000, 8000, 4000, 2000, 1000, 500, 300):
        game = bullet_game()
        game.state["wtime"] = clock
        game.state["btime"] = clock
        limit = bullet_clock_time(board, game, Timer(), msec(200), config)
        remaining = seconds(clock) - msec(200)
        assert limit.time >= 0.015
        assert limit.time <= max(0.015, (remaining - msec(120)).total_seconds())


def test_move_time_routes_bullet_games_to_the_adaptive_clock() -> None:
    """move_time routes bullet games to the adaptive allocator."""
    game = bullet_game()
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("e7e5")

    limit, can_ponder = move_time(board, game, True, Timer(), msec(200), False, seconds(0), adaptive_config())

    assert limit.clock_id == "bullet"
    assert can_ponder

    first_move_limit, first_move_can_ponder = move_time(chess.Board(), game, True, Timer(), msec(200), False,
                                                        seconds(0), adaptive_config())
    assert first_move_limit.clock_id == "bullet"
    assert not first_move_can_ponder
