# global_variables.py
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.pgn
import threading, os, sys, asyncio
from matplotlib import colors as mcolors

'''Global variables defined here so they are accessible to all modules. The coder is responsible for not using these before they are defined correctly.'''

# Chess global constants
g = chess.pgn.Game()
player = chess.WHITE
games = [g]
currentGame = 0
ADD_MAIN_VARIATION = 1
ADD_LAST_VARIATION = -1
new_move_mode = ADD_MAIN_VARIATION

# Gtk global constants
# These will be defined after the builder loads the ui file
glib_mainloop = GLib.MainLoop()
window = None
pgn_window = None
pgn_textview = None
pgn_buffer = None
stockfish_textview = None
stockfish_buffer = None
entry_bar = None
status_bar = None
board_display = None
clipboard = gtk.Clipboard.get(selection=gdk.SELECTION_CLIPBOARD)
selection = gtk.Clipboard.get(selection=gdk.SELECTION_PRIMARY)
board_h_box = None
scrolled_window = None
queen_promotion_item = None
rook_promotion_item = None
bishop_promotion_item = None
knight_promotion_item = None

pgn_textview_mark = None
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
learnRanges = []
commentRanges = []
currentMoveRange = (None, None)

# Arrows
# Should be a list of pairs of squares
# If the two squares are the same, that means to highlight the square
# TODO: Make dict with colors as values and current elems as keys.
arrows = set()
arrow_source = NULL_SQUARE
arrowRGBA = [0, 0.4, 0, 0.5]

# Other global constants
base_directory = os.path.dirname(sys.argv[0])
piece_images = [None] * 12
puzzle_file = 'puzzles'
promotion_piece = chess.QUEEN
rep = None
pgnFile = None
save_file_name = "savedGame.pgn"
save_file_names = ["savedGame.pgn"]
repertoire_file_name = "main.rep"

currentMove = ""

# For key press events
escapeKeys = [gdk.KEY_Escape, gdk.KEY_semicolon] #, gdk.KEY_Control_L, gdk.KEY_Control_R]
modifier_mask = gtk.accelerator_get_default_mod_mask() & ~gdk.ModifierType.SHIFT_MASK
modifier_names = {gdk.ModifierType.CONTROL_MASK: "Ctrl",
    gdk.ModifierType.MOD1_MASK: "Alt",
    gdk.ModifierType.MOD2_MASK: "Mod2",
    gdk.ModifierType.MOD3_MASK: "Mod3",
    gdk.ModifierType.MOD4_MASK: "Mod4",
    gdk.ModifierType.MOD5_MASK: "Mod5",
    gdk.ModifierType.SUPER_MASK: "Super",
    gdk.ModifierType.META_MASK: "Meta",
    gdk.ModifierType.HYPER_MASK: "Hyper"}
modifier_bit_values = {modifier_names[k]:k for k in modifier_names}
key_binding_maps = {}

# For entry_bar commands
command_callbacks = {}
command_history = []
command_index = 0

# Generator for opening trainer positions
ot_gen = None
ot_board = None
incorrect_answers = 0
starting_time = 0

# Callback for after legal move is complete
# Default is to do nothing
move_completed_callback = lambda x : None

# Engine
engine_command = "leela"
engine_settings = {"stockfish" : {"Hash" : 8192, "Threads" : 8, "Contempt" : 0}, "leela" : {}, "ethereal" : {"Hash" : 4096, "Threads" : 2}}
engine_board = chess.Board()
stockfish_text_lock = threading.Lock()
engine_enabled_event = None # Must be defined inside async loop
latest_engine_stats = [-1, -1, -1, -1, -1]
latest_engine_lines = []
engine_best_move = None
multipv = 1
stockfish = None 
playLevel = 20 # Int represents depth, float represents time

# Weak engine
weak_engine_enabled_event = None
WEAK_STOCKFISH_DEFAULT_LEVEL = 4

# NAG's
proper_save_format = False
nag_strings = 256 * [""]
nag_strings[1:24] = ["!", "?", "\u203c", "\u2047", "\u2049", "\u2048", "\u25a1", "\u25a1", "", "=", "", "", "\u221e", "\u2a72", "\u2a71", "\u00b1", "\u2213", "+-", "-+", "1-0", "0-1", "\u2a00", "\u2a00"] 
nag_strings[24:30] = 6 * ["\u25cb"]
nag_strings[30:36] = 6 * ["\u27f3"]
nag_strings[36:42] = ["\u2192", "\u2192", "\u2192", "\u2192", "\u2191", "\u2191"]
nag_strings[42:48] = 6 * ["=/\u221e"]
nag_strings[130:136] = 6 * ["\u21c6"]
nag_strings[136:140] = 4 * ["\u2295"]
nag_strings[140:143] = ["\u25B3", "\u25BD", "\u2313"]
nag_strings[145:147] = ["RR", "N"]
nag_strings[238:246] = ["\u25cb", "\u21d4", "\u21d7", "", "\u27eb", "\u27ea", "\u2715", "\u22A5"]

nag_names = 256 * [""]
nag_names[1:24] = ["", "", "!!", "??", "!?", "?!", "box", "", "", "equal", "", "", "unclear", "+=", "=+", "+/-", "-/+", "", "", "", "", "zugswang", "zugswang"]
nag_names[24:30] = 6 * ["space"]
nag_names[30:36] = 6 * ["development"]
nag_names[36:42] = 6 * ["initiative"]
nag_names[42:48] = 6 * ["compensation"]
nag_names[130:136] = 6 * ["counterplay"]
nag_names[136:140] = 4 * ["time_trouble"]
nag_names[140:143] = ["with_idea", "countering", "better_is"]
nag_names[145:147] = ["editorial_comment", "novelty"]
nag_names[238:246] = ["space", "file", "diagonal", "", "kingside", "queenside", "weakness", "endgame"]

nag_set = set(nag_strings + nag_names)

# Colors
colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
# Remove annoying single letter color names
for c in set(colors):
    if len(c) == 1:
        del colors[c]

# Set of documented functions
documented_functions = set()

# Lichess support
use_lichess = False # Set to true to use lichess in listing opening moves
cached_lichess_responses = {} # Dictionary to keep JSON responses for opening positions
top_game_ids = []

# Autosave interval
autosave = True # Set to False to turn off autosave
autosave_dir = ".autosave/"
autosave_interval = 60 # In seconds
last_autosave_pgn_string = None # Stores last autosaved PGN string, to avoid repeatedly saving same file
