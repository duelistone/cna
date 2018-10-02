# global_variables.py
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.pgn
import threading

'''Global variables defined here so they are accessible to all modules. The coder is responsible for not using these before they are defined correctly.'''

# Chess global constants
g = chess.pgn.Game()
player = chess.WHITE
games = [g]
currentGame = 0

# Gtk global constants
# These will be defined after the builder loads the ui file
glib_mainloop = GLib.MainLoop()
window = None
pgn_window = None
pgn_textview = None
pgn_buffer = None
stockfish_textview = None
stockfish_buffer = None
status_bar = None
board_display = None
clipboard = gtk.Clipboard.get(selection=gdk.SELECTION_CLIPBOARD)
selection = gtk.Clipboard.get(selection=gdk.SELECTION_PRIMARY)
board_h_box = None
scrolled_window = None

status_bar_cid = None 
handlers = {} # Callback functions dictionary for builder
NULL_SQUARE = -1
drag_source = NULL_SQUARE # For location of start of piece drag
DEFAULT_SQUARE_SIZE = 50
mouse_x = 0
mouse_y = 0
pgn_textview_enabled = False
textview_pressed_text_iter = None
bufferToNodes = {}
nodesToRanges = {}
currentMoveOffset = None
specialRanges = []
bookRanges = []
commentRanges = []
currentMoveRange = (None, None)

# Other global constants
piece_images = [None] * 12
promotion_piece = chess.QUEEN
rep = None
pgnFile = None
save_file_name = "savedGame.pgn"
save_file_names = ["savedGame.pgn"]
repertoire_file_name = "main.rep"
escapeKeys = [gdk.KEY_Escape, gdk.KEY_semicolon, gdk.KEY_Control_L, gdk.KEY_Control_R, gdk.KEY_o, gdk.KEY_v, gdk.KEY_Left, gdk.KEY_Right]
ignoreKeys = [gdk.KEY_j, gdk.KEY_k]

# For key press events
controlPressed = False
inMove = None
currentMove = ""

# Generator for opening trainer positions
ot_gen = None

# Callback for after legal move is complete
# Default is to do nothing
move_completed_callback = lambda x : None

# Engine
stockfish_text_lock = threading.Lock()
stockfish_enabled = False
NUM_VARIATIONS = 1
NUM_THREADS = 2
HASH_SIZE = 4096
stockfish = None 
playLevel = 20 # Int represents depth, float represents time

# Weak engine
weak_stockfish = None
weak_stockfish_enabled = False
WEAK_STOCKFISH_DEFAULT_LEVEL = 4
