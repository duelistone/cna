# opening_pgn.py

import chess, chess.polyglot, chess.pgn
from chess_tools import *
from mmrw import *

# TODO: Change argument order, and give filename default None at the end
def create_opening_game(filename, repertoire, color, starting_node):
    findMoves = repertoire.findMovesWhite
    if color == chess.BLACK: 
        findMoves = repertoire.findMovesBlack

    # Visited nodes (to prevent too many paths to the same position)
    visited_hashes = set()

    # Make game of just line leading to starting_node
    result = chess.pgn.Game.from_board(starting_node.board())
    curr = result
    while len(curr.variations) > 0:
        curr = curr.variation(0)
        visited_hashes.add(zobrist_hash(curr.board()))

    def inner_iter(curr):
        if curr.board().can_claim_threefold_repetition():
            return # To avoid infinite loops, though should not be necessary if using visited nodes
        board = curr.board()
        for move in findMoves(board):
            curr = curr.add_variation(move)
            if zobrist_hash(curr.board()) in visited_hashes: return
            visited_hashes.add(zobrist_hash(curr.board()))
            inner_iter(curr)
            curr = curr.parent

    inner_iter(curr)

    # Set place to start and color to test
    if color == chess.WHITE:
        result.root().headers["White"] = str(starting_node.board().fullmove_number - 1)
    else:
        result.root().headers["Black"] = str(starting_node.board().fullmove_number - 1)

    # Save to file if given filename
    if filename:
        create_opening_pgn(filename, color, result.root())

    return result.root()

def create_opening_pgn(filename, color, game, start=1):
    fil = open(filename, 'w')
    exporter = chess.pgn.FileExporter(fil)
    game.accept(exporter)
    fil.close()
