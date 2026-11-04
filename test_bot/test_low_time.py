"""Tests for the low time mode that overrides the engine clock."""
import chess
from types import SimpleNamespace

from lib.config import Configuration
from lib.engine_wrapper import game_clock_time, low_time_limit
from lib.timer import Timer, msec


def low_time_config() -> Configuration:
    """Return an engine config with low time mode enabled."""
    return Configuration({"low_time_threshold": 6000,
                          "low_time_horizon": 30,
                          "low_time_min": 40,
                          "low_time_max": 300})


def blitz_game(clock_ms: int) -> SimpleNamespace:
    """Return the game fields used by the clock manager."""
    return SimpleNamespace(variant_name="Standard",
                           speed="blitz",
                           clock_initial=msec(180000),
                           clock_increment=msec(2000),
                           state={"wtime": clock_ms, "btime": clock_ms, "winc": 2000, "binc": 2000},
                           id="test-game")


def test_low_time_is_off_above_the_threshold() -> None:
    """Nothing is overridden while the clock is comfortable."""
    assert low_time_limit(msec(10000), low_time_config()) is None
    assert low_time_limit(msec(6000), low_time_config()) is not None


def test_low_time_scales_down_with_the_clock() -> None:
    """The search time shrinks as the clock shrinks."""
    config = low_time_config()
    times = [low_time_limit(msec(clock), config).time for clock in (6000, 3000, 1500)]
    assert times[0] > times[1] > times[2]
    assert times[0] == 0.2
    assert times[2] == 0.05


def test_low_time_respects_floor_and_ceiling() -> None:
    """The floor and the ceiling bound the search time."""
    config = low_time_config()
    assert low_time_limit(msec(500), config).time == 0.04
    tight = Configuration({"low_time_threshold": 6000, "low_time_horizon": 2,
                           "low_time_min": 40, "low_time_max": 300})
    assert low_time_limit(msec(5000), tight).time == 0.3


def test_low_time_never_spends_the_clock() -> None:
    """The limit never eats the last milliseconds of the clock."""
    config = low_time_config()
    for clock in (6000, 2000, 500, 200, 100):
        limit = low_time_limit(msec(clock), config)
        assert limit.time >= 0.015
        assert limit.time <= max(0.015, (msec(clock) - msec(60)).total_seconds())


def test_game_clock_time_switches_to_low_time() -> None:
    """A real-time game below the threshold is played with the low time limit."""
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("e7e5")

    comfortable = game_clock_time(board, blitz_game(60000), Timer(), msec(200), low_time_config())
    assert comfortable.clock_id == "real time"

    low = game_clock_time(board, blitz_game(5000), Timer(), msec(200), low_time_config())
    assert low.clock_id == "low time"
    assert low.time == 0.16
