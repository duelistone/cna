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
    load_svgs("/home/duelist/cna/chessboard/pieces/merida/")
    builder = gtk.Builder()
    builder.add_from_file("/home/duelist/cna/chessboard.ui")
    builder.connect_signals(G.handlers)
    preparations(builder)
    G.window.show_all()
    G.stockfish_textview.hide()
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

    # Extra definitions
    G.status_bar_cid = G.status_bar.get_context_id("")

    # Signal connections
    G.window.connect("destroy", destroy_main_window_callback)
    G.window.connect("key_press_event", key_press_callback)
    G.window.connect("key_release_event", key_release_callback)
    G.board_display.add_events(gdk.EventMask.BUTTON_PRESS_MASK | gdk.EventMask.BUTTON_RELEASE_MASK | gdk.EventMask.POINTER_MOTION_MASK | gdk.EventMask.SCROLL_MASK)
    G.board_display.connect("draw", board_draw_callback)
    G.board_display.connect("button-press-event", board_mouse_down_callback)
    G.board_display.connect("button-release-event", board_mouse_up_callback)
    G.board_display.connect("motion-notify-event", board_mouse_move_callback)
    G.board_display.connect("scroll-event", board_scroll_event_callback)
    G.pgn_textview.connect("key-press-event", pgn_textview_key_press_callback)

    # PGN textview tags
    G.pgn_buffer.create_tag(tag_name="monospace", family="Monospace")
    G.pgn_buffer.create_tag(tag_name="special", weight=pango.Weight.BOLD)
    G.pgn_buffer.create_tag(tag_name="book", underline=pango.Underline.SINGLE)
    G.pgn_buffer.create_tag(tag_name="comment", foreground="#009900")
    G.pgn_buffer.create_tag(tag_name="current", background="#9FCCFF")

    # Handle command line arguments
    if len(sys.argv) > 1:
        load_new_game_from_pgn_file(sys.argv[1])
    
    # Flip board if necessary
    if G.g.board().turn == chess.BLACK:
        G.board_flipped = True

    # Prepare repertoire and mark nodes
    try:
        G.rep = Repertoire("main.rep")
    except:
        pass
    mark_nodes(G.g.root())

GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, signal_handler, signal.SIGINT)
GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, signal_handler, signal.SIGTERM)

# Start
try:
    main()
except KeyboardInterrupt:
    signal_handler()
