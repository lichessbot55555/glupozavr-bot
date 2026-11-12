"""Build a polyglot opening book for a variant from an engine's own lines.

The engine is driven through a command pipe, because this sandbox cannot create the
anonymous pipes that asyncio needs.
"""
from __future__ import annotations
import argparse, os, re, struct, subprocess
import chess, chess.polyglot, chess.variant

VARIANTS = {
    "atomic": chess.variant.AtomicBoard,
    "horde": chess.variant.HordeBoard,
    "crazyhouse": chess.variant.CrazyhouseBoard,
    "kingofthehill": chess.variant.KingOfTheHillBoard,
    "threecheck": chess.variant.ThreeCheckBoard,
    "antichess": chess.variant.AntichessBoard,
    "racingkings": chess.variant.RacingKingsBoard,
}


def run_engine(engine_path, positions, movetime):
    """Search every position with MultiPV and return the raw output blocks."""
    cmds = os.path.abspath("tmp_book_cmds.txt")
    out = os.path.abspath("tmp_book_out.txt")
    lines = ["uci", "setoption name Threads value 4", "setoption name Hash value 512",
             "setoption name MultiPV value 6", "isready"]
    for fen in positions:
        lines += [f"position fen {fen}", f"go movetime {movetime}"]
    with open(cmds, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")
    # The pipe must stay open until the last search finishes, otherwise the engine
    # treats end-of-input as quit and answers instantly at depth 1.
    wait_s = max(6, int(len(positions) * (movetime / 1000 + 0.6)) + 4)
    subprocess.run(f'cmd /c "(type "{cmds}" & ping -n {wait_s} 127.0.0.1 >nul) | '
                   f'"{engine_path}" > "{out}" 2>&1"', shell=True, timeout=wait_s + 120)
    text = open(out, encoding="utf-8", errors="replace").read()
    os.remove(cmds); os.remove(out)
    blocks, current = [], []
    for line in text.splitlines():
        current.append(line)
        if line.startswith("bestmove"):
            blocks.append(current); current = []
    return blocks


def parse_block(block):
    """Return [(uci, score)] for one position, best first."""
    moves = {}
    for line in block:
        m = re.match(r"info .*? multipv (\d+) .*?score (cp|mate) (-?\d+).*? pv (\S+)", line)
        if m:
            moves[int(m.group(1))] = (m.group(4), int(m.group(3)) * (1 if m.group(2) == "cp" else 100000))
    return [moves[k] for k in sorted(moves)]


def build(variant, engine_path, plies, width, movetime, margin):
    board_class = VARIANTS[variant]
    entries, frontier = {}, [board_class()]
    for ply in range(plies):
        blocks = run_engine(engine_path, [b.fen() for b in frontier], movetime)
        next_frontier = []
        for board, block in zip(frontier, blocks):
            cand = [(u, s) for u, s in parse_block(block) if u]
            if not cand:
                continue
            best = cand[0][1]
            for uci, score in cand:
                if best - score > margin:
                    continue
                try:
                    move = chess.Move.from_uci(uci)
                except ValueError:
                    continue
                if move not in board.legal_moves:
                    continue
                key = (chess.polyglot.zobrist_hash(board), uci)
                entries[key] = max(entries.get(key, 0.0), max(1.0, margin - (best - score)))
                child = board.copy(stack=False)
                child.push(move)
                if not child.is_game_over():
                    next_frontier.append(child)
        frontier = next_frontier[:width]
        print(f"  ply {ply + 1}: {len(entries)} entries, frontier {len(frontier)}", flush=True)
        if not frontier:
            break
    return entries


def write_book(entries, path):
    rows = []
    for (key, uci), weight in entries.items():
        move = chess.Move.from_uci(uci)
        rows.append((key, move, int(max(1, min(65535, round(weight * 100))))))
    rows.sort(key=lambda r: (r[0], r[1].uci()))
    with open(path, "wb") as f:
        for key, move, weight in rows:
            packed = (move.from_square << 6) | move.to_square
            f.write(struct.pack(">QHHI", key, packed, weight, 0))
    print(f"wrote {len(rows)} entries to {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    ap.add_argument("--engine", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plies", type=int, default=8)
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--movetime", type=int, default=400)
    ap.add_argument("--margin", type=int, default=80)
    a = ap.parse_args()
    write_book(build(a.variant, os.path.abspath(a.engine), a.plies, a.width, a.movetime, a.margin), a.out)