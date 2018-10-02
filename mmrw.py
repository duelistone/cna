# mmrw.py

import mmap, os
import chess, chess.polyglot, chess.pgn
from chess_tools import *

class MemoryMappedReaderWriter(chess.polyglot.MemoryMappedReader):
    '''Extends python-chess's polyglot memory mapped reader to also modify them and write new entries.'''
    def __init__(self, filename, length=0, offset=0):
        # Like superclass init, just allowing writing
        self.fd = os.open(filename, os.O_RDWR)
        
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

    def add_position_and_move(self, p, m, weight=1, learn=0):
        entry = makeEntry(p, m)
        self.add_entry(entry)

class Repertoire(object):
    '''Loads, reads, and modifies a repertoire.
    The repertoire in the file system should be a directory with two subdirectories 
    called 'white' and 'black'. Each subdirectory should also contain two files, 
    titled 'white' and 'black'. The 'white' directory contains moves in a repertoire for white,
    while the black repertoire contains moves in a repertoire for black. In each directory,
    the 'white' file contains positions where it is white's move, and the 'black'
    file contains positions where it is black's move.'''

    def __init__(self, directory):
        self.directory = directory
        self.ww = MemoryMappedReaderWriter(directory + '/white/white')
        self.wb = MemoryMappedReaderWriter(directory + '/white/black')
        self.bw = MemoryMappedReaderWriter(directory + '/black/white')
        self.bb = MemoryMappedReaderWriter(directory + '/black/black')

        if None in [self.ww.mmap, self.wb.mmap, self.bw.mmap, self.bb.mmap]: return None

    def flush(self):
        self.ww.mmap.flush()
        self.wb.mmap.flush()
        self.bw.mmap.flush()
        self.bb.mmap.flush()

    def close(self):
        self.ww.mmap.close()
        self.wb.mmap.close()
        self.bw.mmap.close()
        self.bb.mmap.close()

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

    def findMoveWhite(self, p):
        if p.turn == chess.WHITE:
            for entry in self.ww.find_all(p):
                return entry.move()
        else:
            for entry in self.wb.find_all(p):
                return entry.move()
        return None

    def findMoveBlack(self, p):
        if p.turn == chess.WHITE:
            for entry in self.bw.find_all(p):
                return entry.move()
        else:
            for entry in self.bb.find_all(p):
                return entry.move()
        return None

    def findMove(self, perspective, p):
        if perspective == chess.WHITE:
            return self.findMoveWhite(p)
        return self.findMoveBlack(p)

    def findMovesWhite(self, p):
        if p.turn == chess.WHITE:
            return map(lambda e : e.move(), self.ww.find_all(p))
        else:
            return map(lambda e : e.move(), self.wb.find_all(p))

    def findMovesBlack(self, p):
        if p.turn == chess.WHITE:
            return map(lambda e : e.move(), self.bw.find_all(p))
        else:
            return map(lambda e : e.move(), self.bb.find_all(p))

    def findMoves(self, perspective, p):
        if perspective == chess.WHITE:
            return self.findMovesWhite(p)
        return self.findMovesBlack(p)

    def hasPositionWhite(self, p):
        for e in self.findMovesWhite(p):
            return True
        return False

    def hasPositionBlack(self, p):
        for e in self.findMovesBlack(p):
            return True
        return False

    def removeWhite(self, p, move=None):
        zh = zobrist_hash(p)
        deleteIndices = set()
        mmrw = self.ww
        if p.turn == chess.BLACK: mmrw = self.wb
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

    def removeBlack(self, p, move=None):
        zh = zobrist_hash(p)
        deleteIndices = set()
        mmrw = self.bw
        if p.turn == chess.BLACK: mmrw = self.bb
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

