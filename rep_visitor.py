# rep_visitor.py

import global_variables as G
import datetime, random
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
            child_board.push(entry.move)
            child_hash = chess.polyglot.zobrist_hash(child_board)
            if child_hash not in visited_hashes:
                if (board.turn == player or player == None) and \
                    (only_sr == False or \
                    (entry.learn > 0 and \
                    (return_entry == True or entry.learn <= int(time.time() / 60)))):
                    if not return_entry:
                        yield board.copy(), entry.move
                    else:
                        yield board.copy(), entry.move, entry
                board.push(entry.move)
                yield from rep_visitor(board.copy(), player, only_sr, return_entry)
                board.pop()
    return rep_visitor(board, player, only_sr, return_entry)

def quickselect_partition(f, l, left, right, pivotIndex):
    '''Helper function for quickselect based on Wikipedia's algorithm.'''
    pivotValue = l[pivotIndex]
    l[pivotIndex], l[right] = l[right], l[pivotIndex]
    storeIndex = left
    for i in range(left, right):
        if f(l[i]) < f(pivotValue):
            l[storeIndex], l[i] = l[i], l[storeIndex]
            storeIndex += 1
    l[right], l[storeIndex] = l[storeIndex], l[right]
    return storeIndex

def quickselect(f, k, l, left=0, right=-1):
    '''Quickselect function based on Wikipedia's algorithm.

    We actually don't care about the return value, as we just want the algorithm
    to rearrange the list so that the kth element is in the correct spot,
    with the elements to the less being less and the elements to the right being more.'''
    if right == -1:
        right = len(l) - 1 # Quick hack since default argument can't depend on l
    if left == right:
        return
    pivotIndex = random.randint(left, right)
    pivotIndex = quickselect_partition(f, l, left, right, pivotIndex)
    if k == pivotIndex:
        return
    elif k < pivotIndex:
        return quickselect(f, k, l, left, pivotIndex - 1)
    return quickselect(f, k, l, pivotIndex + 1, right)

def clear_orphaned_learn_values(player, only_print=True):
    # WARNING: This function assumes that the repertoire is not modified
    # while the function is running, but it does not implement a lock mechanism.
    # Use with caution.
    # Partially for these reasons, this is not currently tied to a callback,
    # and can only be used manually.
    start_time = int(time.time() / 60)
    entries_and_boards = get_learning_schedule(chess.Board(), player, 0, True)
    hashes_set = set(map(lambda x : (x[0].key, x[0].raw_move), entries_and_boards))
    subrep = G.rep.ww if player == chess.WHITE else G.rep.bb
    counter = 0
    for i, entry in enumerate(subrep):
        if (entry.key, entry.raw_move) not in hashes_set and entry.learn > 0:
            counter += 1
            if not only_print:
                subrep[i] = chess.polyglot.Entry(entry.key, entry.raw_move, entry.weight, 0, 0)
            else:
                print(entry.key)
    print("%d changes%s." % (counter, "" if only_print else " made"))

def repeated_nodes(subrep):
    # Just for debugging
    hashes_set = set()
    for entry in subrep:
        if (entry.key, entry.raw_move) in hashes_set and entry.learn > 0:
            print(entry)
            for entry2 in subrep:
                if (entry2.key, entry2.raw_move) == (entry.key, entry.raw_move):
                    print(entry2)
            print("---")
        hashes_set.add((entry.key, entry.raw_move))

def flat_rep_visitor(player):
    subrep = G.rep.ww if player == chess.WHITE else G.rep.bb
    for entry in subrep:
        if entry.learn > 0:
            yield entry

def get_learning_schedule(board, player, max_lines=100, must_use_tree_visitor=False):
    startTime = time.time()
    entries_and_boards = []
    # Get spaced repetition entries
    if max_lines > 0 or must_use_tree_visitor:
        visitor = rep_visitor(board, player, only_sr=True, return_entry=True)
        for b, m, entry in visitor:
            entries_and_boards.append((entry, b))
    else:
        visitor = flat_rep_visitor(player)
        for entry in visitor:
            entries_and_boards.append((entry, None))
    if max_lines == 0:
        return entries_and_boards
    if max_lines > len(entries_and_boards):
        max_lines = len(entries_and_boards)
    # Now we sort the 'max_lines' most urgent entries
    # This is orders of magnitude faster than the iterating through rep_visitor step
    # TODO: Fix (sorting is incorrect right now, quickselect is probably to blame)
    key_function = lambda x : x[0].learn
    quickselect(key_function, max_lines, entries_and_boards)
    entries_and_boards[:max_lines] = sorted(entries_and_boards[:max_lines], key=key_function)
    # The rest is just the printing, which should probably be done somewhere else
    counter = 0
    for entry, b in entries_and_boards:
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
    return entries_and_boards
