# mmrw.py

import mmap, os, os.path, time, sys, subprocess
import chess, chess.polyglot, chess.pgn
from spaced_repetition import *
from chess_tools import *
from bisect import bisect_left

class MemoryMappedReaderWriter(chess.polyglot.MemoryMappedReader):
    '''Extends python-chess's polyglot memory mapped reader to also modify them and write new entries.'''
    def __init__(self, filename, length=0, offset=0):
        # Like superclass init, just allowing writing
        self.fd = os.open(filename, os.O_RDWR)
        self.filename = filename

        try:
            self.mmap = mmap.mmap(self.fd, length, offset=offset)
        except:
            self.mmap = None

    def add_entry(self, entry):
        # Get bytes to write
        byteArray = entry.key.to_bytes(8, byteorder="big")
        byteArray += entry.raw_move.to_bytes(2, byteorder="big")
        byteArray += entry.weight.to_bytes(2, byteorder="big")
        byteArray += entry.learn.to_bytes(4, byteorder="big")

        # Increase size of mmap by 16 bytes
        insertionIndex = 16 * self.bisect_key_left(entry.key)
        oldEndIndex = self.mmap.size()
        self.mmap.resize(oldEndIndex + 16)

        # Write to mmap (use flush method on self.mmap to make sure this
        # has gone through to hard drive)
        # To keep the book ordered, we apply an insertion sort
        nextEntry = None
        for i in range(insertionIndex, oldEndIndex + 16, 16):
            if i == insertionIndex:
                nextEntry = self.mmap[i:i + 16]
                self.mmap[i:i + 16] = byteArray
            else:
                nextTempEntry = self.mmap[i:i + 16]
                self.mmap[i:i + 16] = nextEntry
                nextEntry = nextTempEntry

    def remove_entry(self, entry):
        for i, e in enumerate(self):
            if e == entry:
                del self[i]
                break

    def edit_entry(self, index, position, move, new_weight, new_learn):
        # Make entry and corresponding byte array
        entry = makeEntry(position, move, new_weight, new_learn)
        self[index] = entry

    def __setitem__(self, key, value):
        byteArray = value.key.to_bytes(8, byteorder="big")
        byteArray += value.raw_move.to_bytes(2, byteorder="big")
        byteArray += value.weight.to_bytes(2, byteorder="big")
        byteArray += value.learn.to_bytes(4, byteorder="big")
        self.mmap[16 * key : 16 * key + 16] = byteArray

    def __delitem__(self, key):
        for i in range(key, len(self) - 1):
            self[i] = self[i + 1]
        self.mmap.resize(len(self.mmap) - 16)

    def __contains__(self, entry):
        index = self.bisect_key_left(entry.key)
        if index >= len(self):
            return False
        suggestion = self[index]
        while suggestion.key == entry.key:
            if suggestion.move == entry.move:
                return True
            index += 1
            suggestion = self[index]
        return False

    def add_position_and_move(self, p, m, weight=1, learn=0):
        entry = makeEntry(p, m, weight, learn)
        # We do nothing if entry with same position/move combo is already in mmap
        if entry not in self:
            self.add_entry(entry)

class CommentsMMRW(mmap.mmap):
    def __init__(self, fd, length):
        self.key_size = 8
        self.comment_size = 248
        self.entry_size = self.key_size + self.comment_size

    def hash_at_position_index(self, i):
        byte_list = self[i * self.entry_size:i * self.entry_size + self.key_size]
        return int.from_bytes(byte_list, byteorder="big")

    def comment_at_position_index(self, i):
        start = i * self.entry_size + self.key_size
        end = (i + 1) * self.entry_size
        return self[start:end].decode('utf-8').rstrip('\0')

    def create_entry(self, i):
        '''Creates an empty entry at index i, which should immediately after
        be given an appropriate hash to keep the ordering.'''
        if i > self.size() // self.entry_size or i < 0:
            raise ValueError("Invalid index given")
        start = i * self.entry_size
        end = self.size()
        self.resize(self.size() + self.entry_size)
        self[start + self.entry_size : end + self.entry_size] = self[start:end]
        self[start : start + self.entry_size] = self.entry_size * b'\0'

    def replace_entry(self, i, h, s):
        '''Replaces the entry at index i with hash h and string s.'''
        # Get bytes to add
        byteArray = h.to_bytes(8, byteorder="big")
        byteArray += s.encode('utf-8')
        padding_length = self.entry_size - len(byteArray)
        if padding_length < 0:
            raise ValueError("Size of opening comment is too large")
        byteArray += padding_length * b'\0'

        # Get indices
        start = i * self.entry_size
        end = (i + 1) * self.entry_size
        self[start:end] = byteArray
        
    def find_position(self, p):
        if type(p) != int:
            p = chess.polyglot.zobrist_hash(p)
        left = 0
        right = self.size() // self.entry_size
        while left < right:
            middle = (left + right) // 2
            hash_to_test = self.hash_at_position_index(middle)
            if hash_to_test < p:
                left = middle + 1
            elif hash_to_test > p:
                right = middle
            else:
                return middle
        return left


class Repertoire(object):
    '''Loads, reads, and modifies a repertoire.
    
    The repertoire in the file system should be a directory with two 
    subdirectories called 'white' and 'black'. Each subdirectory should 
    also contain two files, titled 'white' and 'black'. The 'white' 
    directory contains moves in a repertoire for white, while the black 
    repertoire contains moves in a repertoire for black. In each directory, 
    the 'white' file contains positions where it is white's move, and the 'black'
    file contains positions where it is black's move.'''

    def __init__(self, directory):
        # TODO: Create directories/files when they do not exist
        self.directory = directory
        self.ww = MemoryMappedReaderWriter(os.sep.join([directory, 'white', 'white']))
        self.wb = MemoryMappedReaderWriter(os.sep.join([directory, 'white', 'black']))
        self.bw = MemoryMappedReaderWriter(os.sep.join([directory, 'black', 'white']))
        self.bb = MemoryMappedReaderWriter(os.sep.join([directory, 'black', 'black']))
        self.t  = MemoryMappedReaderWriter(os.sep.join([directory, 'tactics']))

        # If some of code below takes too long to run and isn't necessary
        # at startup, consider putting it in a thread and joining the thread
        # when necessary

        comments_filename = os.sep.join([directory, 'comments'])
        if os.path.getsize(comments_filename) == 0:
            fil = open(comments_filename, 'w')
            fil.write(G.COMMENT_ENTRY_SIZE * '\0') # Change if comment entry size changes
            fil.close()
        comments_file = os.open(comments_filename, os.O_RDWR)
        try:
            self.comments = CommentsMMRW(comments_file, 0)
        except Exception as e:
            # For now
            print(e, file=sys.stderr)
            pass

        # Load initial positions
        self.initial_positions = []
        self.initial_position_hashes = []
        try:
            fil = open(os.sep.join([directory, 'initial_positions']), 'r')
            for line in fil:
                try:
                    b = chess.Board(fen=line.strip())
                    self.initial_positions.append(b)
                    self.initial_position_hashes.append(chess.polyglot.zobrist_hash(b))
                except:
                    continue
            fil.close()
        except FileNotFoundError:
            pass

        if None in [self.ww.mmap, self.wb.mmap, self.bw.mmap, self.bb.mmap, self.t]:
            return None

    def save_initial_positions_to_file(self):
        fil = open(os.sep.join([self.directory, 'initial_positions']), 'w')
        for line in map(lambda x : x.fen(), self.initial_positions):
            print(line, file=fil)
        fil.close()

    def add_initial_position(self, b, save=False):
        h = chess.polyglot.zobrist_hash(b)
        index = bisect_left(self.initial_position_hashes, h)
        self.initial_positions.insert(index, b)
        self.initial_position_hashes.insert(index, h)
        if save:
            self.save_initial_positions_to_file()

    def delete_initial_position(self, b, delete_orphans=False, save=False):
        h = chess.polyglot.zobrist_hash(b)
        index = bisect_left(self.initial_position_hashes)
        del self.initial_positions[index]
        del self.initial_position_hashes[index]
        if delete_orphans:
            self.delete_orphaned_tactics()
        if save:
            self.save_initial_positions_to_file()

    def delete_orphaned_tactics(self):
        hashes = set()
        for b, _ in tactics_visitor():
            hashes.add(chess.polyglot.zobrist_hash(b))
        # This can probably be more efficient, as each delete might be expensive
        for i in range(0, len(self.t)):
            if self.t[i].key not in hashes:
                del self.t[i]

    def set_comment(self, position, comment):
        '''Saves the comment for the position in the self.comments file.'''
        if type(position) == int:
            # Hash already given
            h = position
        else:
            h = chess.polyglot.zobrist_hash(position)
        index = self.comments.find_position(h)
        if self.comments.hash_at_position_index(index) == h:
            try:
                # Replace opening comment
                self.comments.replace_entry(index, h, comment)
            except ValueError as e:
                print(e, file=sys.stderr)
                return
        else:
            # Add new entry at index
            self.comments.create_entry(index)
            self.comments.replace_entry(index, h, comment)
            return None
        pass

    def get_comment(self, position):
        '''Returns comment for given position, or None if the position
        does not have a comment in the repertoire.'''
        if type(position) == int:
            # Hash already given
            h = position
        else:
            h = chess.polyglot.zobrist_hash(position)
        index = self.comments.find_position(h)
        if self.comments.hash_at_position_index(index) == h:
            return self.comments.comment_at_position_index(index)
        else:
            return None

    def get_mmrw(self, player, turn_color):
        if player == chess.WHITE and turn_color == chess.WHITE:
            return self.ww
        if player == chess.WHITE and turn_color == chess.BLACK:
            return self.wb
        if player == chess.BLACK and turn_color == chess.WHITE:
            return self.bw
        if player == chess.BLACK and turn_color == chess.BLACK:
            return self.bb
        if player == None:
            return self.t

    def flush(self):
        self.ww.mmap.flush()
        self.wb.mmap.flush()
        self.bw.mmap.flush()
        self.bb.mmap.flush()
        self.t.mmap.flush()

    def close(self):
        self.ww.mmap.close()
        self.wb.mmap.close()
        self.bw.mmap.close()
        self.bb.mmap.close()
        self.t.mmap.close()

    def appendWhite(self, p, m, weight=1, learn=0):
        if p.turn == chess.WHITE:
            self.ww.add_position_and_move(p, m, weight, learn)
        else:
            self.wb.add_position_and_move(p, m, weight, learn)

    def appendBlack(self, p, m, weight=1, learn=0):
        if p.turn == chess.WHITE:
            self.bw.add_position_and_move(p, m, weight, learn)
        else:
            self.bb.add_position_and_move(p, m, weight, learn)

    def appendTactic(self, p, m, weight=None, learn=None):
        if weight == None or learn == None:
            weight, learn = export_values(2.5, 0, int(time.time() / 60))
        self.t.add_position_and_move(p, m, weight, learn)

    def findMove(self, perspective, p):
        mmrw = self.get_mmrw(perspective, p.turn)
        for entry in mmrw.find_all(p):
            return entry.move

    def findMoveWhite(self, p):
        return self.findMove(chess.WHITE, p)

    def findMoveBlack(self, p):
        return self.findMove(chess.BLACK, p)

    def findMoves(self, perspective, p):
        mmrw = self.get_mmrw(perspective, p.turn)
        return map(lambda e : e.move, mmrw.find_all(p))

    def findMovesWhite(self, p):
        return self.findMoves(chess.WHITE, p)

    def findMovesBlack(self, p):
        return self.findMoves(chess.BLACK, p)

    def hasPositionWhite(self, p):
        for e in self.findMovesWhite(p):
            return True
        return False

    def hasPositionBlack(self, p):
        for e in self.findMovesBlack(p):
            return True
        return False

    def remove(self, perspective, p, move=None):
        zh = zobrist_hash(p)
        deleteIndices = set()
        mmrw = self.get_mmrw(perspective, p.turn)
        index = 16 * mmrw.bisect_key_left(zh)

        # Find deletions to make
        for i in range(index, 16 * len(mmrw), 16):
            key, mBits, _, _ = chess.polyglot.ENTRY_STRUCT.unpack_from(mmrw.mmap, i)
            if key != zh:
                break
            elif move == None or moveToBits(move) == mBits:
                deleteIndices.add(i)

        # Make deletions to mmap
        if len(deleteIndices) > 0:
            offset = 0
            for i in range(index, 16 * len(mmrw), 16):
                while i + offset in deleteIndices:
                    offset += 16
                if i + offset >= 16 * len(mmrw):
                    break
                if offset != 0:
                    mmrw.mmap[i:i + 16] = mmrw.mmap[i + offset:i + offset + 16]
        mmrw.mmap.resize(len(mmrw.mmap) - 16 * len(deleteIndices))

        return len(deleteIndices)

    def removeWhite(self, p, move=None):
        return self.remove(chess.WHITE, p, move)

    def removeBlack(self, p, move=None):
        return self.remove(chess.BLACK, p, move)

    def removeTactic(self, p, move=None):
        # Less efficient attempt than remove method
        h = chess.polyglot.zobrist_hash(p)
        index = self.t.bisect_key_left(h)
        for i in range(index, len(self.t)):
            if self.t[i].key == h:
                if move == None or move == self.t[i].move:
                    del self.t[i]
            else:
                break

    def add_games(self, games=[], filenames=[]):
        # Do nothing case
        if len(games) == 0 and len(filenames) == 0:
            return

        # Variable to list filenames that encountered an error
        errors = []

        # We're saving the games to self.directory + '/games' + number,
        # where number is one more than the highest number already used.
        # Here we calculate what this number is.
        game_directory = self.directory + os.sep + 'games'
        position_directory = self.directory + os.sep + 'positions' # Used further below
        existing_files = os.listdir(game_directory)
        next_game_number = 0
        for name in existing_files:
            try:
                n = int(name)
            except:
                continue
            if n >= next_game_number:
                next_game_number = n + 1

        # Combine lists
        for filename in filenames:
            try:
                pgnFile = open(filename, 'r')
                game = chess.pgn.read_game(filename)
                pgnFile.close()
            except:
                errors.append(filename)
                continue
            games.append(game)

        # Now we know we're saving to game_directory + os.sep + str(next_game_number).
        # We loop through the inputs.
        for game in games:
            # Store game
            outputFile = open(game_directory + os.sep + str(next_game_number), 'w')
            print(game, file=outputFile)
            outputFile.close()

            # Link relevant nodes to game
            # Will just run through principal variation
            while game.variations:
                board = game.board()
                key = zobrist_hash(game.board())
                positionFile = None
                pgnFile = None
                try:
                    pgnFile = open(position_directory + os.sep + str(key), 'r')
                except FileNotFoundError:
                    # If creating file for node, just need to write the game number
                    pgnFile = open(position_directory + os.sep + str(key), 'w')
                    print(next_game_number, file=pgnFile)
                    pgnFile.close()
                    game = game.variation(0)
                    continue

                if pgnFile != None:
                    # Parse file contents
                    firstLine = pgnFile.readline().strip()
                    rest = pgnFile.read()
                    pgnFile.close()
                    # Form new first line
                    firstLine += ',' + str(next_game_number)
                    # Reopen to write
                    # TODO: Use temp file in case something goes wrong between
                    # reading and writing
                    pgnFile = open(position_directory + os.sep + str(key), 'w')
                    print(firstLine, file=pgnFile)
                    print(rest, file=pgnFile, end="")
                    pgnFile.close()

                # Go to next node
                game = game.variation(0)

            # Update next_game_number
            next_game_number += 1

        # Return number of errors
        return errors

    def list_games(self, position):
        positionDirectory = self.directory + os.sep + 'positions'
        positionFile = None
        try:
            positionFile = open(positionDirectory + os.sep + str(zobrist_hash(position)), 'r')
        except FileNotFoundError:
            return []
        firstLine = positionFile.readline()
        games = list(map(lambda x : x.strip(), firstLine.split(',')))
        return games

    def make_position_learnable(self, position, perspective, override=False):
        weight, learn = export_values(2.5, 0, int(time.time() / 60))
        mmrw = self.get_mmrw(perspective, position.turn)
        position_hash = chess.polyglot.zobrist_hash(position)
        index = mmrw.bisect_key_left(position_hash)
        while index < len(mmrw):
            entry = mmrw[index]
            if entry.key != position_hash:
                break
            # The line below would be more efficient if it used hash and raw move
            # The weight and learn should already be in their raw bits format
            # First we check it hasn't been already set for learning!
            if entry.learn == 0 or override == True:
                mmrw.edit_entry(index, position, entry.move, weight, learn)
            index += 1

    def update_modified_date(self, player, turn):
        mmrw = self.get_mmrw(player, turn)
        subprocess.Popen(["touch", mmrw.filename])

    def update_learning_data(self, player, position, move, incorrect_answers, time_to_complete):
        mmrw = self.get_mmrw(player, position.turn)
        # Get q value
        q = 3
        if incorrect_answers > 2:
            q = 0
        elif incorrect_answers == 2:
            q = 1
        elif incorrect_answers == 1:
            q = 2
        else:
            if time_to_complete < 30:
                q = 5
            elif time_to_complete < 60:
                q = 4

        # Find node
        position_hash = chess.polyglot.zobrist_hash(position)
        index = mmrw.bisect_key_left(position_hash)
        counter = 0
        while index < len(mmrw):
            entry = mmrw[index]
            if entry.key != position_hash:
                break
            if entry.move != move:
                index += 1
                continue
            if counter > 0:
                # This shouldn't happen!
                # To make work, need to compare positions
                print("Warning: following board/move pair has multiple entries")
                print(position)
                print("Board hash: %d" % position_hash)
                print(move)
                break
            # The line below would be more efficient if it used hash and raw move
            # The weight and learn should already be in their raw bits format
            # First we check it hasn't been already set for learning!
            e, c, n = read_values((entry.weight << 32) | entry.learn)
            e, c, n = update_spaced_repetition_values(e, c, n, q)
            weight, learn = export_values(e, c, n)
            mmrw.edit_entry(index, position, entry.move, weight, learn)
            index += 1
            counter += 1
