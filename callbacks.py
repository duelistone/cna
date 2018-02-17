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
import signal, math, subprocess, sys, os, os.path
from functools import reduce
from opening_pgn import *
from mmrw import *
from engine import *
from drawing import *
from dfs import *
from pgn_visitor import game_gui_string

# Helper functions

def make_move(m):
    # Make the move if legal
    # Check if move already in tree first
    moves = map(lambda v: v.move, G.g.variations)
    if m in moves:
        G.g = G.g.variation(m)
        update_pgn_textview_move()
        return True
    elif m in G.g.board().legal_moves:
        G.g = G.g.add_main_variation(m)
        mark_nodes(G.g)
        update_pgn_message()
        return True
    return False

def mark_if_special(game):
    '''Assuming the 'player' only makes moves appearing in first variations,
    a node is special if it can be reached.'''
    game.special = False
    if game.is_main_variation() and (game.parent == None or game.parent.special):
        game.special = True # Root node
    elif game.board().turn == G.player:
        if game.parent.special:
            game.special = True

def mark_if_book(game):
    '''Checks if a game appears in the loaded opening repertoire.'''
    game.book = False
    if G.rep:
        if game.parent == None: game.book = True
        elif G.player == chess.WHITE and G.rep.hasPositionWhite(game.parent.board()) and game.move in G.rep.findMovesWhite(game.parent.board()): game.book = True
        elif G.player == chess.BLACK and G.rep.hasPositionBlack(game.parent.board()) and game.move in G.rep.findMovesBlack(game.parent.board()): game.book = True

def mark_nodes(game):
    '''Marks special and book nodes.'''
    # Check if special or book node
    mark_if_special(game)
    mark_if_book(game)

    # PGN order recursion
    children = game.variations
    num_children = len(game.variations)
    for i in range(1, num_children):
        mark_nodes(game.variation(i))
    if num_children > 0:
        mark_nodes(game.variation(0))

def save_special_nodes_to_repertoire(game):
    '''Adds new nodes beneath an input node into repertoire for
    the G.player side.'''
    # Select correct helper functions for each side
    findMoves = G.rep.findMovesWhite
    append = G.rep.appendWhite
    if G.player == chess.BLACK:
        findMoves = G.rep.findMovesBlack
        append = G.rep.appendBlack
    # Save position
    if game.parent != None:
        board = game.parent.board()
        move = game.move
        moveInBook = False
        for m in findMoves(board): # Checking if move in book
            if m == move:
                moveInBook = True
                break
        if not moveInBook: # If it isn't in the book, add it
            append(board, move)
    # Recursion
    for node in game.variations:
        if node.special:
            save_special_nodes_to_repertoire(node)

def display_status(s):
    G.status_bar.remove_all(G.status_bar_cid)
    G.status_bar.push(G.status_bar_cid, s)

def update_game_info():
    stringToDisplay = "%s vs %s, %s, %s, %s" % (G.g.root().headers["White"], G.g.root().headers["Black"], G.g.root().headers["Event"], G.g.root().headers["Site"], G.g.root().headers["Date"])
    display_status(stringToDisplay)

def display_variations():
    words = ["Variations:"]
    for child in G.g.variations:
        words.append(G.g.board().san(child.move))
    display_status(" ".join(words))

def delete_opening_node(color, game):
    # Cannot delete root node
    if game.parent == None: return

    # Get position and move to delete, and then delete
    board = game.parent.board()
    move = game.move
    if color == chess.WHITE:
        G.rep.removeWhite(board, move)
    else:
        G.rep.removeBlack(board, move)

def commonString(s, t):
    i = 0
    while i < len(s):
        if s[i] != t[i]:
            break
        i += 1
    return s[:i]

def tab_completion_callback(widget, event):
    if event.keyval == gdk.KEY_Tab:
        # Parse string so far
        text = widget.get_text()
        path, tail = os.path.split(text)
        try:
            candidates = list(filter(lambda x: x[0:len(tail)] == tail, os.listdir(path if path != '' else '.')))
        except:
            return True
        if len(candidates) == 1:
            widget.set_text(path + (os.sep if path != '' else '') + candidates[0])
            widget.set_position(-1)
        elif len(candidates) > 1:
            widget.set_text(path + (os.sep if path != '' else '') + reduce(commonString, candidates))
            widget.set_position(-1)
        return True
    return False

def prompt(parent, message, callback):
    # Widget definitions
    dialog = gtk.Dialog(title="Message", parent=parent, flags=0); # 0 is for DIALOG_DESTROY_WITH_PARENT
    content_area = dialog.get_content_area()
    label = gtk.Label(message)
    entry = gtk.Entry()

    # Callbacks
    entry.connect("activate", callback, dialog) # Note extra argument!
    entry.connect("key_press_event", tab_completion_callback)
    dialog.connect("response", lambda x, _: x.destroy())

    # Put it all together
    content_area.add(label)
    content_area.add(entry)
    dialog.show_all()

def commentPrompt(parent, message, callback, startingText=""):
    # Widget definitions
    dialog = gtk.Dialog(title="Message", parent=parent, flags=0); # 0 is for DIALOG_DESTROY_WITH_PARENT
    content_area = dialog.get_content_area()
    label = gtk.Label(message)
    entry = gtk.TextView()
    entry.set_size_request(300, 100)
    entry.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
    entry.get_buffer().set_text(startingText)

    # Callbacks
    entry.connect("key_press_event", callback, dialog)
    dialog.connect("response", lambda x, _: x.destroy())

    # Put it all together
    content_area.add(label)
    content_area.add(entry)
    dialog.show_all()

def board_coords_to_square(x, y):
    square_size = get_square_size(G.board_display)
    board_x = x // square_size
    board_y = y // square_size
    if not G.board_flipped:
        board_y = 7 - board_y
    else:
        board_x = 7 - board_x

    if int(board_x) >= 0 and int(board_y) >= 0 and int(board_x) < 8 and int(board_y) < 8:
        return chess.square(int(board_x), int(board_y))
    return None

def go_back():
    if G.g.parent:
        G.g = G.g.parent
    update_pgn_textview_move()

def go_forward():
    if len(G.g.variations) > 0:
        G.g = G.g.variation(0)
    update_pgn_textview_move()

def findFork(game):
    fork = game.parent
    transitionMove = game.move
    while len(fork.variations) <= 1 and fork != game.root():
        transitionMove = fork.move
        fork = fork.parent
    return fork, transitionMove

def load_new_game_from_board(board):
    new_game = chess.pgn.Game()
    try:
        new_game.setup(board)
        mark_nodes(new_game)
        G.games.append(new_game)
        G.currentGame += 1
        G.g = new_game
        G.player = board.turn
        G.board_flipped = False if G.player == chess.WHITE else True
        G.board_display.queue_draw()
        update_pgn_message()
    except:
        display_status("Unexpected error loading FEN.") # Errors caused by bad FEN should be handled elsewhere

def load_new_game_from_pgn_file(file_name):
    pgnFile = None
    movePath = []
    # Casework based on whether file_name is string or already opened file
    if type(file_name) == str:
        try:
            pgnFile = open(file_name, 'r', encoding='utf-8')
        except:
            # Display error in status bar
            stringToDisplay = "Error finding PGN file '%s'." % file_name
            display_status(stringToDisplay)
            return False
    else:
        pgnFile = file_name
    # Read game from pgn file
    if pgnFile != None:
        try:
            firstChar = pgnFile.read(1)
            if firstChar == '%':
                restOfLine = pgnFile.readline()
                movePath = map(int, restOfLine.split())
            else:
                pgnFile.seek(0)
            new_game = chess.pgn.read_game(pgnFile)
            mark_nodes(new_game)
        except:
            stringToDisplay = "Error loading PGN file '%s'." % file_name
            display_status(stringToDisplay)
            return False
        try:
            for m in movePath:
                new_game = new_game.variation(m)
        except:
            pass
        try:
            pgnFile.close()
        except:
            pass
    G.games.append(new_game)
    G.currentGame += 1
    G.g = new_game
    G.player = G.g.board().turn
    G.board_flipped = False if G.player == chess.WHITE else True
    update_pgn_message()
    return True

def update_pgn_textview_tags():
    if G.pgn_textview_enabled:
        veryStart = G.pgn_buffer.get_start_iter()
        veryEnd = G.pgn_buffer.get_end_iter()
        # Are these necessary?
        #G.pgn_buffer.remove_tag_by_name("special", veryStart, veryEnd)
        #G.pgn_buffer.remove_tag_by_name("book", veryStart, veryEnd)
        #G.pgn_buffer.remove_tag_by_name("comment", veryStart, veryEnd)
        G.pgn_buffer.apply_tag_by_name("monospace", veryStart, veryEnd)
        for start, end in G.specialRanges:
            start = G.pgn_buffer.get_iter_at_offset(start)
            end = G.pgn_buffer.get_iter_at_offset(end)
            G.pgn_buffer.apply_tag_by_name("special", start, end)
        for start, end in G.bookRanges:
            start = G.pgn_buffer.get_iter_at_offset(start)
            end = G.pgn_buffer.get_iter_at_offset(end)
            G.pgn_buffer.apply_tag_by_name("book", start, end)
        for start, end in G.commentRanges:
            start = G.pgn_buffer.get_iter_at_offset(start)
            end = G.pgn_buffer.get_iter_at_offset(end)
            G.pgn_buffer.apply_tag_by_name("comment", start, end)
        update_pgn_textview_move()
    
def update_pgn_message():
    if G.pgn_textview_enabled:
        # Do updating
        G.pgn_buffer.set_text(game_gui_string(G.g.root()))

        # Update text tags
        update_pgn_textview_tags()

def update_pgn_textview_move():
    if G.pgn_textview_enabled:
        G.pgn_buffer.remove_tag_by_name("current", G.pgn_buffer.get_start_iter(), G.pgn_buffer.get_end_iter())
        start, end = G.nodesToRanges[G.g]
        start = G.pgn_buffer.get_iter_at_offset(start)
        end = G.pgn_buffer.get_iter_at_offset(end)
        G.pgn_buffer.apply_tag_by_name("current", start, end)
        G.pgn_textview.scroll_to_iter(start, 0, False, 0.5, 0.5)

def execute_command():
    pass

def move_completion(s):
    sans = map(G.g.board().san, G.g.board().legal_moves)
    candidates = list(filter(lambda x: x[0:len(s)] == s, sans))
    if len(candidates) == 0:
        return s, ""
    if len(candidates) == 1:
        return candidates[0], ""
    # There are multiple candidates if we get here
    return s, " (%s)" % " ".join(candidates)

def command_completion(s):
    return s

# Decorator

def gui_callback(cb):
    G.handlers[cb.__name__] = cb
    return cb

# GUI callbacks

@gui_callback
def opening_save_callback(widget=None):
    if G.player == chess.BLACK:
        return opening_black_save_callback()
    else:
        return opening_white_save_callback()

@gui_callback
def opening_white_save_callback(widget=None):
    if G.rep:
        save_special_nodes_to_repertoire(G.g.root())
        G.rep.flush()
        mark_nodes(G.g.root())
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
def opening_black_save_callback(widget=None):
    if G.rep:
        save_special_nodes_to_repertoire(G.g.root())
        G.rep.flush()
        mark_nodes(G.g.root())
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
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

@gui_callback
def file_name_entry_callback(widget, dialog):
    G.controlPressed = False # Necessary since key release won't work since focus is moved to dialog
    G.save_file_name = widget.get_text()
    dialog.destroy()
    return False

@gui_callback
def load_fen_entry_callback(widget, dialog):
    fen_string = widget.get_text()
    G.selection.set_text(fen_string, -1) # To make already typed FEN retrievable if something goes wrong
    board = None
    try:
        board = chess.Board(fen_string)
    except ValueError:
        pass
    if board != None:
        # Load new game from board
        load_new_game_from_board(board)
        dialog.destroy()
        G.board_display.queue_draw()
    else:
        success = load_new_game_from_pgn_file(fen_string)
        if success:
            dialog.destroy()
            G.save_file_name = fen_string
        G.board_display.queue_draw()
    # TODO: Also allow pasted PGN and list of pieces
    return False

@gui_callback
def previous_game_callback(widget=None):
    if G.currentGame > 0:
        G.currentGame -= 1
        G.g = G.games[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
    return False

@gui_callback
def next_game_callback(widget=None):
    if G.currentGame < len(G.games) - 1:
        G.currentGame += 1
        G.g = G.games[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
    elif G.currentGame == len(G.games) - 1 and G.pgnFile != None:
        # Try to read next game, if not give up.
        try:
            load_new_game_from_pgn_file(G.pgnFile) # Already updates pgn message
        except:
            return
        G.board_display.queue_draw()

    return False

@gui_callback
def demote_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.demote(transitionMove)
        update_pgn_message()
    return False

@gui_callback
def promote_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote(transitionMove)
        update_pgn_message()
    return False

@gui_callback
def promote_to_main_callback(widget=None):
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote_to_main(transitionMove)
        update_pgn_message()
    return False

@gui_callback
def demote_to_last_callback(widget=None):
    # Is this even necessary?
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        for i in range(len(fork.variations) - 1):
            fork.demote(transitionMove)
        update_pgn_message()
    return False

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
    update_pgn_message()
    return False

@gui_callback
def opening_test_callback(widget=None):
    if G.rep:
        create_opening_game("currentTest.pgn", G.rep, G.player, G.g)
        subprocess.Popen(['ot', 'currentTest.pgn'])
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

    # Color light squares
    cr.set_line_width(0)
    for file in range(8):
        x = 7 - file if G.board_flipped else file
        for rank in range(7, -1, -1):
            y = 7 - rank if G.board_flipped else rank
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

            # Draw the piece, if there is one
            piece = G.g.board().piece_at(chess.square(x, y))
            if piece != None and (G.drag_source == G.NULL_SQUARE or chess.square(x, y) != G.drag_source):
                draw_piece(cr, piece, square_size)

            # Go to next rank
            cr.translate(0, square_size)

        # Go to next file
        cr.translate(square_size, -square_size * 8);

    # Draw little circle for side to move on bottom left
    margin = int(math.ceil(0.01 * square_size))
    radius = int(math.ceil(0.05 * square_size))
    centerCoord = margin + radius
    cr.restore()
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
        cr.identity_matrix()
        cr.translate(padding + G.mouse_x - square_size // 2, padding + G.mouse_y - square_size // 2)
        draw_piece(cr, G.g.board().piece_at(G.drag_source), square_size)

    return False

@gui_callback
def board_mouse_down_callback(widget, event):
    if event.button != 1:
        # TODO: Arrows, selection paste, other possibilities...
        return False

    clicked_square = board_coords_to_square(event.x, event.y)
    if clicked_square != None and G.g.board().piece_at(clicked_square) != None:
        G.drag_source = clicked_square

    return False

@gui_callback
def board_mouse_up_callback(widget, event):
    if G.drag_source == G.NULL_SQUARE:
        return False

    if event.button != 1:
        # TODO
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
        go_back()
    elif event.direction == gdk.ScrollDirection.DOWN:
        go_forward()
    G.board_display.queue_draw()
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
        mark_nodes(G.g.root())
        dialog.destroy()
    except:
        display_status("Error loading repertoire '%s'." % G.repertoire_file_name)
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

@gui_callback
def save_callback(widget=None, save_file_name=None, showStatus=True, prelude=None):
    if save_file_name == None:
        save_file_name = G.save_file_name
    outPgnFile = open(save_file_name, 'w')
    if prelude:
        print(prelude, file=outPgnFile)
    print(G.g.root(), file=outPgnFile, end="\n\n")
    outPgnFile.close()
    if showStatus:
        display_status("Game saved to %s." % save_file_name)
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
    subprocess.Popen(["python3", "gui.py", "game.temp"]) # Should eventually replace with 'at'
    return False

@gui_callback
def copy_fen_callback(widget=None):
    G.clipboard.set_text(G.g.board().fen(), -1)
    return False

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

    # Check if inputting move or command
    if G.inMove:
        completionString = ""
        if event.keyval in G.escapeKeys:
            G.inMove = False
            G.currentMove = ""
            display_status("")
            return False
        if event.keyval == gdk.KEY_Tab or event.keyval == gdk.KEY_Return:
            G.currentMove, completionString = move_completion(G.currentMove)
        elif event.keyval == gdk.KEY_BackSpace:
            G.currentMove = G.currentMove[:-1]
        else:
            c = gdk.keyval_name(event.keyval)
            if len(c) == 1 or c == "minus":
                if c == "minus":
                    c = '-'
                G.currentMove += c
        try:
            parsedMove = G.g.board().parse_san(G.currentMove)
            if parsedMove:
                make_move(parsedMove)
                G.board_display.queue_draw()
                display_status("")
                G.currentMove = ""
        except:
            pass
        display_status("Inputting move: %s%s" % (G.currentMove, completionString))
        return False
    elif G.inCommand:
        if event.keyval in G.escapeKeys:
            G.inCommand = False
            G.currentCommand = ""
            return False
        if event.keyval == gdk.KEY_Return:
            execute_command(G.currentCommand)
            G.currentCommand = ""
        elif event.keyval == gdk.KEY_BackSpace:
            G.currentCommand = G.currentCommand[:-1]
        elif event.keyval == gdk.KEY_Tab:
            G.currentCommand = command_completion(G.currentCommand)
        else:
            c = gdk.keyval_name(event.keyval)
            if c.isalnum():
                G.currentCommand += c
            display_status(":%s" % G.currentCommand)
        return False

    # Casework
    if event.keyval in [gdk.KEY_Control_L, gdk.KEY_Control_R]:
        G.controlPressed = True
    elif event.keyval == gdk.KEY_i:
        G.inMove = True
        display_status("Inputting move:")
    elif event.keyval == gdk.KEY_colon:
        G.inCommand = True
    elif event.keyval == gdk.KEY_space:
        play_move_callback()
    elif event.keyval == gdk.KEY_Escape:
        G.inCommand = False
        G.currentCommand = ""
        G.inMove = False
        G.currentMove = ""
    elif event.keyval == gdk.KEY_c:
        commentPrompt(G.window, "Edit comment:", comment_key_press_callback, G.g.comment)
    elif event.keyval == gdk.KEY_f:
        G.player = not G.player # TODO: Remove redundancy
        G.board_flipped = not G.board_flipped
        mark_nodes(G.g.root())
        update_pgn_message()
    elif event.keyval == gdk.KEY_g:
        G.g = G.g.root()
        update_pgn_textview_move()
    elif event.keyval == gdk.KEY_G:
        while len(G.g.variations) > 0:
            G.g = G.g.variation(0)
        update_pgn_textview_move()
    elif event.keyval == gdk.KEY_v:
        display_variations()
    elif event.keyval == gdk.KEY_Left or event.keyval == gdk.KEY_k:
        go_back()
    elif event.keyval == gdk.KEY_Right or event.keyval == gdk.KEY_j:
        go_forward()
    elif event.keyval == gdk.KEY_Down:
        demote_callback()
    elif event.keyval == gdk.KEY_Up:
        promote_callback()

    # Redraw board
    G.board_display.queue_draw()

    return False

# Other callbacks

def cleanup(showMessage=False):
    if G.stockfish != None:
        G.stockfish.process.process.send_signal(signal.SIGCONT) # In case stopped
        G.stockfish.terminate()
    if showMessage:
        print('Exiting gracefully.')

def destroy_main_window_callback(widget):
    '''Destroy main window callback. Provides cleanup code for things like stockfish, etc, as well.'''
    G.glib_mainloop.quit()
    cleanup(True)
    return False

def signal_handler(signum=None):
    '''Signal handling (SIGINT). Surprisingly, this doesn't need to do anything.'''
    cleanup(True)
    exit(0)
