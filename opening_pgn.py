# opening_pgn.py

import chess, chess.polyglot, chess.pgn
from chess_tools import *
from mmrw import *

def create_opening_game(filename, repertoire, color, starting_node):
    findMove = repertoire.findMoveWhite
    findMoves = repertoire.findMovesWhite
    if color == chess.BLACK: 
        findMove = repertoire.findMoveBlack
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
        turn = board.turn
        if turn == color:
            move = findMove(board)
            if move == None: return
            curr = curr.add_main_variation(move)
            if zobrist_hash(curr.board()) in visited_hashes: return
            visited_hashes.add(zobrist_hash(curr.board()))
            inner_iter(curr)
        else:
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

    create_opening_pgn(filename, color, result.root())
    return result.root()

def create_opening_pgn(filename, color, game, start=1):
    fil = open(filename, 'w')
    exporter = chess.pgn.FileExporter(fil)
    game.accept(exporter)
    fil.close()
