import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.pgn, chess.polyglot, sys, subprocess, time, os, os.path, random, re, signal, threading, unicodedata, cairo, threading
import global_variables as G
from chess_tools import *
from opening_pgn import *
from mmrw import *
from dfs import *
from drawing import *
from callbacks import *
from lichess_helpers import *
from help_helpers import *
from engine import *
from shortcut_loader import load_shortcuts_from_config_file
from command_line_arguments import cla_parser
from menu_items import MenuNode
from json_loader import CallbackConfigManager

def main():
    # Change directory to application directory
    if G.base_directory != "": 
        os.chdir(G.base_directory)

    # Load images and GUI elements
    load_svgs("pieces/merida/")
    builder = gtk.Builder()
    builder.add_from_file("chessboard.ui")
    builder.connect_signals(G.handlers)

    # Parse command line arguments
    parser = cla_parser(sys.argv)
    parser.register("--tb", 1)
    parser.register("--config", 1)
    parser.register("--sr", 0, 2)
    parser.register("-h", 0, 2)
    parser.register("-b", 0, 2)
    parser.register("--ot", -1, 9)
    parser.register("--tt", -1, 9)
    parser.parse()

    # Determine player color
    if '-b' in parser:
        G.player = chess.BLACK

    # TODO: Add engine config to fill in G.engine_settings
    # And SyzygyPath? Or is that part of a general config file?
    # Speaking of which, should also have general config for global constants

    # Get tablebase path
    tb_args = parser.args_for_keyword("--tb", enforce_num_args=True)
    if tb_args != None:
        for e in G.engine_settings:
            G.engine_settings[e].update({"SyzygyPath": tb_args[0]})
        G.tablebase = chess.syzygy.open_tablebase(tb_args[0])

    # Check if should use opening test or learn mode and finish preperations
    useOpeningMode = '--ot' in parser
    useTacticsMode = '--tt' in parser
    useLearningMode = '--sr' in parser # Still needs to have '--ot' or '--tt' as well, for now
    if useLearningMode and not (useOpeningMode or useTacticsMode):
        print("Incorrect usage. Cannot practice spaced repetition without ot mode.", file=sys.stderr)
        exit(1)
    if useOpeningMode and useTacticsMode:
        print("Incorrect usage. Cannot practice both opening and tactics.", file=sys.stderr)
    if useOpeningMode or useTacticsMode:
        fenString = " ".join(parser.args_for_keyword("--ot")) if useOpeningMode else " ".join(parser.args_for_keyword("--tt"))
        try:
            G.ot_board = chess.Board(fen=fenString)
        except ValueError:
            G.ot_board = chess.Board() if useOpeningMode else None
        preparations(builder)
        setup_ot_mode(only_sr=useLearningMode, visitor=rep_visitor if useOpeningMode else tactics_visitor)
    else:
        preparations(builder)

    if len(parser.get_leftover_args()) > 0:
        load_new_game_from_pgn_file(parser.get_leftover_args()[0])

    # Read and parse config file
    config_args = parser.args_for_keyword("--config", enforce_num_args=True)
    if config_args == None:
        config_file = G.DEFAULT_CONFIG_FILENAME
    else:
        config_file = config_args[0]
    try:
        config_manager = CallbackConfigManager(G.handlers)
        config_manager.load_json_from_file(config_file)
    except FileNotFoundError:
        if config_file == G.DEFAULT_CONFIG_FILENAME:
            print("%s file not found, setting up default shortcuts" % G.DEFAULT_CONFIG_FILENAME, file=sys.stderr)
            os.system("cp default_shortcuts.json %s" % G.DEFAULT_CONFIG_FILENAME)
            load_shortcuts_from_config_file(G.DEFAULT_CONFIG_FILENAME)
        else:
            print("Config file not found. Exiting.")
            sys.exit(1)

    # Add entry and keyboard shortcuts
    config_manager.load_entry_shortcuts(G.command_callbacks)
    config_manager.load_keyboard_shortcuts(G.key_binding_maps)

    # Prepare main menu
    menu_root = MenuNode()
    config_manager.load_menu_items(menu_root)
    menu_root.insert(G.big_box)


    # Help?
    if '-h' in parser:
        print(full_help_report())
        exit(0)

    # Show elements
    G.window.show_all()
    G.stockfish_textview.hide()

    # Autosave thread
    autosave_thread = threading.Thread(target=autosave, daemon=True)
    autosave_thread.start()

    # asyncio threads
    G.engines = list(map(AnalysisEngine, G.engine_commands))
    for e in G.engines:
        threading.Thread(target=lambda : asyncio.run(e.async_init()), daemon=True).start()
    threading.Thread(target=lambda : asyncio.run(weak_engine_init()), daemon=True).start()

    # Start main loop
    G.glib_mainloop.run()

def preparations(builder):
    # Widget extraction
    G.window = builder.get_object("main_window")
    G.big_box = builder.get_object("big_box")
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

    # Make status bar selectable 
    for elem in G.status_bar.get_message_area():
        elem.set_selectable(True)

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
    G.stockfish_textview.connect("button-press-event", engine_textview_mouse_down_callback)

    # PGN textview tags
    G.pgn_buffer.create_tag(tag_name="monospace", family="Monospace")
    G.pgn_buffer.create_tag(tag_name="special", weight=pango.Weight.BOLD)
    G.pgn_buffer.create_tag(tag_name="book", underline=pango.Underline.SINGLE)
    G.pgn_buffer.create_tag(tag_name="learn", style=pango.Style.ITALIC)
    G.pgn_buffer.create_tag(tag_name="comment", foreground="#009900")
    G.pgn_buffer.create_tag(tag_name="current", background="#9FCCFF")

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
