# callbacks.py
'''Module for callbacks from GUI. These must also be registered
in the handlers dictionary in the global_variables module, which is done
automatically if you use the @gui_callback decorator defined below.'''

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango
from gi.repository import GLib
import global_variables as G
import signal, math, subprocess, sys, os, os.path, shutil, chess, chess.pgn, shlex
from functools import reduce
from helper import *
from opening_pgn import *
from mmrw import *
from engine import *
from drawing import *
from dfs import *
from rep_visitor import rep_visitor
from pgn_visitor import game_gui_string

# Decorators

def gui_callback(cb):
    G.handlers[cb.__name__] = cb
    return cb

# Decorators returning decorators!

def entry_callback(*strings):
    def result(cb):
        for s in strings:
            G.command_callbacks[s] = cb
        return cb
    return result

def key_callback(*keys):
    def result(cb):
        for k in keys:
            G.key_binding_map[k] = cb
        return cb
    return result

# GUI callbacks

@entry_callback("flip", "f")
@key_callback(gdk.KEY_f)
@gui_callback
def flip_callback(widget=None):
    # Flip board
    G.player = not G.player
    mark_nodes(G.g.root())
    update_pgn_message()
    G.board_display.queue_draw()
    return False

@key_callback(gdk.KEY_Left, gdk.KEY_k)
@gui_callback
def go_back_callback(widget=None):
    if G.g.parent:
        G.g = G.g.parent
    update_pgn_textview_move()
    G.board_display.queue_draw()
    return False

@key_callback(gdk.KEY_Right, gdk.KEY_j)
@gui_callback
def go_forward_callback(widget=None):
    if len(G.g.variations) > 0:
        G.g = G.g.variation(0)
    update_pgn_textview_move()
    G.board_display.queue_draw()
    return False

@key_callback(gdk.KEY_g, gdk.KEY_Home)
@gui_callback
def go_to_beginning_callback(widget=None):
    G.g = G.g.root()
    update_pgn_textview_move()
    G.board_display.queue_draw()
    return False

@key_callback(gdk.KEY_G, gdk.KEY_End)
@gui_callback
def go_to_end_callback(widget=None):
    if not G.inMove:
        while len(G.g.variations) > 0:
            G.g = G.g.variation(0)
        update_pgn_textview_move()
        G.board_display.queue_draw()
    return False
    
@key_callback(gdk.KEY_c)
@entry_callback("ec", "edit_comment")
@gui_callback
def add_comment_callback(widget=None):
    if not G.inMove:
        commentPrompt(G.window, "Edit comment:", comment_key_press_callback, G.g.comment)
    return False

@entry_callback("c", "comment", "set_comment")
def set_comment_callback(*args):
    G.g.comment = " ".join(args)
    update_pgn_message()
    return False

@entry_callback("add_last")
def add_last_callback(*args):
    G.new_move_mode = G.ADD_LAST_VARIATION
    return False

@entry_callback("add_first", "add_main")
def add_main_callback(*args):
    G.new_move_mode = G.ADD_MAIN_VARIATION
    return False

@gui_callback
def opening_games_callback(widget=None):
    games = G.rep.list_games(G.g.board())
    display_string = " ".join(games)
    display_status(display_string)
    return False

@entry_callback("save_opening")
@gui_callback
def opening_save_callback(widget=None):
    if G.rep:
        save_special_nodes_to_repertoire(G.g.root())
        G.rep.flush()
        mark_nodes(G.g.root())
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False

@entry_callback("save_opening_node")
@gui_callback
def opening_single_save_callback(widget=None):
    if G.rep:
        save_special_node_to_repertoire(G.g)
        G.rep.flush()
        mark_nodes(G.g.root())
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False    

@entry_callback("save_game_to_repertoire")
@gui_callback
def opening_save_game_callback(widget=None):
    if G.rep:
        G.rep.add_games([G.g.root()])
    else:
        display_status("No repertoire file loaded.")
    return False

@key_callback(gdk.KEY_o)
@entry_callback("o", "display_repertoire_moves")
@gui_callback
def display_repertoire_moves_callback(widget=None):
    if G.rep:
        words = ["Repertoire moves:"]
        board = G.g.board()
        for move in G.rep.findMoves(G.player, board):
            words.append(board.san(move))
        display_status(" ".join(words))
    else:
        display_status("No repertoire loaded.")
    return True

@key_callback(gdk.KEY_v)
@entry_callback("v", "display_variations")
@gui_callback
def display_variations_callback(widget=None):
    words = ["Variations:"]
    for child in G.g.variations:
        words.append(G.g.board().san(child.move))
    display_status(" ".join(words))
    return False

@gui_callback
def queen_promotion_callback(widget=None):
    G.promotion_piece = chess.QUEEN
    return False

@gui_callback
def rook_promotion_callback(widget=None):
    G.promotion_piece = chess.ROOK
    return False

@gui_callback
def bishop_promotion_callback(widget=None):
    G.promotion_piece = chess.BISHOP
    return False

@gui_callback
def knight_promotion_callback(widget=None):
    G.promotion_piece = chess.KNIGHT
    return False

@gui_callback
def reload_callback(widget=None):
    update_game_info() # Should be replaced by more useful functionality
    return False

@gui_callback
def save_file_name_callback(widget=None):
    G.controlPressed = False # Necessary since key release won't work since focus is moved to dialog
    promptMessage = "Enter path to save file. This does not save the file!"
    prompt(G.window, promptMessage, file_name_entry_callback)
    return False

@entry_callback("save_file_name")
@gui_callback
def file_name_entry_callback(widget, dialog=None):
    G.controlPressed = False # Necessary since key release won't work since focus is moved to dialog
    G.save_file_name = widget.get_text() if type(widget) != str else widget
    G.save_file_names[G.currentGame] = G.save_file_name
    if dialog != None: dialog.destroy()
    return False

@entry_callback("load", "l")
@gui_callback
def load_fen_entry_callback(widget, dialog=None):
    if type(widget) != str:
        # widget is actually a widget
        fen_string = widget.get_text()
        G.selection.set_text(fen_string, -1) # To make already typed FEN retrievable if something goes wrong
    else:
        # Entry bar version, widget is the string representing what should be loaded
        fen_string = widget
    if load_new_game_from_pgn_file(fen_string) or load_new_game_from_fen(fen_string) or load_new_game_from_piece_list(fen_string) or load_new_game_from_pgn_string(fen_string):
        if dialog: dialog.destroy()
        display_status("Loaded %s" % fen_string)
    G.board_display.queue_draw()
    return False

def load_new_game_from_piece_list(piece_list_string):
    words = piece_list_string.split()
    isWhiteMarker = lambda x : x in ["W:", "w:", "W", "w"]
    isBlackMarker = lambda x : x in ["B:", "b:", "B", "b"]

    # Determine turn
    turn = chess.WHITE
    if len(words) > 0 and isBlackMarker(words[-1]):
            turn = chess.BLACK
    words = words[:-1]

    # Get pieces
    if len(words) < 1 and not isWhiteMarker(words[0]):
        return False
    i = 1
    whitePieces = []
    blackPieces = []
    currentList = whitePieces
    while i < len(words):
        if isBlackMarker(words[i]):
            currentList = blackPieces
            i += 1
            continue

        # Get square
        try:
            square = chess.SQUARE_NAMES.index(words[i][-2:])
            if len(words[i]) == 2:
                piece_type = chess.PAWN
            else:
                piece_type = [None, None, 'N', 'B', 'R', 'Q', 'K'].index(words[i][0])
            currentList.append((piece_type, square))
        except:
            return False

        i += 1

    # Place pieces
    board = chess.Board(fen=None)
    board.turn = turn
    for pt, sq in whitePieces:
        p = chess.Piece(pt, chess.WHITE)
        board.set_piece_at(sq, p)
    for pt, sq in blackPieces:
        p = chess.Piece(pt, chess.BLACK)
        board.set_piece_at(sq, p)

    # Load game
    try:
        game = chess.pgn.Game()
        game.setup(board)
        load_new_game_from_game(game)
    except:
        return False

    return True

def load_new_game_from_pgn_string(pgn_string):
    pgnFile = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgnFile)
    if game != None:
        load_new_game_from_game(game)
        return True
    else:
        return False

@entry_callback("clear_arrows")
@gui_callback
def clear_arrows_callback(*args):
    G.arrows.clear()
    G.board_display.queue_draw()
    return True

@entry_callback("sh", "header", "set_header")
def set_header_callback(*args):
    if len(args) < 2:
        update_pgn_message()
        return False
    G.g.root().headers[args[0]] = args[1]
    return set_header_callback(args[2:])

@entry_callback("nag", "add_nag", "set_nag")
def set_nag_callback(*args):
    errors = []
    for s in args:
        nag_number = None
        try:
            nag_number = G.nag_strings.index(s)
        except ValueError:
            try:
                nag_number = G.nag_names.index(s)
            except ValueError:
                errors.append(s)
        if nag_number:
            G.g.nags.add(nag_number)
    if len(errors) > 0:
        display_status("Could not understand these nags: " + str(errors))
    if len(errors) < len(args):
        update_pgn_message()
    return False

@entry_callback("remove_nags")
def remove_nags_callback():
    if len(G.g.nags) > 0:
        G.g.nags.clear()
        update_pgn_message()
    return False
        
@gui_callback
def header_entry_callback(widget, dialog, entries):
    if len(entries) < 2:
        # Error...incorrect number of entries
        # Ignore for now
        return False
    entries = map(lambda x: x.get_text(), entries)
    set_header_callback(*entries)
    dialog.destroy()
    update_pgn_message()
    return False

@gui_callback
def header_set_callback(widget=None):
    G.controlPressed = False
    messages = ["Tag name (defaults: Event, Site, Date, Round, White, Black, Result)", "Value"]
    multiPrompt(G.window, messages, header_entry_callback)
    return False

@gui_callback
def previous_game_callback(widget=None):
    if G.currentGame > 0:
        G.currentGame -= 1
        G.g = G.games[G.currentGame]
        G.save_file_name = G.save_file_names[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
        update_game_info()
    return False

@gui_callback
def next_game_callback(widget=None):
    if G.currentGame < len(G.games) - 1:
        G.currentGame += 1
        G.g = G.games[G.currentGame]
        G.save_file_name = G.save_file_names[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
        update_game_info()
    elif G.currentGame == len(G.games) - 1 and G.pgnFile != None:
        # Try to read next game, if not give up.
        success = load_new_game_from_pgn_file(G.pgnFile) # Already updates pgn message
        if not success: return False
        G.board_display.queue_draw()

    return False

@key_callback(gdk.KEY_Down)
@gui_callback
def demote_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.demote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@key_callback(gdk.KEY_Up)
@gui_callback
def promote_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
def promote_to_main_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote_to_main(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
def demote_to_last_callback(widget=None):
    # Is this even necessary?
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        for i in range(len(fork.variations) - 1):
            fork.demote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@key_callback(gdk.KEY_Delete)
@entry_callback("delete_children")
@gui_callback
def delete_children_callback(widget=None):
    # If there are children, delete those
    if len(G.g.variations) > 0:
        for var in G.g.variations:
            G.g.remove_variation(var.move)
    elif G.g.parent != None: # Can't delete root node
        # Delete current child-less node
        var = G.g
        G.g = G.g.parent
        G.g.remove_variation(var.move)
        G.board_display.queue_draw()
    mark_nodes(G.g.root())
    update_pgn_message()
    return False

@entry_callback("delete_nonspecial_nodes")
@gui_callback
def delete_nonspecial_nodes_callback(widget=None):
    # Opens new game with just special nodes
    game = copy_game(G.g.root(), lambda node : node.special)
    load_new_game_from_game(game)
    return False
    
@gui_callback
def opening_test_callback(widget=None):
    if G.rep:
        create_opening_game("currentTest.pgn", G.rep, G.player, G.g)
        #subprocess.Popen(['ot', 'currentTest.pgn'])
        if G.player == chess.WHITE:
            subprocess.Popen(['python3', 'gui.py', '--ot', G.g.board().fen()])
        else:
            subprocess.Popen(['python3', 'gui.py', '-b', '--ot', G.g.board().fen()])
    else:
        display_status("No repertoire file loaded.")
    return False 

@gui_callback
def board_draw_callback(widget, cr):
    '''Main drawing callback function.'''
    # Following original C chessboard implementation very closely
    square_size = get_square_size(widget)
    leftover_space = widget.get_allocated_width() - square_size * 8;
    padding = leftover_space // 2
    cr.translate(padding, padding);
    cr.save()

    cr.set_line_width(0)
    for file in range(8):
        x = 7 - file if G.player == chess.BLACK else file
        for rank in range(7, -1, -1):
            y = 7 - rank if G.player == chess.BLACK else rank
            square = chess.square(x, y)

            # Color light/dark squares
            if (x + y) % 2 == 0:
                # Dark squares
                cr.set_source_rgb(0.450980, 0.53725, 0.713725)
                cr.rectangle(0, 0, square_size, square_size)
                cr.fill()
            else:
                # Light squares
                cr.set_source_rgb(0.952941, 0.952941, 0.952941)
                cr.rectangle(0, 0, square_size, square_size)
                cr.fill()

            # Highlight square if necessary
            if (square, square) in G.arrows:
                highlight_square(cr, square_size)

            # Draw the piece, if there is one
            piece = G.g.board().piece_at(square)
            if piece != None and (G.drag_source == G.NULL_SQUARE or chess.square(x, y) != G.drag_source):
                draw_piece(cr, piece, square_size)

            # Go to next rank
            cr.translate(0, square_size)

        # Go to next file
        cr.translate(square_size, -square_size * 8);

    cr.restore()

    # Draw arrows
    for e in G.arrows:
        if e[0] == e[1]: continue # These are the highlighted squares, already done
        draw_arrow(cr, square_size, e[0], e[1])
    
    # Draw little circle for side to move on bottom left
    margin = int(math.ceil(0.01 * square_size))
    radius = int(math.ceil(0.05 * square_size))
    centerCoord = margin + radius
    cr.save()
    cr.translate(centerCoord, 8 * square_size - centerCoord) # To get bottom left
    if G.g.board().turn == chess.WHITE:
        cr.set_source_rgb(1, 1, 1)
    else:
        cr.set_source_rgb(0, 0, 0)
    cr.arc(0, 0, radius, 0, 2 * math.pi)
    cr.fill()
    cr.restore()

    # Dragging pieces
    if G.drag_source != G.NULL_SQUARE:
        cr.save()
        cr.identity_matrix()
        cr.translate(padding + G.mouse_x - square_size // 2, padding + G.mouse_y - square_size // 2)
        draw_piece(cr, G.g.board().piece_at(G.drag_source), square_size)
        cr.restore()

    return False

@gui_callback
def board_mouse_down_callback(widget, event):
    if event.button not in [1, 3]:
        return False

    clicked_square = board_coords_to_square(event.x, event.y)
    if clicked_square != None:
        if event.button == 1 and G.g.board().piece_at(clicked_square) != None:
            G.drag_source = clicked_square
        elif event.button == 3:
            G.arrow_source = clicked_square
        wx, wy = G.board_display.translate_coordinates(G.board_display.get_toplevel(), 0, 0)
        G.mouse_x = event.x + wx
        G.mouse_y = event.y + wy

    # Remove focus from entry bar
    G.board_display.grab_focus()

    return False

@gui_callback
def board_mouse_up_callback(widget, event):
    if event.button == 3:
        if G.arrow_source == G.NULL_SQUARE:
            return False

        arrow_target = board_coords_to_square(event.x, event.y)
        
        if arrow_target != None and G.arrow_source != None:
            elem = (G.arrow_source, arrow_target)
            if elem in G.arrows:
                G.arrows.remove(elem)
            else:
                G.arrows.add(elem)

        G.arrow_source = G.NULL_SQUARE
        G.board_display.queue_draw()
        return False

    if event.button != 1 or G.drag_source == G.NULL_SQUARE:
        return False

    drag_target = board_coords_to_square(event.x, event.y)
    
    if drag_target != None and G.drag_source != None:
        m = chess.Move(G.drag_source, drag_target)
        if not make_move(m):
            # Try promotion
            m = chess.Move(G.drag_source, drag_target, promotion=G.promotion_piece)
            make_move(m)

    G.drag_source = G.NULL_SQUARE
    G.board_display.queue_draw()

    return False

@gui_callback
def board_mouse_move_callback(widget, event):
    if G.drag_source != G.NULL_SQUARE:
        wx, wy = G.board_display.translate_coordinates(G.board_display.get_toplevel(), 0, 0)
        G.mouse_x = event.x + wx
        G.mouse_y = event.y + wy
        G.board_display.queue_draw()
    return False

@gui_callback
def board_scroll_event_callback(widget, event):
    if event.direction == gdk.ScrollDirection.UP:
        go_back_callback()
    elif event.direction == gdk.ScrollDirection.DOWN:
        go_forward_callback()
    return False

@gui_callback
def repertoire_name_entry_callback(widget, dialog):
    G.repertoire_file_name = widget.get_text()
    try:
        rep2 = Repertoire(G.repertoire_file_name)
        if G.rep:
            G.rep.flush()
            G.rep.close()
        G.rep = rep2
        dialog.destroy()
    except:
        display_status("Error loading repertoire '%s'." % G.repertoire_file_name)
    mark_nodes(G.g.root())
    update_pgn_message()
    return False

@gui_callback
def load_repertoire_callback(widget=None):
    G.controlPressed = False # Necessary since key release won't work since focus is moved to dialog
    prompt(G.window, "Enter repertoire name:", repertoire_name_entry_callback)
    return False

@gui_callback
def opening_size_callback(widget=None):
    if G.rep:
        opening_game = create_opening_game('currentTest.pgn', G.rep, G.player, G.g)
        count = countNodes(opening_game, color=G.player)
        count -= G.g.board().fullmove_number - 1
        display_status("Opening size: %d" % count)
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
def delete_opening_node_callback(widget=None):
    if G.rep:
        if G.player == chess.WHITE:
            delete_opening_node(chess.WHITE, G.g)
        else:
            delete_opening_node(chess.BLACK, G.g)
        G.rep.flush()
        mark_if_book(G.g)
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False

@entry_callback("save")
@gui_callback
def save_callback(widget=None, save_file_name=None, showStatus=True, prelude=None):
    if type(widget) == str:
        # Allows first argument to also set save file name (for entry save command)
        G.save_file_name = widget
        G.save_file_names[G.currentGame] = G.save_file_name
        save_file_name = G.save_file_name
        # Ignore more than one argument in entry
        showStatus = True
        prelude = None
    elif save_file_name == None:
        # Do not set global save_file_name if keyword arg is used
        save_file_name = G.save_file_name
    outPgnFile = open(G.save_file_name, 'w')
    if prelude:
        print(prelude, file=outPgnFile)
    print(G.g.root(), file=outPgnFile, end="\n\n")
    outPgnFile.close()
    if showStatus:
        display_status("Game saved to %s." % G.save_file_name)
    return False

@gui_callback
def open_pgn_textview_callback(widget=None):
    if G.pgn_textview_enabled:
        G.board_h_box.remove(G.scrolled_window)
    else:
        G.board_h_box.pack_end(G.scrolled_window, True, True, 0)
        G.board_h_box.show_all()
    G.pgn_textview_enabled = not G.pgn_textview_enabled
    update_pgn_message()
    return False

@gui_callback
def analyze_callback(widget=None):
    movePath = []
    node = G.g
    while node.parent != None:
        movePath.append(node.parent.variations.index(node))
        node = node.parent
    movePath.reverse()
    prelude = '%' + " ".join(map(str, movePath))
    save_callback(G.g.root(), save_file_name="game.temp", showStatus=False, prelude=prelude)
    # Should eventually replace with 'at' script or with memorized command line arguments
    # Issue currently is that this does not keep current command line arguments like a tablebases folder
    subprocess.Popen(["python3", "gui.py", "game.temp"]) 
    return False

@gui_callback
def copy_fen_callback(widget=None):
    G.clipboard.set_text(G.g.board().fen(), -1)
    return False

@key_callback(gdk.KEY_e)
@gui_callback
def toggle_stockfish_callback(widget=None):
    if G.stockfish == None:
        # Start up stockfish
        G.stockfish = engine_init()
        G.stockfish.info_handlers[0].curr_pos = G.g.board()
        G.stockfish_enabled = True
        G.stockfish_textview.show_all()
        engine_go(G.stockfish)
        return False

    if G.stockfish_enabled:
        # Turn stockfish off
        G.stockfish.process.process.send_signal(signal.SIGSTOP)
        G.stockfish_textview.hide()
        G.stockfish_enabled = False
    else:
        # Turn stockfish on
        G.stockfish.process.process.send_signal(signal.SIGCONT)
        new_board = G.g.board()
        if new_board != G.stockfish.info_handlers[0].curr_pos:
            G.stockfish.stop()
            G.stockfish.info_handlers[0].curr_pos = G.g.board()
            engine_go(G.stockfish)
        G.stockfish_textview.show_all()
        G.stockfish_enabled = True

    return False

@gui_callback
def set_multipv_1_callback(widget=None):
    change_multipv(1)
    if G.stockfish_enabled:
        engine_go(G.stockfish)

@gui_callback
def set_multipv_2_callback(widget=None):
    change_multipv(2)
    if G.stockfish_enabled:
        engine_go(G.stockfish)

@gui_callback
def set_multipv_3_callback(widget=None):
    change_multipv(3)
    if G.stockfish_enabled:
        engine_go(G.stockfish)

@gui_callback
def set_multipv_4_callback(widget=None):
    change_multipv(4)
    if G.stockfish_enabled:
        engine_go(G.stockfish)

@gui_callback
def set_multipv_5_callback(widget=None):
    change_multipv(5)
    if G.stockfish_enabled:
        engine_go(G.stockfish)

@key_callback(gdk.KEY_space)
@entry_callback("play_move")
@gui_callback
def play_move_callback(widget=None):
    if G.stockfish_enabled:
        if G.stockfish.info_handlers[0].curr_pos == G.g.board():
            try:
                move = find_current_best_move(G.stockfish)
                make_move(move)
                # Start analyzing new position
                toggle_stockfish_callback()
                toggle_stockfish_callback()
            except:
                pass
                display_status("Error finding move.")
        else:
            display_status("Cannot play engine move: engine currently analyzing a different position.")
    else:
        # TODO: Play without showing analysis
        # Use G.playLevel
        if type(G.playLevel) == type(0):
            # Use depth
            pass
        else:
            # Use time
            pass
    return False

@gui_callback
def load_fen_callback(widget=None):
    G.controlPressed = False # Necessary since key release won't work since focus is moved to dialog
    promptMessage = "Enter FEN or path to PGN file"
    prompt(G.window, promptMessage, load_fen_entry_callback)
    return False

@gui_callback
def make_report_callback(widget=None):
    make_report()
    return False

@gui_callback
def textview_mouse_pressed_callback(widget, event):
    text_window = gtk.TextWindowType.WIDGET
    pressed_tuple = widget.window_to_buffer_coords(text_window, event.x, event.y)
    G.textview_pressed_text_iter = G.pgn_textview.get_iter_at_location(pressed_tuple[0], pressed_tuple[1])[1] # Yeah...the [1] is necessary, which is ridiculous
    G.textview_pressed_text_iter.backward_char()
    if not G.textview_pressed_text_iter.starts_word() and G.textview_pressed_text_iter.inside_word():
        G.textview_pressed_text_iter.backward_word_start()
    return False

@gui_callback
def textview_mouse_released_callback(widget, event):
    if G.textview_pressed_text_iter != None:
        text_window = gtk.TextWindowType.WIDGET
        released_tuple = widget.window_to_buffer_coords(text_window, event.x, event.y)
        text_iter = G.pgn_textview.get_iter_at_location(released_tuple[0], released_tuple[1])[1] # Yeah...the [1] is necessary, which is ridiculous
        text_iter.backward_char()
        if not text_iter.starts_word() and text_iter.inside_word():
            text_iter.backward_word_start()
        if G.textview_pressed_text_iter.equal(text_iter): # The == operator isn't overloaded
            try:
                G.g = G.bufferToNodes[text_iter.get_offset()]
                update_pgn_textview_move()
            except KeyError:
                pass
            G.board_display.queue_draw()
    G.textview_pressed_text_iter = None
    return False

@gui_callback
def pgn_textview_key_press_callback(widget, event):
    return True

@gui_callback
def entry_bar_callback(widget):
    text = widget.get_text()
    args = shlex.split(text)

    # Save in history
    if len(args) > 0:
        G.command_history.append(text)

    while len(args) > 0:
        # Try to parse moves
        move = None
        try:
            move = G.g.board().parse_san(args[0])
        except ValueError:
            pass

        if move:
            # Legal move given
            make_move(move)
            G.board_display.queue_draw()
            widget.set_text("")
            G.command_index = 0
            del args[0]
        else:
            # Command given
            if args[0] in G.command_callbacks:
                G.command_callbacks[args[0]](*args[1:])
                widget.set_text("")
                G.command_index = 0
            break
        
    return False

@gui_callback
def entry_bar_key_press_callback(widget, event):
    # Autocomplete
    if event.keyval == gdk.KEY_Tab:
        text = widget.get_text()
        words = shlex.split(text)
        if len(words) == 1:
            # Command completion
            partial = words[0]
            if partial != "":
                matches = []
                moves = map(lambda m: G.g.board().san(m), G.g.board().legal_moves)
                for command in G.command_callbacks:
                    if partial == command[:len(partial)]:
                        matches.append(command)
                for command in moves:
                    if partial == command[:len(partial)]:
                        matches.append(command)
                if len(matches) > 0:
                    display_status(", ".join(matches))
                    new_entry_string = reduce(commonString, matches)
                    widget.set_text(new_entry_string)
                    widget.set_position(-1)
                else:
                    display_status("No matches for %s." % partial)
        elif len(words) > 1:
            # Other type of completion
            # For now, we'll just assume this should be file completion or NAG completion
            partial = words[-1]
            prev = " ".join(words[:-1]) + " "
            path, tail = os.path.split(partial)
            try:
                candidates = list(filter(lambda x: x[0:len(tail)] == tail, os.listdir(path if path != '' else '.')))
            except:
                return True
            candidates += list(filter(lambda x : x[0:len(tail)] == tail, G.nag_set))
            if len(candidates) > 0:
                widget.set_text(prev + path + (os.sep if path != '' else '') + reduce(commonString, candidates))
                display_status(", ".join(candidates))
                widget.set_position(-1)
        return True

    # Scroll through history
    if event.keyval == gdk.KEY_Up:
        if -G.command_index < len(G.command_history):
            G.command_index -= 1
            widget.set_text(G.command_history[G.command_index])
        return True
    if event.keyval == gdk.KEY_Down:
        if G.command_index < 0:
            G.command_index += 1
            if G.command_index < 0:
                widget.set_text(G.command_history[G.command_index])
            else:
                widget.set_text("")
        return True

    return False
    
@gui_callback
def key_release_callback(widget, event):
    if event.keyval in [gdk.KEY_Control_L, gdk.KEY_Control_R]:
        G.controlPressed = False
    return False

def comment_key_press_callback(widget, event, dialog=None):
    if event.keyval == gdk.KEY_Return:
        buff = widget.get_buffer()
        G.g.comment = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), True)
        update_pgn_message()
        if dialog:
            dialog.destroy()
        return True
    return False

@gui_callback
def key_press_callback(widget, event):
    # Check for modifier keys
    if G.controlPressed:
        return False

    # Set controlPressed flag if necessary
    if event.keyval in [gdk.KEY_Control_L, gdk.KEY_Control_R]:
        G.controlPressed = True

    # Return focus outside of entry
    if event.keyval in G.escapeKeys:
        G.board_display.grab_focus()
        return False
    
    # Check if focus is on entry bar
    if G.entry_bar.is_focus():
        return False

    # Unorganized callbacks
    if event.keyval == gdk.KEY_t:
        # Play engine in training mode
        if G.weak_stockfish == None:
            G.weak_stockfish = weak_engine_init(G.WEAK_STOCKFISH_DEFAULT_LEVEL)
        while 1:
            G.weak_stockfish.position(G.g.board())
            best, _ = G.weak_stockfish.go(movetime=1000)
            score = G.weak_stockfish.info_handlers[0].e
            if score.cp != None:
                correctLevel = score_to_level(score.cp, G.WEAK_STOCKFISH_DEFAULT_LEVEL)
                if correctLevel == G.weak_stockfish.level:
                    break
                change_level(G.weak_stockfish, correctLevel)
            else:
                # If a mate was found, we don't care about the level right now
                break
        print("Current level: %s" % G.weak_stockfish.level)
        make_move(best)
        G.board_display.queue_draw()
        return True

    # Organized callbacks
    if event.keyval in G.key_binding_map:
        G.key_binding_map[event.keyval]()
        return True

    return False

# Other callbacks

def ot_move_completed_callback(answer):
    # Currying
    def f(guess):
        if guess.from_square == answer.from_square and guess.to_square == answer.to_square and guess.promotion == answer.promotion:
            ot_correct_answer_callback()
        else:
            go_back_callback()
    return f

def ot_correct_answer_callback():
    # Load generator if first time
    if G.ot_gen == None and G.ot_board != None:
        G.ot_gen = rep_visitor(G.ot_board, G.player)

    # Get next position
    try:
        b, m = next(G.ot_gen)
    except StopIteration:
        display_status("Training complete!")
        G.move_completed_callback = ot_move_completed_callback(chess.Move.null())
        return

    # Set new answer + callback, and load new board
    G.move_completed_callback = ot_move_completed_callback(m) # This is a function
    load_new_game_from_board(b)
    
def destroy_main_window_callback(widget):
    '''Destroy main window callback. Provides cleanup code for things like stockfish, etc, as well.'''
    G.glib_mainloop.quit()
    cleanup(True)
    return False

def signal_handler(signum=None):
    '''Signal handling (SIGINT). Surprisingly, this doesn't need to do anything.'''
    cleanup(True)
    exit(0)
