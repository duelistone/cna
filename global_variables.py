# global_variables.py
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.pgn, chess.syzygy
import threading, os, sys, asyncio
from matplotlib import colors as mcolors
from ot_information import OT_Information
from constants import *

'''Global variables defined here so they are accessible to all modules. The coder is responsible for not using these before they are defined correctly.'''

# Chess global constants
g = chess.pgn.Game()
player = chess.WHITE
games = [g]
currentGame = 0
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
drag_source = NULL_SQUARE # For location of start of piece drag
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
ot_info = OT_Information()
sound = True # To toggle sound in opening trainer

# Callback for after legal move is complete
# Default is to do nothing
move_completed_callback = lambda x : None

# Engine
engine_commands = ["leela", "stockfish", "ethereal"] # Used for order
engine_settings = {"stockfish" : {"Hash" : 12288, "Threads" : 12, "Contempt" : 0}, "leela" : {}, "ethereal" : {"Hash" : 4096, "Threads" : 4}}
engines = [] # Have to be defined elsewhere due to engine.py dependency on this file
current_engine_index = 0
# Output related
latest_engine_stats = [-1, -1, -1, -1, -1]
latest_engine_lines = []
multipv = 3
show_engine_pv = True
# Weak engine related
playLevel = 20 # Int represents depth, float represents time
# Match related
match_async_loop = None
current_match_task = None
default_match_time_control = "1+1"

# Tablebase
tablebase = None

# Weak engine
weak_engine_enabled_event = None

# NAG's
proper_save_format = False
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
autosave_interval = 90 # In seconds
last_autosave_pgn_string = None # Stores last autosaved PGN string, to avoid repeatedly saving same file
