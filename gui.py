import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.pgn, chess.polyglot, sys, subprocess, time, os, os.path, random, re, signal, threading, unicodedata, cairo
import global_variables as G
from chess_tools import *
from opening_pgn import *
from mmrw import *
from dfs import *
from drawing import *
from callbacks import *

def main():
    # Change directory to application directory
    if G.base_directory != "": 
        os.chdir(G.base_directory)

    # Load images and GUI elements
    load_svgs("pieces/merida/")
    builder = gtk.Builder()
    builder.add_from_file("chessboard.ui")
    builder.connect_signals(G.handlers)

    # Determine player color
    if '-b' in sys.argv:
        G.player = chess.BLACK
        sys.argv.remove('-b')

    # Get tablebase path
    if "--tb" in sys.argv:
        tbIndex = sys.argv.index('--tb')
        try:
            tablebase_path = sys.argv[tbIndex + 1]
            del sys.argv[tbIndex + 1]
        except:
            pass
        finally:
            del sys.argv[tbIndex]
        for e in G.engine_settings:
            G.engine_settings[e].update({"SyzygyPath": tablebase_path})

    # Check if should use opening test or learn mode and finish preperations
    useOpeningMode = '--ot' in sys.argv
    useLearningMode = '--sr' in sys.argv # Still needs to have '--ot' as well, for now
    if useLearningMode:
        sys.argv.remove('--sr')
        if not useOpeningMode:
            print("Incorrect usage. Cannot practice spaced repetition without ot mode.", file=sys.stderr)
            exit(1)
    if useOpeningMode:
        otIndex = sys.argv.index('--ot')
        fenString = " ".join(sys.argv[otIndex + 1:])
        del sys.argv[otIndex:]
        G.ot_board = chess.Board(fen=fenString)
        if G.ot_board == None: raise ValueError("Bad FEN") # Temporary
        preparations(builder)
        setup_ot_mode(only_sr=useLearningMode)
    else:
        preparations(builder)

    # Show elements
    G.window.show_all()
    G.stockfish_textview.hide()

    # Start main loop
    G.glib_mainloop.run()

def preparations(builder):
    # Widget extraction
    G.window = builder.get_object("main_window")
    G.board_display = builder.get_object("board_drawing_area")
    G.status_bar = builder.get_object("status_bar")
    G.stockfish_textview = builder.get_object("stockfish_textview")
    G.stockfish_buffer = G.stockfish_textview.get_buffer()
    G.pgn_textview = builder.get_object("pgn_textview")
    G.pgn_buffer = G.pgn_textview.get_buffer()
    G.board_h_box = builder.get_object("board_h_box")
    G.scrolled_window = builder.get_object("scrolled_window")
    G.entry_bar = builder.get_object("entry_bar")
    G.queen_promotion_item = builder.get_object("queen_promotion")
    G.rook_promotion_item = builder.get_object("rook_promotion")
    G.bishop_promotion_item = builder.get_object("bishop_promotion")
    G.knight_promotion_item = builder.get_object("knight_promotion")

    # Extra definitions
    G.status_bar_cid = G.status_bar.get_context_id("")

    # Signal connections
    G.window.connect("destroy", destroy_main_window_callback)
    G.window.connect("key_press_event", key_press_callback)
    G.board_display.add_events(gdk.EventMask.BUTTON_PRESS_MASK | gdk.EventMask.BUTTON_RELEASE_MASK | gdk.EventMask.POINTER_MOTION_MASK | gdk.EventMask.SCROLL_MASK)
    G.board_display.connect("draw", board_draw_callback)
    G.board_display.connect("button-press-event", board_mouse_down_callback)
    G.board_display.connect("button-release-event", board_mouse_up_callback)
    G.board_display.connect("motion-notify-event", board_mouse_move_callback)
    G.board_display.connect("scroll-event", board_scroll_event_callback)
    G.pgn_textview.connect("key-press-event", pgn_textview_key_press_callback)

    G.key_binding_map[gdk.KEY_i] = G.entry_bar.grab_focus

    # PGN textview tags
    G.pgn_buffer.create_tag(tag_name="monospace", family="Monospace")
    G.pgn_buffer.create_tag(tag_name="special", weight=pango.Weight.BOLD)
    G.pgn_buffer.create_tag(tag_name="book", underline=pango.Underline.SINGLE)
    G.pgn_buffer.create_tag(tag_name="learn", style=pango.Style.ITALIC)
    G.pgn_buffer.create_tag(tag_name="comment", foreground="#009900")
    G.pgn_buffer.create_tag(tag_name="current", background="#9FCCFF")

    # Handle command line arguments
    if len(sys.argv) > 1:
        load_new_game_from_pgn_file(sys.argv[1])
    
    # Prepare repertoire and mark nodes
    try:
        G.rep = Repertoire("main.rep")
    except:
        pass
    mark_nodes(G.g.root())
    
# For graceful exits
GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, signal_handler, signal.SIGINT)
GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, signal_handler, signal.SIGTERM)

# Start
try:
    main()
except KeyboardInterrupt:
    signal_handler()
