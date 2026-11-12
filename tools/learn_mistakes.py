"""Find the bot's blunders in its own games and remember them in the mistake book.

Run after a session: every position where the bot gave away more than `--threshold`
centipawns compared to the engine's best move is stored, together with the move it should
have played. The live bot then skips those exact moves.
"""
from __future__ import annotations
import argparse, io, os, re, sys
import chess, chess.engine, chess.pgn, chess.variant
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.mistake_book import MistakeBook  # noqa: E402


def board_class_for(variant_name: str):
    """Return the python-chess board class for a lichess variant name."""
    if variant_name in ("Standard", "From Position"):
        return chess.Board
    return chess.variant.find_variant(variant_name)


def engine_for(config: dict, variant_name: str) -> str:
    """Return the engine binary this variant uses."""
    engine_cfg = config["engine"]
    key = variant_name.casefold().replace(" ", "")
    overrides = engine_cfg.get("variant_engines") or {}
    for name, binary in overrides.items():
        if name.casefold().replace(" ", "") == key:
            return os.path.join(engine_cfg["dir"], binary)
    if variant_name in ("Standard", "From Position", "Chess960"):
        return os.path.join(engine_cfg["dir"], engine_cfg.get("standard_chess_name") or engine_cfg["name"])
    return os.path.join(engine_cfg["dir"], engine_cfg["name"])


def evaluate(engine, board, played, depth: int, width: int):
    """Return (best_move, best_score, played_score) for one position."""
    infos = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=width)
    best_score, best_move, played_score = None, None, None
    for info in infos:
        pv = info.get("pv")
        if not pv:
            continue
        score = info["score"].pov(board.turn).score(mate_score=100000)
        if score is None:
            continue
        if best_score is None:
            best_score, best_move = score, pv[0]
        if pv[0] == played:
            played_score = score
    if best_score is None:
        return None, None, None
    if played_score is None:
        # The played move is not among the top lines: score it on its own.
        info = engine.analyse(board, chess.engine.Limit(depth=depth), root_moves=[played])
        if not info or "score" not in info:
            return None, None, None
        played_score = info["score"].pov(board.turn).score(mate_score=100000)
    return best_move, best_score, played_score


def learn(pgn_path: str, book_path: str, config_path: str, username: str,
          depth: int, threshold: int, width: int, max_games: int) -> None:
    """Analyse the games and write the mistakes into the book."""
    config = yaml.safe_load(open(config_path, encoding="utf-8"))
    book = MistakeBook(book_path)
    before = len(book)
    if not os.path.isfile(pgn_path):
        print(f"No PGN at {pgn_path}, nothing to learn.")
        return

    text = open(pgn_path, encoding="utf-8", errors="replace").read()
    blocks = re.split(r"\n\s*\n(?=\[Event )", text)
    engines = {}
    games = 0
    for block in blocks[-max_games:]:
        game = chess.pgn.read_game(io.StringIO(block))
        if game is None:
            continue
        variant_name = game.headers.get("Variant", "Standard")
        white = game.headers.get("White", "")
        black = game.headers.get("Black", "")
        if username not in (white, black):
            continue
        bot_is_white = white == username
        board_class = board_class_for(variant_name)
        path = engine_for(config, variant_name)
        if not os.path.isfile(path):
            print(f"  skipping {variant_name}: no engine at {path}")
            continue
        if path not in engines:
            engine = chess.engine.SimpleEngine.popen_uci(path)
            engine.configure({"Threads": 2, "Hash": 256})
            engines[path] = engine
        engine = engines[path]

        board = board_class()
        try:
            for move in game.mainline_moves():
                if board.turn == bot_is_white:
                    best, best_score, played_score = evaluate(engine, board, move, depth, width)
                    if best is not None and played_score is not None and best != move:
                        loss = best_score - played_score
                        if loss >= threshold:
                            book.record(board, move, best, loss)
                            print(f"  blunder {move.uci()} -> {best.uci()} (-{loss} cp) in {game.headers.get('Site')}")
                board.push(move)
        except (ValueError, AssertionError) as error:
            print(f"  skipping a game: {error}")
            continue
        games += 1

    for engine in engines.values():
        engine.close()
    book.save()
    print(f"analysed {games} games, mistakes {before} -> {len(book)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pgn", required=True)
    ap.add_argument("--book", default="mistakes.json")
    ap.add_argument("--config", default="config.github.yml")
    ap.add_argument("--username", required=True)
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--threshold", type=int, default=150)
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--max-games", type=int, default=40)
    a = ap.parse_args()
    learn(a.pgn, a.book, a.config, a.username, a.depth, a.threshold, a.width, a.max_games)