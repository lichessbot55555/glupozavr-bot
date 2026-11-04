from types import SimpleNamespace

from lib.config import Configuration, activate_account_blitz
from lib.engine_wrapper import is_account_blitz


def make_config() -> Configuration:
    return Configuration({
        "account_blitz": {
            "enabled": True,
            "username": "GlupoZavr",
            "max_base": 600,
            "initial_time": 180,
            "increment": 2,
            "ponder": True,
            "uci_options": {},
        },
        "challenge": {"time_controls": ["bullet"], "max_base": 30},
        "matchmaking": {"overrides": {}},
    })


def test_account_blitz_is_not_activated_for_another_account() -> None:
    config = make_config()

    assert not activate_account_blitz(config, "AnotherBot")
    assert config.challenge.time_controls == ["bullet"]
    assert config.challenge.max_base == 30
    assert config.matchmaking.overrides.config == {}


def test_account_blitz_adds_blitz_without_removing_bullet() -> None:
    config = make_config()

    assert activate_account_blitz(config, "glupozavr")
    assert config.challenge.time_controls == ["bullet", "blitz"]
    assert config.challenge.max_base == 600
    assert config.matchmaking.overrides.account_blitz.challenge_initial_time == [180]
    assert config.matchmaking.overrides.account_blitz.challenge_increment == [2]
    assert config.matchmaking.overrides.account_blitz.challenge_days == [None]


def test_account_blitz_game_requires_both_username_and_speed() -> None:
    config = make_config()

    assert is_account_blitz(config, SimpleNamespace(username="GlupoZavr", speed="blitz"))
    assert not is_account_blitz(config, SimpleNamespace(username="OtherBot", speed="blitz"))
    assert not is_account_blitz(config, SimpleNamespace(username="GlupoZavr", speed="bullet"))
