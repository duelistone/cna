# drawing.py
'''Module for drawing code. Drawing callback function is actually in callbacks.py.'''
import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg
import global_variables as G
import cairo
import chess

def load_svgs(base_dir):
    piece_letters = "pnbrqk"
    for piece_type in range(chess.PAWN, chess.KING + 1):
        for piece_color in [chess.WHITE, chess.BLACK]:
            piece = chess.Piece(piece_type, piece_color)
            pl = piece_letters[piece_type - 1]
            sl = 'w' if piece_color == chess.WHITE else 'b'
            path = "%s%c_%c.svg" % (base_dir, sl, pl)
            index = piece_image_index(piece)
            handle = Rsvg.Handle()
            G.piece_images[index] = handle.new_from_file(path)

def piece_image_index(piece):
    '''Determines index of the image of a given piece.'''
    return -1 + piece.piece_type + 6 if piece.color == chess.WHITE else -1 + piece.piece_type

def draw_piece(cr, piece, square_size):
    '''Helper function just responsible for drawing one piece.'''
    piece_image = G.piece_images[piece_image_index(piece)]
    scale = 0.025 * square_size / G.DEFAULT_SQUARE_SIZE
    cr.scale(scale, scale)
    piece_image.render_cairo(cr)
    cr.scale(1 / scale, 1 / scale)

def get_square_size(boardWidget):
    width = boardWidget.get_allocated_width()
    height = boardWidget.get_allocated_height()
    max_square_width = width // 8
    max_square_height = height // 8
    return min(max_square_width, max_square_height)
