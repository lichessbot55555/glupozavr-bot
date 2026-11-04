"""Test functions for matchmaking module."""
from unittest.mock import Mock
from lib.matchmaking import game_category, Matchmaking
from lib.config import Configuration
from lib.timer import Timer, seconds
from lib.lichess_types import UserProfileType


def test_game_category_standard_bullet() -> None:
    """Test bullet time control with config values."""
    # challenge_initial_time: 60 (1 min), challenge_increment: 1
    # 60 + 1*40 = 100 seconds < 179 = bullet
    assert game_category("standard", 60, 1, 0) == "bullet"

    # challenge_initial_time: 60, challenge_increment: 2
    # 60 + 2*40 = 140 seconds < 179 = bullet
    assert game_category("standard", 60, 2, 0) == "bullet"


def test_game_category_standard_blitz() -> None:
    """Test blitz time control with config values."""
    # challenge_initial_time: 180 (3 min), challenge_increment: 1
    # 180 + 1*40 = 220 seconds, 179 <= 220 < 479 = blitz
    assert game_category("standard", 180, 1, 0) == "blitz"

    # challenge_initial_time: 180, challenge_increment: 2
    # 180 + 2*40 = 260 seconds, 179 <= 260 < 479 = blitz
    assert game_category("standard", 180, 2, 0) == "blitz"


def test_game_category_standard_rapid() -> None:
    """Test rapid time control."""
    # 10 minutes + 5 seconds increment
    # 600 + 5*40 = 800 seconds, 479 <= 800 < 1499 = rapid
    assert game_category("standard", 600, 5, 0) == "rapid"

    # 15 minutes no increment
    # 900 + 0*40 = 900 seconds, 479 <= 900 < 1499 = rapid
    assert game_category("standard", 900, 0, 0) == "rapid"


def test_game_category_standard_classical() -> None:
    """Test classical time control with max config values."""
    # max_base: 1800 (30 min), max_increment: 20
    # 1800 + 20*40 = 2600 seconds >= 1499 = classical
    assert game_category("standard", 1800, 20, 0) == "classical"

    # 25 minutes no increment
    # 1500 + 0*40 = 1500 seconds >= 1499 = classical
    assert game_category("standard", 1500, 0, 0) == "classical"


def test_game_category_correspondence() -> None:
    """Test correspondence games with config values."""
    # min_days: 1
    assert game_category("standard", 0, 0, 1) == "correspondence"

    # challenge_days: 2
    assert game_category("standard", 0, 0, 2) == "correspondence"

    # max_days: 14
    assert game_category("standard", 0, 0, 14) == "correspondence"


def test_game_category_variants() -> None:
    """Test chess variants from config."""
    assert game_category("atomic", 60, 1, 0) == "atomic"
    assert game_category("chess960", 180, 2, 0) == "chess960"
    assert game_category("crazyhouse", 600, 5, 0) == "crazyhouse"
    assert game_category("horde", 60, 0, 0) == "horde"
    assert game_category("kingOfTheHill", 180, 1, 0) == "kingOfTheHill"
    assert game_category("racingKings", 600, 0, 0) == "racingKings"
    assert game_category("threeCheck", 60, 1, 0) == "threeCheck"
    assert game_category("antichess", 180, 2, 0) == "antichess"


def test_game_category_time_boundaries() -> None:
    """Test edge cases at time control boundaries."""
    # Exactly at bullet/blitz boundary
    # 179 seconds should be blitz (179 < 179 is False)
    assert game_category("standard", 179, 0, 0) == "blitz"

    # Just below boundary
    assert game_category("standard", 178, 0, 0) == "bullet"

    # Exactly at blitz/rapid boundary
    assert game_category("standard", 479, 0, 0) == "rapid"

    # Just below
    assert game_category("standard", 478, 0, 0) == "blitz"

    # Exactly at rapid/classical boundary
    assert game_category("standard", 1499, 0, 0) == "classical"

    # Just below
    assert game_category("standard", 1498, 0, 0) == "rapid"


def test_game_category_min_config_values() -> None:
    """Test minimum config values."""
    # min_base: 0, min_increment: 0
    # This is an edge case: 0 + 0*40 = 0 < 179 = bullet
    assert game_category("standard", 0, 0, 0) == "bullet"

    # min_base: 0, min_increment: 0, min_days: 1
    assert game_category("standard", 0, 0, 1) == "correspondence"


def test_game_category_correspondence_overrides_time() -> None:
    """Test that correspondence takes precedence over time controls."""
    # If both days and time controls are set, days takes precedence
    assert game_category("standard", 1800, 20, 1) == "correspondence"
    assert game_category("standard", 60, 1, 2) == "correspondence"


def test_game_category_variant_overrides_time() -> None:
    """Test that variants override time control categorization."""
    # Variants are returned regardless of time control
    # Even if time would be "classical", variant name is returned
    assert game_category("atomic", 1800, 20, 0) == "atomic"
    assert game_category("horde", 60, 1, 0) == "horde"

    # Variants override correspondence too
    assert game_category("chess960", 0, 0, 14) == "chess960"


def test_game_category_negative_values() -> None:
    """Test edge case with negative values (should not happen in practice)."""
    # Negative base time
    assert game_category("standard", -100, 5, 0) == "bullet"

    # Negative increment results in negative duration
    result = game_category("standard", 100, -10, 0)
    # 100 + (-10)*40 = -300, which is < 179, so bullet
    assert result == "bullet"


def test_game_category_realistic_scenarios() -> None:
    """Test realistic game scenarios from actual lichess games."""
    # 1+0 bullet
    assert game_category("standard", 60, 0, 0) == "bullet"

    # 2+1 bullet
    assert game_category("standard", 120, 1, 0) == "bullet"

    # 3+0 blitz
    assert game_category("standard", 180, 0, 0) == "blitz"

    # 3+2 blitz
    assert game_category("standard", 180, 2, 0) == "blitz"

    # 5+0 blitz
    assert game_category("standard", 300, 0, 0) == "blitz"

    # 5+3 blitz
    assert game_category("standard", 300, 3, 0) == "blitz"

    # 10+0 rapid
    assert game_category("standard", 600, 0, 0) == "rapid"

    # 15+5 rapid
    assert game_category("standard", 900, 5, 0) == "rapid"

    # 15+10 rapid
    assert game_category("standard", 900, 10, 0) == "rapid"

    # 30+0 classical
    assert game_category("standard", 1800, 0, 0) == "classical"

    # 30+20 classical
    assert game_category("standard", 1800, 20, 0) == "classical"


def test_get_random_config_value__returns_specific_value() -> None:
    """Test that get_random_config_value returns the config value when it's not 'random'."""
    # Create mock objects
    mock_li = Mock()
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": False,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30
        }
    })
    mock_user_profile: UserProfileType = {"username": "testbot", "perfs": {}}

    # Create matchmaking instance
    matchmaking = Matchmaking(mock_li, mock_config, mock_user_profile)

    # Create config with a specific value
    test_config = Configuration({"challenge_variant": "atomic"})

    # Test that it returns the specific value, not a random choice
    choices = ["standard", "chess960", "atomic", "horde"]
    result = matchmaking.get_random_config_value(test_config, "challenge_variant", choices)

    assert result == "atomic", f"Expected 'atomic' but got '{result}'"


def test_should_create_challenge_respects_rate_limit_when_previous_challenge_expired() -> None:
    """An expired previous challenge should not bypass the challenge rate-limit timer."""
    mock_li = Mock()
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 0
        }
    })
    mock_user_profile: UserProfileType = {"username": "testbot", "perfs": {}}
    matchmaking = Matchmaking(mock_li, mock_config, mock_user_profile)
    matchmaking.challenge_id = "challenge-id"
    matchmaking.last_challenge_created_delay.starting_time -= 100
    matchmaking.rate_limit_timer = Timer(seconds(60))

    assert matchmaking.should_create_challenge() is False


def test_unanswered_challenge_is_retried_after_configured_delay() -> None:
    """An unanswered outgoing challenge is cancelled after the configured retry delay."""
    mock_li = Mock()
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30,
            "challenge_retry_delay": 15,
        },
    })
    matchmaking = Matchmaking(mock_li, mock_config, {"username": "testbot", "perfs": {}})
    matchmaking.challenge_id = "unanswered-id"
    matchmaking.last_challenge_created_delay.starting_time -= 16

    assert matchmaking.should_create_challenge() is True
    mock_li.cancel.assert_called_once_with("unanswered-id")
    assert matchmaking.challenge_id == ""


def test_idle_delay_can_be_configured_in_seconds() -> None:
    """Matchmaking can begin shortly after startup instead of waiting whole minutes."""
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30,
            "challenge_idle_delay": 15,
        },
    })
    matchmaking = Matchmaking(Mock(), mock_config, {"username": "testbot", "perfs": {}})

    assert matchmaking.last_game_ended_delay.duration == seconds(15)


def test_no_suitable_opponent_retries_after_configured_delay() -> None:
    """An empty opponent pool should be retried on the configured cadence."""
    mock_config = Configuration({
        "challenge": {"variants": ["chess960"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "allow_during_games": False,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30,
            "challenge_retry_delay": 15,
            "challenge_idle_delay": 0,
        },
    })
    matchmaking = Matchmaking(Mock(), mock_config, {"username": "testbot", "perfs": {}})
    matchmaking.last_challenge_created_delay.starting_time -= 16
    matchmaking.choose_opponent = Mock(return_value=(None, 30, 0, 0, "chess960", "rated"))
    matchmaking.show_earliest_challenge_time = Mock()

    matchmaking.challenge(set(), [], 1)

    assert matchmaking.rate_limit_timer.duration == seconds(15)
    assert matchmaking.rate_limit_timer.is_expired() is False
    matchmaking.show_earliest_challenge_time.assert_called_once_with()


def test_completed_game_queues_and_creates_configured_rematch() -> None:
    """A completed game against a listed opponent should be recreated before random matchmaking."""
    mock_li = Mock()
    mock_li.challenge.return_value = {"id": "rematch-id"}
    mock_li.get_user_statuses.return_value = {
        "alphawolf_bot": {"id": "alphawolf_bot", "online": True, "playing": False}
    }
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "allow_during_games": False,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30,
            "rematch_opponents": ["AlphaWolf_BOT"]
        }
    })
    matchmaking = Matchmaking(mock_li, mock_config, {"username": "testbot", "perfs": {}})
    rematch = {"complete": True,
               "opponent": "alphawolf_bot",
               "base_time": 30,
               "increment": 0,
               "days": 0,
               "variant": "standard",
               "mode": "rated"}

    matchmaking.game_done({"type": "local_game_done", "rematch": rematch})
    matchmaking.last_challenge_created_delay.starting_time -= 61
    matchmaking.challenge(set(), [], 1)

    mock_li.challenge.assert_called_once_with("alphawolf_bot", {"rated": True,
                                                                 "variant": "standard",
                                                                 "clock.limit": 30,
                                                                 "clock.increment": 0})
    assert matchmaking.challenge_id == "rematch-id"
    assert matchmaking.pending_rematch is None


def test_unlisted_opponent_does_not_queue_rematch() -> None:
    """Games against other opponents should continue through normal matchmaking."""
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {"allow_matchmaking": False,
                        "block_list": [],
                        "online_block_list": [],
                        "challenge_timeout": 30,
                        "rematch_opponents": ["AlphaWolf_BOT"]}
    })
    matchmaking = Matchmaking(Mock(), mock_config, {"username": "testbot", "perfs": {}})

    matchmaking.game_done({"type": "local_game_done",
                           "rematch": {"complete": True,
                                       "opponent": "SomeOtherBot",
                                       "base_time": 30,
                                       "increment": 0,
                                       "days": 0,
                                       "variant": "standard",
                                       "mode": "rated"}})

    assert matchmaking.pending_rematch is None


def test_get_random_config_value__returns_from_choices_when_random() -> None:
    """Test that get_random_config_value returns a value from choices when config value is 'random'."""
    # Create mock objects
    mock_li = Mock()
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": False,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30
        }
    })
    mock_user_profile: UserProfileType = {"username": "testbot", "perfs": {}}

    # Create matchmaking instance
    matchmaking = Matchmaking(mock_li, mock_config, mock_user_profile)

    # Create config with "random" value
    test_config = Configuration({"challenge_mode": "random"})

    # Test that it returns one of the choices
    choices = ["casual", "rated"]
    result = matchmaking.get_random_config_value(test_config, "challenge_mode", choices)

    assert result in choices, f"Expected result to be in {choices} but got '{result}'"


def test_choose_opponent_only_chooses_online_idle_bot() -> None:
    """Busy and offline bots must not receive matchmaking challenges."""
    mock_li = Mock()
    mock_li.get_online_bots.return_value = [
        {"id": "busybot", "username": "BusyBot", "perfs": {"bullet": {"games": 5, "rating": 2000}}},
        {"id": "offlinebot", "username": "OfflineBot", "perfs": {"bullet": {"games": 5, "rating": 2000}}},
        {"id": "idlebot", "username": "IdleBot", "perfs": {"bullet": {"games": 5, "rating": 2000}}},
    ]
    mock_li.get_user_statuses.return_value = {
        "busybot": {"id": "busybot", "online": True, "playing": True},
        "offlinebot": {"id": "offlinebot", "online": False, "playing": False},
        "idlebot": {"id": "idlebot", "online": True, "playing": False},
    }
    mock_li.get_public_data.return_value = {"blocking": False}
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 0,
            "challenge_variant": "standard",
            "challenge_mode": "rated",
            "challenge_initial_time": [30],
            "challenge_increment": [0],
            "challenge_days": [None],
            "opponent_min_rating": 1000,
            "opponent_max_rating": 3000,
            "opponent_rating_difference": None,
            "rating_preference": "none",
            "overrides": {},
        },
    })
    matchmaking = Matchmaking(mock_li, mock_config,
                              {"username": "TestBot", "perfs": {"bullet": {"rating": 2000}}})

    opponent, *_ = matchmaking.choose_opponent()

    assert opponent == "IdleBot"


def test_busy_rematch_opponent_is_not_challenged() -> None:
    """Keep a rematch queued while the configured opponent is playing."""
    mock_li = Mock()
    mock_li.get_user_statuses.return_value = {
        "alphawolf_bot": {"id": "alphawolf_bot", "online": True, "playing": True}
    }
    mock_config = Configuration({
        "challenge": {"variants": ["standard"]},
        "matchmaking": {
            "allow_matchmaking": True,
            "allow_during_games": False,
            "block_list": [],
            "online_block_list": [],
            "challenge_timeout": 30,
            "rematch_opponents": ["AlphaWolf_BOT"],
        },
    })
    matchmaking = Matchmaking(mock_li, mock_config, {"username": "testbot", "perfs": {}})
    matchmaking.pending_rematch = {"complete": True, "opponent": "AlphaWolf_BOT", "base_time": 30,
                                   "increment": 0, "days": 0, "variant": "standard", "mode": "rated"}
    matchmaking.last_challenge_created_delay.starting_time -= 61

    matchmaking.challenge(set(), [], 1)

    mock_li.challenge.assert_not_called()
    assert matchmaking.pending_rematch is not None
