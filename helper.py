# helper.py

# Helper functions, mainly for callbacks.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango
from gi.repository import GLib
import global_variables as G
import signal, math, subprocess, sys, os, os.path, shutil, chess, chess.pgn, shlex, io, requests, threading
from functools import reduce
from opening_pgn import *
from mmrw import *
from drawing import *
from dfs import *
from lichess_helpers import *
from help_helpers import *
from rep_visitor import rep_visitor
from pgn_visitor import game_gui_string

def make_move(m):
    # Make the move if legal
    # Check if move already in tree first
    moves = map(lambda v: v.move, G.g.variations)
    if m in moves:
        G.g = G.g.variation(m)
        update_pgn_textview_move(G.g)
        G.move_completed_callback(m)
        return True
    elif m in G.g.readonly_board.legal_moves:
        if G.new_move_mode == G.ADD_MAIN_VARIATION:
            G.g = G.g.add_main_variation(m)
        elif G.new_move_mode == G.ADD_LAST_VARIATION:
            G.g = G.g.add_variation(m)
        mark_nodes(G.g.root())
        update_pgn_message()
        G.move_completed_callback(m)
        return True
    return False

def parse_side(side_string):
    side_string = side_string.lower()
    if side_string in ["w", "white"]:
        return chess.WHITE
    elif side_string in ["b", "black"]:
        return chess.BLACK
    return None

def mark_if_special(game):
    '''Assuming the 'player' only makes moves appearing in first variations,
    a node is special if it can be reached.'''
    game.special = False
    if game.is_main_variation() and (game.parent == None or game.parent.special):
        game.special = True # Root node
    elif game.readonly_board.turn == G.player:
        if game.parent.special:
            game.special = True

def mark_if_book(game):
    '''Checks if a game appears in the loaded opening repertoire.'''
    game.book = 0
    if G.rep:
        # Root node
        if game.parent == None:
            game.book = 1.5 # 1 for repertoire position, 0.5 for set to learn

        else:
            position = game.parent.readonly_board
            parent_book = int(game.parent.book)
            
            # Normal book
            if G.player == chess.WHITE and G.rep.hasPositionWhite(position) and game.move in G.rep.findMovesWhite(position): game.book = 1
            elif G.player == chess.BLACK and G.rep.hasPositionBlack(position) and game.move in G.rep.findMovesBlack(position): game.book = 1
            # The other player deviates first
            elif G.player == chess.WHITE and parent_book == 1 and position.turn == chess.BLACK and game.move not in G.rep.findMovesWhite(position): game.book = 2
            elif G.player == chess.BLACK and parent_book == 1 and position.turn == chess.WHITE and game.move not in G.rep.findMovesBlack(position): game.book = 2
            elif parent_book == 2: game.book = 2
            
            # Check if set to learn
            zh = chess.polyglot.zobrist_hash(position)
            mmrw = G.rep.get_mmrw(G.player, position.turn)
            index = mmrw.bisect_key_left(zh)
            while index < len(mmrw):
                entry = mmrw[index]
                if entry.key != zh:
                    break
                if entry.move != game.move:
                    index += 1
                    continue
                if entry.learn != 0:
                    game.book += 0.5
                break

def is_arrow_nag(nag):
    return nag & (1 << (32 + 6 + 6))

def parse_arrow_nag(nag):
    # Binary format for special NAG's:
    # 1xxxxxxyyyyyyzz...zz,
    # where xxxxxx is the starting square of the arrow,
    # yyyyyy is the ending square of the arrow,
    # and zz...zz (8 * 4 = 32 digits) is the color of the arrow
    # (rgb + transparency out of 256).
    transparency = ((nag & 255) + 1) / 256.0
    nag >>= 8
    blue = ((nag & 255) + 1) / 256.0
    nag >>= 8
    green = ((nag & 255) + 1) / 256.0
    nag >>= 8
    red = ((nag & 255) + 1) / 256.0
    nag >>= 8
    end_square = nag & 63
    nag >>= 6
    start_square = nag & 63
    return start_square, end_square, red, green, blue, transparency

def mark_nodes(game):
    '''Marks special and book nodes, as well as the arrows given by arrow nags.'''
    # TODO: Create subclass to have these attributes
    # Make sure node has an arrows attribute
    if not hasattr(game, 'arrows'):
        game.arrows = {}

    if not hasattr(game, 'readonly_board'):
        game.readonly_board = game.board()

    # Change special NAG's to arrows
    # Reminder: Root nodes don't have nags, so no arrows of the root node will be saved
    for nag in game.nags:
        if is_arrow_nag(nag):
            # See parse_arrow_nag for details
            start_square, end_square, red, green, blue, transparency = parse_arrow_nag(nag)
            game.arrows[(start_square, end_square)] = (red, green, blue, transparency)

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

def learn_special_node(game):
    if game.special:
        G.rep.make_position_learnable(game.board(), G.player)

def learn_special_nodes(game):
    learn_special_node(game)
    for node in game.variations:
        if node.special:
            learn_special_nodes(node)

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

def load_new_game_from_board_history(board):
    new_game = chess.pgn.Game.from_board(board)
    load_new_game_from_game(new_game)
    G.handlers["go_to_end_callback"]()
    G.handlers["flip_callback"](G.g.readonly_board.turn)
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
    # Line below changed to avoid rewriting over files accidentally,
    # especially when they have more than one game in them.
    # G.save_file_names.append(file_name if type(file_name) == str else file_name.name)
    G.save_file_names.append("savedGame.pgn")
    G.pgnFile = pgnFile
    G.currentGame += 1
    G.g = new_game
    G.player = G.g.readonly_board.turn
    update_pgn_message()
    update_game_info()
    return True

def load_new_game_from_piece_list(piece_list_string):
    words = piece_list_string.split()
    isWhiteMarker = lambda x : x.lower() in ["w:", "w", "white:", "white"]
    isBlackMarker = lambda x : x.lower() in ["b:", "b", "black:", "black"]

    # Determine turn
    turn = parse_side(words[-1])
    if turn == None:
        turn = chess.WHITE
    else:
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

def update_pgn_textview_tags(node):
    if G.pgn_textview_enabled:
        # Useful iterators
        veryStart = G.pgn_buffer.get_start_iter()
        veryEnd = G.pgn_buffer.get_end_iter()

        # Are these necessary to clear the old tags?
        G.pgn_buffer.remove_tag_by_name("special", veryStart, veryEnd)
        G.pgn_buffer.remove_tag_by_name("book", veryStart, veryEnd)
        G.pgn_buffer.remove_tag_by_name("learn", veryStart, veryEnd)
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
        for start, end in G.learnRanges:
            start = G.pgn_buffer.get_iter_at_offset(start)
            end = G.pgn_buffer.get_iter_at_offset(end)
            G.pgn_buffer.apply_tag_by_name("learn", start, end)
        for start, end in G.commentRanges:
            start = G.pgn_buffer.get_iter_at_offset(start)
            end = G.pgn_buffer.get_iter_at_offset(end)
            G.pgn_buffer.apply_tag_by_name("comment", start, end)
        update_pgn_textview_move(node)

def update_pgn_message():
    if G.pgn_textview_enabled:
        current_game_node = G.g
        # Do updating
        G.pgn_buffer.set_text(game_gui_string(G.g.root()))

        # Update text tags
        update_pgn_textview_tags(current_game_node)
        G.pgn_textview.queue_draw()
        # Scrolling will occur after drawing since 
        # the draw event has higher priority.
        # Would be nice to prevent unscrolling in first place when possible.
        # Running update_pgn_textview_move before queue_draw did not work.
        GLib.idle_add(update_pgn_textview_move, current_game_node)

def update_pgn_textview_move(node):
    if G.pgn_textview_enabled:
        G.pgn_buffer.remove_tag_by_name("current", G.pgn_buffer.get_start_iter(), G.pgn_buffer.get_end_iter())
        start, end = G.nodesToRanges[node]
        start = G.pgn_buffer.get_iter_at_offset(start)
        end = G.pgn_buffer.get_iter_at_offset(end)
        G.pgn_buffer.apply_tag_by_name("current", start, end)
        if G.pgn_textview_mark == None:
            G.pgn_textview_mark = G.pgn_buffer.create_mark(None, end, False)
        else:
            G.pgn_buffer.move_mark(G.pgn_textview_mark, end)
        G.pgn_textview.scroll_to_mark(G.pgn_textview_mark, 0, True, 0.5, 0.5)

def make_report():
    if G.rep:
        create_opening_game("currentTest.pgn", G.rep, G.player, G.g)
        splitter = subprocess.Popen(["python3", "splitGame.py", "currentTest.pgn", "-o"])
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
    sans = map(G.g.readonly_board.san, G.g.readonly_board.legal_moves)
    candidates = list(filter(lambda x: x[0:len(s)] == s, sans))
    if len(candidates) == 0:
        return s, ""
    if len(candidates) == 1:
        return candidates[0], ""
    # There are multiple candidates if we get here
    return s, " (%s)" % " ".join(candidates)

def arrow_nag(start_square, end_square, color_tuple):
    '''Produces integer NAG to represent an arrow.
    The integers produced here are intentionally huge.
    In particular, they do not collide with regular NAGs, which should be < 256.'''
    result = 1
    result <<= 6
    result += start_square & 63
    result <<= 6
    result += end_square & 63
    for i in range(4):
        result <<= 8
        result += int(color_tuple[i] * 255) & 255
    return result

def ot_move_completed_callback(answer):
    '''This technically isn't a callback function, but rather a function that generates
    the callback function for an answer being given in opening trainer mode.'''
    if answer:
        # Currying
        def f(guess):
            if guess.from_square == answer.from_square and guess.to_square == answer.to_square and guess.promotion == answer.promotion:
                setup_ot_mode()
            else:
                G.handlers["delete_children_callback"]() # Uses dictionary to avoid circular reference problem
                G.handlers["show_opening_comment_callback"]()
        return f
    return lambda _ : None

def setup_ot_mode(only_sr=False):
    '''Sets up opening trainer mode, and starts it or continues it with the next problem).'''
    # Load generator if first time
    if G.ot_gen == None and G.ot_board != None:
        G.ot_gen = rep_visitor(G.ot_board, G.player, only_sr)

    # Get next position
    try:
        b, m = next(G.ot_gen)
    except StopIteration:
        display_status("Training complete! (%d/%d)" % G.ot_progress)
        G.move_completed_callback = ot_move_completed_callback(chess.Move.null())
        return False

    # Set new answer + callback, and load new board
    if only_sr:
        if random.random() < G.SR_FULL_LINE_PROBABILITY:
            return sr_full_line_setup(create_board_answer_stack(b, m))
        else:
            G.incorrect_answers = 0
            G.starting_time = time.time()
            G.move_completed_callback = sr_move_completed_callback(m) # This is a function
    else:
        G.move_completed_callback = ot_move_completed_callback(m) # This is a function
    load_new_game_from_board_history(b)
    display_status(("(%d/%d) " + board_moves(b)) % G.ot_progress)

    return False

def sr_full_line_setup(stack, only_sr=True):
    '''Similar to sr_move_completed_callback, except covers entire line.'''
    # The only_sr argument is completely ignored, just meant for compatibilty 
    # for 'setup_function' use in sr_move_completed_callback

    # Create next board/answer pair
    try:
        board, answer = stack.pop()
    except IndexError:
        return setup_ot_mode(only_sr)

    # Prepare callback and display problem
    G.incorrect_answers = 0
    G.starting_time = time.time()
    load_new_game_from_board_history(board)
    display_status(("(%d/%d) " + board_moves(board)) % G.ot_progress)
    new_setup = lambda x : sr_full_line_setup(stack, x) # Closure
    G.move_completed_callback = sr_move_completed_callback(answer, new_setup)
        
    return False

def sr_move_completed_callback(answer, setup_function=setup_ot_mode):
    '''Similar to ot_move_completed_callback, except for spaced repetition practice.'''
    if answer:
        def f(guess):
            if guess == answer:
                # Correct answer
                # Update learning data
                G.rep.update_learning_data(G.player, G.g.parent.readonly_board, answer, G.incorrect_answers, time.time() - G.starting_time)
                # Update progress
                G.ot_progress = (G.ot_progress[0] + (not G.incorrect_answers), G.ot_progress[1] + 1)

                # Prepare next
                setup_function(True)
            elif guess in G.rep.findMoves(G.player, G.g.parent.readonly_board):
                # Valid alternate, give another try with clock reset
                G.handlers["go_back_callback"]()
                display_status("%s is a valid alternate." % G.g.readonly_board.san(guess))
                G.starting_time = time.time()
            else:
                G.incorrect_answers += 1
                G.handlers["delete_children_callback"]()
                G.handlers["show_opening_comment_callback"]()
        return f
    return lambda _ : None

def create_board_answer_stack(board, final_answer):
    # Create stack of positions of interest
    # Helper for sr_full_line_setup
    stack = [(board.copy(), final_answer)]
    while 1:
        try:
            last_move = board.pop()
        except IndexError:
            break
        if board.turn != G.player:
            continue
        stack.append((board.copy(), last_move))

    return stack

def save_current_pgn(save_file_name, show_status=False, prelude=None, set_global_save_file=False, proper_format=False):
    '''Saves current game to specified file.
    
    Uses preset save file name if none is specified.'''
    game_to_save = G.g.root()
    if proper_format:
        game_to_save = copy_game(G.g.root(), copy_improper_nags=False)
    outPgnFile = open(save_file_name, 'w')
    if prelude:
        print(prelude, file=outPgnFile)
    print(game_to_save, file=outPgnFile, end="\n\n")
    outPgnFile.close()
    if show_status:
        display_status("Game saved to %s." % save_file_name)
    return False

def autosave():
    '''Automatically saves current game every G.autosave_interval seconds.'''
    while True:
        time.sleep(G.autosave_interval)
        save_file_name = G.autosave_dir + str(int(time.time() * 100))
        string_exporter = chess.pgn.StringExporter()
        pgn_string = G.g.root().accept(string_exporter)
        if pgn_string == G.last_autosave_pgn_string:
            continue
        else:
            G.last_autosave_pgn_string = pgn_string
            with open(save_file_name, 'w') as autosave_file:
                print(pgn_string, file=autosave_file)
