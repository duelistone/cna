# helper.py

# Helper functions, mainly for callbacks.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango
from gi.repository import GLib
import global_variables as G
import signal, math, subprocess, sys, os, os.path, shutil, chess, chess.pgn, shlex
from functools import reduce
from opening_pgn import *
from mmrw import *
from engine import *
from drawing import *
from dfs import *
from rep_visitor import rep_visitor
from pgn_visitor import game_gui_string

def make_move(m):
    # Make the move if legal
    # Check if move already in tree first
    moves = map(lambda v: v.move, G.g.variations)
    if m in moves:
        G.g = G.g.variation(m)
        update_pgn_textview_move()
        G.move_completed_callback(m)
        return True
    elif m in G.g.board().legal_moves:
        if G.new_move_mode == G.ADD_MAIN_VARIATION:
            G.g = G.g.add_main_variation(m)
        elif G.new_move_mode == G.ADD_LAST_VARIATION:
            G.g = G.g.add_variation(m)
        mark_nodes(G.g.root())
        update_pgn_message()
        G.move_completed_callback(m)
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

def save_special_node_to_repertoire(game):
    '''Adds new node into repertoire for G.player side.'''
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

def save_special_nodes_to_repertoire(game):
    '''Adds new nodes beneath an input node into repertoire for
    the G.player side.'''
    save_special_node_to_repertoire(game)
    # Recursion
    for node in game.variations:
        if node.special:
            save_special_nodes_to_repertoire(node)

def display_status(s):
    G.status_bar.remove_all(G.status_bar_cid)
    G.status_bar.push(G.status_bar_cid, s)

def update_game_info():
    stringToDisplay = "%s vs %s, %s, %s, %s, %s" % (G.g.root().headers["White"], G.g.root().headers["Black"], G.g.root().headers["Event"], G.g.root().headers["Site"], G.g.root().headers["Date"], G.g.root().headers["Result"])
    display_status(stringToDisplay)

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
    while i < len(s) and i < len(t):
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

def multiPrompt(parent, messages, callback):
    '''An extension of a prompt with n entries.'''
    # Widget definitions
    dialog = gtk.Dialog(title="Message", parent=parent, flags=0); # 0 is for DIALOG_DESTROY_WITH_PARENT
    content_area = dialog.get_content_area()
    labels = []
    entries = []
    for message in messages: 
        labels.append(gtk.Label(message))
        entries.append(gtk.Entry())

    # Callbacks
    for entry in entries:
        entry.connect("activate", callback, dialog, entries) # Note extra arguments!
    dialog.connect("response", lambda x, _: x.destroy())

    # Put it all together
    for i in range(len(messages)):
        content_area.add(labels[i])
        content_area.add(entries[i])
    dialog.show_all()
    
def board_coords_to_square(x, y):
    square_size = get_square_size(G.board_display)
    board_x = x // square_size
    board_y = y // square_size
    if G.player == chess.WHITE:
        board_y = 7 - board_y
    else:
        board_x = 7 - board_x

    if int(board_x) >= 0 and int(board_y) >= 0 and int(board_x) < 8 and int(board_y) < 8:
        return chess.square(int(board_x), int(board_y))
    return None

def findFork(game):
    fork = game.parent
    transitionMove = game.move
    while len(fork.variations) <= 1 and fork != game.root():
        transitionMove = fork.move
        fork = fork.parent
    return fork, transitionMove

def load_new_game_from_game(game, player=chess.WHITE, save_file_name="savedGame.pgn"):
    # Warning: game isn't copied by value, so changing 
    # the input game later will also change the G.g game.
    G.games.append(game)
    G.save_file_names.append("savedGame.pgn")
    G.save_file_name = save_file_name
    G.currentGame += 1
    G.g = game
    G.player = player
    G.board_display.queue_draw()
    mark_nodes(G.g)
    update_pgn_message()
    
def load_new_game_from_fen(fen):
    try:
        board = chess.Board(fen)
    except ValueError:
        return False
    return load_new_game_from_board(board)

def load_new_game_from_board(board):
    new_game = chess.pgn.Game()
    new_game.setup(board)
    load_new_game_from_game(new_game, board.turn)
    return True

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
            offset = pgnFile.tell()
            firstChar = pgnFile.read(1)
            if firstChar == '%':
                restOfLine = pgnFile.readline()
                movePath = map(int, restOfLine.split())
            else:
                pgnFile.seek(offset)
            new_game = chess.pgn.read_game(pgnFile)
            mark_nodes(new_game)
        except:
            stringToDisplay = "Error loading PGN file '%s', or end of file reached." % pgnFile.name
            display_status(stringToDisplay)
            return False
        try:
            for m in movePath:
                new_game = new_game.variation(m)
        except:
            pass
    G.games.append(new_game)
    G.save_file_names.append(file_name if type(file_name) == str else file_name.name)
    G.pgnFile = pgnFile
    G.currentGame += 1
    G.g = new_game
    G.save_file_name = G.save_file_names[-1]
    G.player = G.g.board().turn
    update_pgn_message()
    update_game_info()
    return True

def update_pgn_textview_tags():
    if G.pgn_textview_enabled:
        # Useful iterators
        veryStart = G.pgn_buffer.get_start_iter()
        veryEnd = G.pgn_buffer.get_end_iter()

        # Are these necessary to clear the old tags?
        G.pgn_buffer.remove_tag_by_name("special", veryStart, veryEnd)
        G.pgn_buffer.remove_tag_by_name("book", veryStart, veryEnd)
        G.pgn_buffer.remove_tag_by_name("comment", veryStart, veryEnd)

        # Applying tags
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
    G.pgn_textview.queue_draw()

def update_pgn_textview_move():
    if G.pgn_textview_enabled:
        G.pgn_buffer.remove_tag_by_name("current", G.pgn_buffer.get_start_iter(), G.pgn_buffer.get_end_iter())
        start, end = G.nodesToRanges[G.g]
        start = G.pgn_buffer.get_iter_at_offset(start)
        end = G.pgn_buffer.get_iter_at_offset(end)
        G.pgn_buffer.apply_tag_by_name("current", start, end)
        G.pgn_textview.scroll_to_iter(start, 0, False, 0.5, 0.5)

def make_report():
    if G.rep:
        create_opening_game("currentTest.pgn", G.rep, G.player, G.g)
        splitter = subprocess.Popen(["split_game", "currentTest.pgn", "-o"])
        file_names = ["currentTest.pgn", "currentTest.pgn.split"] + list(map(lambda x : G.rep.directory + os.sep + 'games' + os.sep + x, G.rep.list_games(G.g.board())))
        reportFile = open("currentReport.pgn", 'w')
        splitter.wait()
        for name in file_names:
            fil = open(name, 'r')
            shutil.copyfileobj(fil, reportFile)
            print(file=reportFile)
        reportFile.close()
        display_status("Report saved to currentReport.pgn.")
    else:
        display_status("No repertoire file loaded.")
    return False

def move_completion(s):
    sans = map(G.g.board().san, G.g.board().legal_moves)
    candidates = list(filter(lambda x: x[0:len(s)] == s, sans))
    if len(candidates) == 0:
        return s, ""
    if len(candidates) == 1:
        return candidates[0], ""
    # There are multiple candidates if we get here
    return s, " (%s)" % " ".join(candidates)

def cleanup(showMessage=False):
    if G.stockfish != None:
        G.stockfish.process.process.send_signal(signal.SIGCONT) # In case stopped
        G.stockfish.terminate()
    if showMessage:
        print('Exiting gracefully.')
