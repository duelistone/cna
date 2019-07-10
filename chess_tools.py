# chess_tools.py

import chess, chess.pgn, chess.polyglot

zobrist_hash = chess.polyglot.zobrist_hash

# The following two functions are meant to be inverses of each other

def moveToBits(m):
    result = 0
    if m.promotion != None: result |= m.promotion - 1
    result <<= 3
    result |= m.from_square // 8
    result <<= 3
    result |= m.from_square % 8
    result <<= 3
    result |= m.to_square // 8
    result <<= 3
    result |= m.to_square % 8
    return result

def bitsToMove(bits):
    targetFile = bits & 7
    bits = bits >> 3
    targetRank = bits & 7
    bits = bits >> 3
    sourceFile = bits & 7
    bits = bits >> 3
    sourceRank = bits & 7
    bits = bits >> 3
    promotionPiece = bits

    target = 8 * targetRank + targetFile
    source = 8 * sourceRank + sourceFile
    
    return chess.Move(source, target, promotion=promotionPiece - 1)

def bitsToMove2(bits):
    targetRank = bits & 7
    bits = bits >> 3
    targetFile = bits & 7
    bits = bits >> 3
    sourceRank = bits & 7
    bits = bits >> 3
    sourceFile = bits & 7
    bits = bits >> 3
    promotionPiece = bits

    target = 8 * targetRank + targetFile
    source = 8 * sourceRank + sourceFile
    
    return chess.Move(source, target, promotion=promotionPiece)

def nodeAndMoveToKeyAndBits(node, move):
    if move == None:
        return (zobrist_hash(node), 0)
    else:
        return (zobrist_hash(node), moveToBits(move))
    
def keyAndBitsToBytes(key, bits):
    keyPart = key.to_bytes(8, sys.byteorder)
    bitsPart = bits.to_bytes(2, sys.biteorder)
    return keyPart + bitsPart

def bytesToKeyAndBits(byteArray):
    # byteArray should have length >= 10
    key = int.from_bytes(byteArray[:8], sys.byteorder)
    bits = int.from_bytes(byteArray[8:10], sys.byteorder)
    return (key, bits)

def makeEntry(board, move, weight=1, learn=0):
    return chess.polyglot.Entry(zobrist_hash(board), moveToBits(move), weight, learn, move)

def lmFilter(board, move):
    if move in board.legal_moves:
        return move
    return None

def board_moves(board):
    '''Returns a string representing the board moves from root node to the given board.'''
    b = board.copy()
    move_stack = [] # Put together in reverse order, then reversed.
    resultList = []
    while True:
        try:
            m = b.pop()
        except IndexError:
            # Move stack is empty
            break
        move_stack.append(b.san(m))
    move_stack.reverse()
    if b.turn == chess.WHITE:
        # Line starts on white's turn
        for i, e in enumerate(move_stack):
            if i % 2 == 0:
                resultList.append(str(i // 2 + b.fullmove_number) + ". " + e)
            else:
                resultList.append(e)
    else:
        # Line starts on black's turn
        for i, e in enumerate(move_stack):
            if i % 2 == 1:
                resultList.append(str(i // 2 + b.fullmove_number + 1) + ". " + e)
            elif i == 0:
                resultList.append(str(b.fullmove_number) + "... " + e)
            else:
                resultList.append(e)
    return " ".join(resultList)

