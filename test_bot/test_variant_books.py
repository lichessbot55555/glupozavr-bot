"""Tests for the generated variant opening books."""
import chess
import chess.polyglot
import chess.variant


def first_moves(path: str, board_class: type[chess.Board]) -> list[tuple[str, int]]:
    """Return the book's root moves as (san, weight) pairs."""
    reader = chess.polyglot.open_reader(path)
    board = board_class()
    moves = [(board.san(entry.move), entry.weight) for entry in reader.find_all(board)]
    reader.close()
    return moves


def test_atomic_book_has_legal_opening_moves() -> None:
    """The atomic book answers the starting position."""
    moves = first_moves("engines/atomic.bin", chess.variant.AtomicBoard)
    assert moves, "atomic book has no entry for the start position"
    board = chess.variant.AtomicBoard()
    for san, weight in moves:
        assert weight > 0
        assert san


def test_horde_book_has_legal_opening_moves() -> None:
    """The horde book answers the starting position."""
    moves = first_moves("engines/horde.bin", chess.variant.HordeBoard)
    assert moves, "horde book has no entry for the start position"


def test_books_only_contain_legal_moves() -> None:
    """Every entry of both books is legal in its own position."""
    for path, board_class in (("engines/atomic.bin", chess.variant.AtomicBoard),
                              ("engines/horde.bin", chess.variant.HordeBoard)):
        reader = chess.polyglot.open_reader(path)
        start = board_class()
        by_key: dict[int, list[chess.Move]] = {}
        for entry in reader:
            by_key.setdefault(entry.key, []).append(entry.move)
        reader.close()
        # Walk every reachable position and check the stored moves against it.
        seen, stack = set(), [start]
        checked = 0
        while stack:
            board = stack.pop()
            key = chess.polyglot.zobrist_hash(board)
            if key in seen:
                continue
            seen.add(key)
            for move in by_key.get(key, []):
                assert move in board.legal_moves, f"{path}: illegal {move.uci()} in {board.fen()}"
                checked += 1
                child = board.copy(stack=False)
                child.push(move)
                stack.append(child)
        assert checked > 0
