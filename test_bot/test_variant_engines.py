"""Tests for per-variant engine selection."""
from types import SimpleNamespace

from lib.config import Configuration
from lib.engine_wrapper import engine_binary_name


def engine_config(**engine: object) -> Configuration:
    """Return a bot config whose engine section is given by the keyword arguments."""
    section = {"dir": "./engines/", "name": "fairy-stockfish", "protocol": "uci"}
    section.update(engine)
    return Configuration({"engine": section})


def pick(variant: str) -> str:
    """Return the binary that the bot would start for this variant."""
    config = engine_config(standard_chess_name="stockfish",
                           variant_engines={"atomic": "atomic-stockfish",
                                            "horde": "horde-stockfish"})
    return engine_binary_name(config, SimpleNamespace(variant_name=variant))


def test_atomic_uses_its_own_engine() -> None:
    """Atomic gets the specialized engine."""
    assert pick("Atomic") == "atomic-stockfish"


def test_standard_and_chess960_use_stockfish() -> None:
    """Standard chess and Chess960 keep the strong Stockfish build."""
    assert pick("Standard") == "stockfish"
    assert pick("Chess960") == "stockfish"
    assert pick("From Position") == "stockfish"


def test_horde_uses_its_own_engine() -> None:
    """Horde gets the specialized engine as well."""
    assert pick("Horde") == "horde-stockfish"


def test_other_variants_fall_back_to_fairy() -> None:
    """Variants without an override keep Fairy-Stockfish."""
    assert pick("Crazyhouse") == "fairy-stockfish"
    assert pick("King of the Hill") == "fairy-stockfish"


def test_without_variant_engines_everything_uses_the_configured_engine() -> None:
    """A config without overrides behaves exactly as before."""
    config = engine_config()
    for variant in ("Standard", "Atomic", "Crazyhouse"):
        assert engine_binary_name(config, SimpleNamespace(variant_name=variant)) == "fairy-stockfish"
