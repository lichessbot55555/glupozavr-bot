"""Tests for the permanent mistake book."""
import json
import shutil
import tempfile
from pathlib import Path

import chess
import pytest

from lib.mistake_book import MistakeBook, position_key


@pytest.fixture()
def tmp_path():
    """A writable directory inside the workspace; the system temp dir is sandboxed."""
    path = tempfile.mkdtemp(prefix="mistakes_", dir=".")
    yield Path(path)
    shutil.rmtree(path, ignore_errors=True)


def test_records_and_replaces_a_mistake(tmp_path: Path) -> None:
    """A recorded bad move is replaced by the remembered good one."""
    book = MistakeBook(str(tmp_path / "mistakes.json"))
    board = chess.Board()
    bad, good = chess.Move.from_uci("f2f3"), chess.Move.from_uci("e2e4")

    assert book.record(board, bad, good, 320)
    assert book.replacement(board, bad) == good
    assert book.replacement(board, good) is None
    assert book.replacement(board, chess.Move.from_uci("d2d4")) is None


def test_book_survives_a_restart(tmp_path: Path) -> None:
    """The book is written to disk and read back."""
    path = str(tmp_path / "mistakes.json")
    board = chess.Board()
    bad, good = chess.Move.from_uci("f2f3"), chess.Move.from_uci("e2e4")
    book = MistakeBook(path)
    book.record(board, bad, good, 250)
    book.save()

    reloaded = MistakeBook(path)
    assert len(reloaded) == 1
    assert reloaded.replacement(board, bad) == good


def test_missing_file_is_not_an_error(tmp_path: Path) -> None:
    """A bot without a book simply starts empty."""
    book = MistakeBook(str(tmp_path / "nope.json"))
    assert len(book) == 0
    assert book.replacement(chess.Board(), chess.Move.from_uci("e2e4")) is None


def test_illegal_remembered_move_is_ignored(tmp_path: Path) -> None:
    """A stale entry never produces an illegal move."""
    path = str(tmp_path / "mistakes.json")
    board = chess.Board()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "positions": {
            position_key(board): {"bad": {"f2f3": 300}, "good": "e7e5", "seen": 1}}}, f)
    book = MistakeBook(path)
    assert book.replacement(board, chess.Move.from_uci("f2f3")) is None


def test_repeated_blunder_keeps_the_worst_loss(tmp_path: Path) -> None:
    """Recording the same mistake twice keeps the bigger loss."""
    path = str(tmp_path / "mistakes.json")
    board = chess.Board()
    bad, good = chess.Move.from_uci("f2f3"), chess.Move.from_uci("e2e4")
    book = MistakeBook(path)
    book.record(board, bad, good, 120)
    book.record(board, bad, good, 400)
    book.save()
    entry = json.load(open(path, encoding="utf-8"))["positions"][position_key(board)]
    assert entry["bad"]["f2f3"] == 400
    assert entry["seen"] == 2


def test_book_is_disabled_by_config() -> None:
    """The feature is off unless the config enables it."""
    from lib.config import Configuration
    from lib.engine_wrapper import get_mistake_book
    assert get_mistake_book(Configuration({"mistakes": {"enabled": False}})) is None