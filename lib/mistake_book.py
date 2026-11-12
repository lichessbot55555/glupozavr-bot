"""A permanent record of positions where the bot blundered.

The engine has no memory: it will happily play the same losing move in the same position
forever. This module keeps a small JSON file keyed by the exact position, remembers which
move lost and which move was better, and lets the bot skip the mistake next time.
"""
from __future__ import annotations
import json
import logging
import os
import threading
import chess
import chess.polyglot

logger = logging.getLogger(__name__)

VERSION = 1


def position_key(board: chess.Board) -> str:
    """Return a stable key for a position, independent of move counters."""
    return f"{chess.polyglot.zobrist_hash(board):016x}"


class MistakeBook:
    """Positions where a specific move must never be played again."""

    def __init__(self, path: str | None) -> None:
        """:param path: The JSON file that stores the mistakes."""
        self.path = path
        self.positions: dict[str, dict] = {}
        self._lock = threading.Lock()
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.positions = data.get("positions", {})
                logger.info(f"Loaded {len(self.positions)} remembered mistakes from {path}")
            except (OSError, ValueError) as error:
                logger.warning(f"Could not read the mistake book {path}: {error}")

    def replacement(self, board: chess.Board, move: chess.Move) -> chess.Move | None:
        """
        Return the better move if `move` is a remembered mistake, else None.

        :param board: The position before the move.
        :param move: The move the engine or the book wants to play.
        :return: A replacement move, or None to keep the original one.
        """
        entry = self.positions.get(position_key(board))
        if not entry:
            return None
        if move.uci() not in entry.get("bad", {}):
            return None
        good = entry.get("good")
        if not good:
            return None
        try:
            replacement = chess.Move.from_uci(good)
        except ValueError:
            return None
        if replacement not in board.legal_moves:
            logger.warning(f"Remembered good move {good} is illegal here, ignoring it")
            return None
        return replacement

    def record(self, board: chess.Board, bad_move: chess.Move, good_move: chess.Move,
               loss_cp: int) -> bool:
        """
        Remember that `bad_move` loses `loss_cp` centipawns compared to `good_move`.

        :return: True when this is a new or worsened mistake.
        """
        if bad_move == good_move:
            return False
        key = position_key(board)
        with self._lock:
            entry = self.positions.setdefault(key, {"bad": {}, "good": good_move.uci(), "seen": 0})
            previous = entry["bad"].get(bad_move.uci(), 0)
            entry["bad"][bad_move.uci()] = max(previous, loss_cp)
            entry["good"] = good_move.uci()
            entry["seen"] = entry.get("seen", 0) + 1
        return True

    def save(self) -> None:
        """Write the book back to disk, atomically."""
        if not self.path:
            return
        with self._lock:
            payload = {"version": VERSION, "positions": self.positions}
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=0, sort_keys=True)
            f.write("\n")
        os.replace(tmp, self.path)
        logger.info(f"Saved {len(self.positions)} remembered mistakes to {self.path}")

    def __len__(self) -> int:
        return len(self.positions)