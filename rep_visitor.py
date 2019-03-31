# rep_visitor.py

import global_variables as G
import datetime
import mmrw
import chess, chess.polyglot, time
from chess_tools import board_moves

'''Module to visit repertoire nodes that are children of given board.'''

def rep_visitor(board, player=None, only_sr=False, return_entry=False):
    '''Visits repertoire nodes that are children of given board in dfs.
    Returns board/move pairs for player.'''
    visited_hashes = set()
    def rep_visitor(board, player=None, only_sr=False, return_entry=False):
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
                if (board.turn == player or player == None) and \
                    (only_sr == False or \
                    (entry.learn > 0 and \
                    (return_entry == True or entry.learn <= int(time.time() / 60)))):
                    if not return_entry:
                        yield board.copy(), entry.move()
                    else:
                        yield board.copy(), entry.move(), entry
                board.push(entry.move())
                yield from rep_visitor(board.copy(), player, only_sr, return_entry)
                board.pop()
    return rep_visitor(board, player, only_sr, return_entry)

def get_learning_schedule(board, player, max_lines=100):
    visitor = rep_visitor(board, player, only_sr=True, return_entry=True)
    entries = []
    boards = []
    for b, m, entry in visitor:
        entries.append(entry)
        boards.append(b)
    sorted_entries_and_boards = sorted(zip(entries, boards), key=lambda x:x[0].learn)
    counter = 0
    for entry, b in sorted_entries_and_boards:
        counter += 1
        if counter > max_lines:
            break
        delta = datetime.timedelta(seconds=entry.learn * 60 - int(time.time()))
        print(delta, end=" ")
        print("|", end=" ")
        print(datetime.datetime.fromtimestamp(entry.learn * 60).strftime('%Y-%m-%d %H:%M'), end=" ")
        print("|", end=" ")
        line = board_moves(b)
        print(line if len(line) > 0 else "(root)")
    return sorted_entries_and_boards
