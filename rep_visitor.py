# rep_visitor.py

import global_variables as G
import mmrw
import chess, chess.polyglot

'''Module to visit repertoire nodes that are children of given board.'''

visited_hashes = set()

def rep_visitor(board, player=None):
    '''Visits repertoire nodes that are children of given board in dfs.
    Returns board/move pairs for player.'''
    # In case of originally given node being repeated later on in search tree
    # For other nodes, this is redundant due to loop below
    hashValue = chess.polyglot.zobrist_hash(board)
    visited_hashes.add(hashValue)
    subrep = G.rep.ww
    if player == chess.WHITE and board.turn == chess.BLACK:
        subrep = G.rep.wb
    elif player == chess.BLACK and board.turn == chess.WHITE:
        subrep = G.rep.bw
    elif player == chess.BLACK and board.turn == chess.BLACK:
        subrep = G.rep.bb
    for entry in subrep.find_all(board):
        child_board = board.copy()
        child_board.push(entry.move())
        child_hash = chess.polyglot.zobrist_hash(child_board)
        if child_hash not in visited_hashes:
            if (board.turn == player or player == None):
                yield board, entry.move()
            board.push(entry.move())
            yield from rep_visitor(board, player)
            board.pop()

