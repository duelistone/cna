# drawing.py
'''Module for drawing code. Drawing callback function is actually in callbacks.py.'''
import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg
import global_variables as G
import cairo
import chess
import math

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

def highlight_square(cr, square_size):
    cr.save()
    cr.set_source_rgba(0, 1, 0, 0.2)
    cr.rectangle(0, 0, square_size, square_size)
    cr.fill()
    cr.restore()

def draw_arrow(cr, square_size, source, target):
    cr.save()
    
    # Get row and column
    source_row = 7 - chess.square_rank(source)
    source_col = chess.square_file(source)
    target_row = 7 - chess.square_rank(target)
    target_col = chess.square_file(target)
    
    # Fix row and column if black's perspective
    if G.player == chess.BLACK:
        source_row = 7 - source_row
        source_col = 7 - source_col
        target_row = 7 - target_row
        target_col = 7 - target_col

    # Draw line part of arrow
    LINE_WIDTH = square_size / 9
    TRIANGLE_RADIUS = square_size / 4.0
    direction_vector = normalize((target_col - source_col, target_row - source_row))
    source_coords = (square_size * source_col + square_size / 2, square_size * source_row + square_size / 2)
    target_coords = (square_size * target_col + square_size / 2, square_size * target_row + square_size / 2)
    cr.set_source_rgba(0, 0.4, 0, 0.5)
    cr.set_line_width(LINE_WIDTH)
    cr.move_to(*source_coords)
    cr.line_to(*add(target_coords, scale(direction_vector, TRIANGLE_RADIUS * math.cos(2 * math.pi / 3))))
    cr.stroke()

    # Draw angled equilateral triangle at target
    top = add(target_coords, scale(direction_vector, TRIANGLE_RADIUS))
    left = add(target_coords, scale(rotate(direction_vector, 2 * math.pi / 3), TRIANGLE_RADIUS))
    right = add(target_coords, scale(rotate(direction_vector, 4 * math.pi / 3), TRIANGLE_RADIUS))
    cr.move_to(*top)
    cr.line_to(*left)
    cr.line_to(*right)
    cr.close_path()
    cr.fill()

    cr.restore()

def normalize(vector):
    size = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])
    return (vector[0] / size, vector[1] / size)

def scale(vector, n):
    return (vector[0] * n, vector[1] * n)

def rotate(vector, theta):
    return (vector[0] * math.cos(theta) - vector[1] * math.sin(theta), vector[0] * math.sin(theta) + vector[1] * math.cos(theta))

def add(vector, vector2):
    return (vector[0] + vector2[0], vector[1] + vector2[1])

def get_square_size(boardWidget):
    width = boardWidget.get_allocated_width()
    height = boardWidget.get_allocated_height()
    max_square_width = width // 8
    max_square_height = height // 8
    return min(max_square_width, max_square_height)
