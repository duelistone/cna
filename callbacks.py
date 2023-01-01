# callbacks.py
'''Module for callbacks from GUI. These must also be registered
in the handlers dictionary in the global_variables module, which is done
automatically if you use the @gui_callback decorator defined in decorators.py.'''

import gi
import asyncio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango
from gi.repository import GLib
import global_variables as G
import signal, math, subprocess, sys, os, os.path, shutil, chess, chess.pgn, shlex, random
from functools import reduce
from helper import *
from opening_pgn import *
from mmrw import *
from engine import *
from drawing import *
from dfs import *
from decorators import *
from rep_visitor import *
from lichess_helpers import *
from help_helpers import *

# GUI callbacks

@gui_callback
@documented
def flip_callback(*args):
    '''Flips or sets board perspective. 

    If first argument exists, it should specify a specific color.
    This change is more than just cosmetic, as it affects
    which nodes are special or included in the repertoire.'''
    # Flip board
    G.player = not G.player
    # Set perspective if necessary
    if len(args) > 0:
        if type(args[0]) == str:
            if args[0].lower() in ['w', 'white']:
                G.player = chess.WHITE
            elif args[0].lower() in ['b', 'black']:
                G.player = chess.BLACK
        else:
            G.player = bool(args[0])
    # Update node properties, PGN text, and board appropriately
    mark_nodes(G.g.root())
    update_pgn_message()
    G.board_display.queue_draw()
    return False

@gui_callback
@documented
def go_back_callback(*args):
    '''Moves back to parent node.'''
    if G.g.parent:
        G.g = G.g.parent
        update_pgn_textview_move(G.g)
        G.board_display.queue_draw()
    return False

@gui_callback
@documented
def go_forward_callback(var_index=0, *args):
    '''Moves forward to a child node. 

    Default is to go to first child.'''
    # If first argument is string (entry version), then 
    # we try to make it var_index.
    if type(var_index) == str:
        try:
            var_index = int(var_index)
        except:
            var_index = 0
            pass
    # If var_index is too big, we go down last variation
    var_index = min(len(G.g.variations) - 1, var_index)
    # Moving and updating
    if var_index >= 0:
        G.g = G.g.variation(var_index)
        update_pgn_textview_move(G.g)
        G.board_display.queue_draw()
    return False

# TODO: Jump up/down variations with k and j (or w and s)

# The next three are just for keyboard shortcuts.
# In the entry bar or scripts, "go_forward var_index" can be used.

@gui_callback
@documented
def go_first_variation_callback():
    '''Moves to first variation after PV.'''
    return go_forward_callback(1)

@gui_callback
@documented
def go_second_variation_callback():
    '''Moves to second variation after PV.'''
    return go_forward_callback(2)

@gui_callback
@documented
def go_third_variation_callback():
    '''Moves to third variation after PV.'''
    return go_forward_callback(3)

@gui_callback
@documented
def go_to_beginning_callback(*args):
    '''Moves to root node.'''
    G.g = G.g.root()
    update_pgn_textview_move(G.g)
    G.board_display.queue_draw()
    return False

@gui_callback
@documented
def go_to_end_callback(*args):
    '''Moves to end of PV (from current node).'''
    while len(G.g.variations) > 0:
        G.g = G.g.variation(0)
    update_pgn_textview_move(G.g)
    G.board_display.queue_draw()
    return False

@gui_callback
@documented
def add_comment_callback(*args):
    '''Opens a dialog to edit the comment of the current node.'''
    commentPrompt(G.window, "Edit comment:", comment_key_press_callback, G.g.comment)
    return False

@gui_callback
@documented
def set_comment_callback(*args):
    '''Sets comment of current node to the given string.'''
    G.g.comment = " ".join(args)
    update_pgn_message()
    return False

@gui_callback
@documented
def set_opening_comment_callback(*args):
    '''Sets opening comment of current board position.'''
    if len(args) == 0:
        display_status("No comment given.")
        return False
    G.rep.set_comment(G.g.readonly_board, args[0])
    return False

@gui_callback
@documented
def show_opening_comment_callback(*args):
    '''Shows opening comment of current board position.'''
    c = G.rep.get_comment(G.g.readonly_board)
    if c:
        display_status(c)
    else:
        display_status("No opening comment exists for this position.")
    return False

@gui_callback
@documented
def add_last_callback(*args):
    '''Sets the default behavior of adding new variations.

    A new variation will be added as the last variation.'''
    G.new_move_mode = G.ADD_LAST_VARIATION
    return False

@gui_callback
@documented
def add_main_callback(*args):
    '''Sets the default behavior of adding new variations.

    A new variation will be added as the main variation.'''
    G.new_move_mode = G.ADD_MAIN_VARIATION
    return False

@gui_callback
@documented
def walk_random_path_callback(*args):
    '''Takes a random path from current node, 
    following the options available in the PGN.'''
    while G.g.variations:
        G.g = random.choice(G.g.variations)
    G.board_display.queue_draw()
    update_pgn_textview_move(G.g)
    return False

@gui_callback
@documented
def walk_random_opening_path_callback(*args):
    '''Takes a random path from current position
    using repertoire. Avoids repeating positions when choosing a path.'''
    if G.rep:
        visited_hashes = set()
        while True:
            visited_hashes.add(chess.polyglot.zobrist_hash(G.g.board()))
            try:
                moves = list(G.rep.findMoves(G.player, G.g.board()))
                while moves:
                    index = random.randint(0, len(moves) - 1)
                    choice = moves[index]
                    temp_board = G.g.board()
                    temp_board.push(choice)
                    if chess.polyglot.zobrist_hash(temp_board) in visited_hashes:
                        del moves[index]
                        continue
                    else:
                        make_move(choice)
                        break
                else:
                    break
            except:
                # In case findMoves raises IndexError instead of returning []
                break
    G.board_display.queue_draw()
    return False

@gui_callback
@documented
def toggle_sound_callback(*args):
    if len(args) > 0:
        G.sound = bool(args[0])
    else:
        G.sound = not G.sound
    if G.sound:
        display_status("Sound turned on.")
    else:
        display_status("Sound turned off.")
    return False

#@gui_callback
#@documented
#def set_hash_callback(*args):
#    '''Sets hash size for an engine.'''
#    try:
#        hash_size = int(args[0])
#    except:
#        display_status("Could not parse hash size (in MB).")
#        return False
#    change_engine_setting("Hash", hash_size)
#    return False

#@gui_callback
#@documented
#def set_engine_option_callback(*args):
#    '''Sets engine settings to specified name/value pairs.
#
#    Args: name1 value1 [name2 value2] ...'''
#    try:
#        name = args[0]
#        value = args[1]
#    except:
#        display_status("An option name and value were not provided")
#        return False
#    change_engine_setting(name, value)
#    return False

@gui_callback
@documented
def set_engine_callback(*args):
    '''Sets which engines should be used first.
    
    Multiple arguments correspond to the first n engines which should be used.
    This should be called before any engine is used.'''
    for name in args:
        try:
            index = G.engine_commands.index(name)
        except ValueError:
            display_status("Invalid engine name '%s' given" % name)
            return False
        # Move index to front in engine_commands and engines
        G.engine_commands = [G.engine_commands[index]] + G.engine_commands[:index] + G.engine_commands[index + 1:]
        G.engines = [G.engines[index]] + G.engines[:index] + G.engines[index + 1:]

    return False
    
@gui_callback
@documented
def wait_callback(*args):
    '''Waiting callback. Behavior depends on types of arguments given.
    Here are some ideas (ones with asterisk not implemented):
    sleep float              -> Sleep for that many seconds
    nodes integer float      -> Wait until current analysis reaches that many nodes.
                                The third argument is optional and represents how often, in seconds,
                                the analysis is checked.
    *depth integer float      -> Similar, but with depth
    *turn color float         -> Similar, but with color (white/w or black/w)
    *score bound_type integer -> Wait until score meets a certain bound. bound_type is upperbound/lowerbound/mate.
                                     If mate is given, the integer argument is optional, and would represent the
                                     number of moves the mate needs to be achieved by.'''
    default_resolution = 1
    if args[0] == "sleep":
        try:
            sleep_time = float(args[1])
        except:
            display_status("No time given for sleep command.")
            return False
        time.sleep(sleep_time)
        
    if args[0] == "nodes":
        try:
            nodes = int(args[1])
        except:
            display_status("No number of nodes given for wait command.")
            return False
        try:
            resolution = float(args[2])
            assert(resolution >= 0)
        except:
            resolution = default_resolution

        while G.engines[G.current_engine_index].latest_engine_stats[4] < nodes:
            time.sleep(resolution)

        return False

    return False

@gui_callback
@documented
def comment_move_callback(*args):
    '''Appends PV of engine at the end of current comment.'''
    engine = G.engines[G.current_engine_index]
    if engine.latest_engine_lines:
        if G.g.comment:
            G.g.comment += " " + engine.latest_engine_lines[0]
        else:
            G.g.comment += engine.latest_engine_lines[0]
        update_pgn_message()
    return False

@gui_callback
@documented
def repeat_callback(*args):
    '''Repeats a command a given number of times.'''
    try:
        num_repetitions = int(args[0])
    except:
        display_status("Did not provide an integer number of repetitions")
    try:
        command = args[1]
    except:
        return False
    command_list = num_repetitions * [command]
    entry_bar_callback(" && ".join(command_list))
    return False

@gui_callback
@documented
def opening_games_callback(*args):
    '''Lists available opening games in a position in the repertoire.

    This feature is experimental and probably won't work too well.'''
    games = G.rep.list_games(G.g.board())
    display_string = " ".join(games)
    display_status(display_string)
    return False

@gui_callback
@documented
def opening_save_callback(*args):
    '''Adds all special nodes in the current game to the repertoire,.'''
    if G.rep:
        save_special_nodes_to_repertoire(G.g.root())
        G.rep.flush()
        mark_nodes(G.g.root())
        G.board_display.queue_draw()
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
@documented
def opening_single_save_callback(*args):
    '''Adds the current node to the repertoire.'''
    if G.rep:
        save_special_node_to_repertoire(G.g)
        G.rep.flush()
        mark_nodes(G.g.root())
        G.board_display.queue_draw()
        update_pgn_message()
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
@documented
def opening_save_game_callback(*args):
    '''Adds a game of chess to the repertoire.

    This does not affect the positions in the repertoire itself.'''
    if G.rep:
        G.rep.add_games([G.g.root()])
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
@documented
def display_repertoire_moves_callback(*args):
    '''Displays the moves given in the repertoire, and optionally in the
    lichess opening explorer as well, for the current position.'''
    if G.rep or G.use_lichess:
        words = []
        board = G.g.board()
        if G.rep:
            words.append("Repertoire moves:")
            for move in G.rep.findMoves(G.player, board):
                words.append(board.san(move))
            display_status(" ".join(words)) # In case worker thread takes too long
        if G.use_lichess:
            def load_lichess_moves(words):
                words.append("Lichess moves:")
                moves = lichess_opening_moves(board)
                if moves != None:
                    words.extend(moves)
                display_status(" ".join(words))
                
            thread = threading.Thread(target=load_lichess_moves, args=(words,), daemon=True)
            thread.start()
    else:
        display_status("No repertoire loaded, and lichess turned off.")
    return False

@gui_callback
@documented
def lichess_top_games_callback(*args):
    def load_lichess_top_games():
        info_list, G.top_game_ids = lichess_top_games(G.g.board())
        display_status(", ".join(info_list))
    
    thread = threading.Thread(target=load_lichess_top_games, daemon=True)
    thread.start()
    return False

@gui_callback
@documented
def load_lichess_game_callback(*args):
    if len(args) < 1:
        display_status("No game specified.")
        return False

    # First argument could be game id or index of game id from top game list
    try:
        game_id = G.top_game_ids[int(args[0])]
    except IndexError:
        display_status("No top game #%d stored. Try running lichess_top_games again." % int(args[0]))
        return False
    except:
        game_id = args[0]

    def load_lichess_game(game_id):
        game = lichess_game(game_id)
        if game != None:
            # TODO: Add behavior to merge with current game, and probably make that default
            def load_and_give_info():
                load_new_game_from_game(game, player=G.player)
                update_game_info()
            GLib.idle_add(load_and_give_info)
        else:
            display_status("An error occurred fetching or parsing the game.")

    thread = threading.Thread(target=load_lichess_game, args=(game_id,), daemon=True)
    thread.start()
    return False

@gui_callback
@documented
def load_lichess_game_1_callback(*args):
    return load_lichess_game_callback(0)

@gui_callback
@documented
def load_lichess_game_2_callback(*args):
    return load_lichess_game_callback(1)

@gui_callback
@documented
def load_lichess_game_3_callback(*args):
    return load_lichess_game_callback(2)

@gui_callback
@documented
def load_lichess_game_4_callback(*args):
    return load_lichess_game_callback(3)

@gui_callback
@documented
def toggle_lichess_callback(*args):
    G.use_lichess = not G.use_lichess
    if G.use_lichess:
        display_status("Lichess opening support turned on.")
    else:
        display_status("Lichess opening support turned off.")
    return False

@gui_callback
@documented
def display_variations_callback(*args):
    '''Displays a list of the variations in the current game for the current position.'''
    words = ["Variations:"]
    for child in G.g.variations:
        words.append(G.g.readonly_board.san(child.move))
    display_status(" ".join(words))
    return False

@gui_callback
@documented
def queen_promotion_callback(*args):
    '''Sets promotion piece to queen.'''
    G.promotion_piece = chess.QUEEN
    return False

@gui_callback
@documented
def rook_promotion_callback(*args):
    '''Sets promotion piece to rook.'''
    G.promotion_piece = chess.ROOK
    return False

@gui_callback
@documented
def bishop_promotion_callback(*args):
    '''Sets promotion piece to bishop.'''
    G.promotion_piece = chess.BISHOP
    return False

@gui_callback
@documented
def knight_promotion_callback(*args):
    '''Sets promotion piece to knight.'''
    G.promotion_piece = chess.KNIGHT
    return False

@gui_callback
@documented
def load_fen_entry_callback(widget, dialog=None):
    '''Loads the given PGN, FEN, piece list, or PGN string into a new game.

    The order above is the order in which the program tries to interpret
    the type of the input.'''
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

@gui_callback
@documented
def paste_callback(*args):
    '''Sets the entry bar text to loading the current clipboard text.

    It does not actually execute the command, to leave the user a chance to 
    check that the text is as intended.'''
    text = G.clipboard.wait_for_text()
    def result():
        G.entry_bar.set_text("l '%s'" % text)
        G.entry_bar.grab_focus()
        G.entry_bar.set_position(-1)
    if len(args) > 0 and type(args[0]) != str:
        # Key callback version
        result()
        return False
    return result

@gui_callback
@documented
def copy_fen_callback(*args):
    '''Copies the FEN of the current position to the clipboard.

    Note that this disables the standard Ctrl-C copy text shortcut sometimes.'''
    if G.board_display.is_focus():
        G.clipboard.set_text(G.g.readonly_board.fen(), -1)
    return False

@gui_callback
@documented
def clear_arrows_callback(*args):
    '''Clears all arrows from the current position.'''
    # Remove any arrow NAGs
    for source, target in G.g.my_arrows:
        nag = arrow_nag(source, target, G.g.my_arrows[(source, target)])
        G.g.nags.remove(nag)
    # Clear arrows dict and redraw board
    G.g.my_arrows.clear()
    G.board_display.queue_draw()
    return True

@gui_callback
@documented
def arrow_color_callback(*args):
    '''Set main arrow color callback. 

    Arg is color name or RGB[A] float values.
    Transparency field is optional.
    Currently the other arrow colors cannot be changed.'''
    # TODO: Add ability to change alternate arrow colors
    if len(args) >= 3:
        try:
            # Change as many fields as given correctly
            G.arrowRGBA[0] = float(args[0])
            G.arrowRGBA[1] = float(args[1])
            G.arrowRGBA[2] = float(args[2])
            G.arrowRGBA[3] = float(args[3])
        except:
            pass
    elif len(args) > 0:
        # First field should be color name.
        # Second, optional, field is transparency.
        color_name = args[0]
        try:
            assert(color_name in G.colors)
        except:
            display_status("Invalid color name given.")
            return False
        color_hex = G.colors[color_name]
        color = gdk.color_parse(color_hex)
        G.arrowRGBA[0] = color.red_float
        G.arrowRGBA[1] = color.green_float
        G.arrowRGBA[2] = color.blue_float
        try:
            G.arrowRGBA[3] = float(args[3])
        except:
            pass
    return False

@gui_callback
@documented
def arrow_transparency_callback(*args):
    '''Just set the main arrow transparency.

    This should be in the form of a float in [0, 1].'''
    try:
        transparency = float(args[3])
        assert(transparency >= 0 and transparency <= 1)
    except:
        display_status("Invalid transparency value given.")
        return False
    G.arrowRGBA[3] = transparency

@gui_callback
@documented
def set_header_callback(*args):
    '''Set PGN headers.

    Args: name1 value1 [name2 value2] ...
    Does not remove existing headers, but can replace their value.'''
    if len(args) < 2:
        update_pgn_message()
        return False
    G.g.root().headers[args[0]] = args[1]
    return set_header_callback(args[2:])

@gui_callback
@documented
def clear_headers_callback(*args):
    '''Remove headers from PGN, and adds the 7 default (supposedly mandatory) headers.'''
    G.g.root().headers = chess.pgn.Game().headers.copy()
    update_pgn_message()
    return False

@gui_callback
@documented
def set_nag_callback(*args):
    '''Adds a NAG to a node.

    It can be specified by the NAG index,
    or by a corresponding name described in global_variables.py.'''
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

@gui_callback
@documented
def remove_nags_callback():
    '''Removes all NAGs from a node.'''
    if len(G.g.nags) > 0:
        G.g.nags.clear()
        update_pgn_message()
    return False

@gui_callback
def header_entry_callback(widget, dialog, entries):
    '''Callback for header_set_callback dialog.
    Not intended for other uses.'''
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
@documented
def header_set_callback(*args):
    '''Creates a graphical dialog to add header tags.'''
    messages = ["Tag name (defaults: Event, Site, Date, Round, White, Black, Result)", "Value"]
    multiPrompt(G.window, messages, header_entry_callback)
    return False

@gui_callback
@documented
def previous_game_callback(*args):
    '''Moves to previous game in game list.'''
    # TODO: Test previous/next game functionality and fix bugs
    if G.currentGame > 0:
        G.currentGame -= 1
        G.g = G.games[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
        update_game_info()
    return False

@gui_callback
def next_game_callback(*args):
    '''Moves to next game in game list.

    If no such game exists and the current game was retrieved from a PGN file, 
    we look for a next game to read from the file.'''
    if G.currentGame < len(G.games) - 1:
        G.currentGame += 1
        G.g = G.games[G.currentGame]
        G.board_display.queue_draw()
        update_pgn_message()
        update_game_info()
    elif G.currentGame == len(G.games) - 1 and G.pgnFile != None:
        # Try to read next game, if not give up.
        success = load_new_game_from_pgn_file(G.pgnFile) # Already updates pgn message
        if not success: return False
        G.board_display.queue_draw()

    return False

@gui_callback
@documented
def demote_callback(*args):
    '''Demote a variation.'''
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.demote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
@documented
def promote_callback(*args):
    '''Promote a variation.'''
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
@documented
def promote_to_main_callback(*args):
    '''Promote a variation to main variation.'''
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        fork.promote_to_main(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
@documented
def demote_to_last_callback(*args):
    '''Demote a variation to last variation.'''
    # Is this even necessary?
    if G.g.parent != None:
        fork, transitionMove = findFork(G.g)
        for i in range(len(fork.variations) - 1):
            fork.demote(transitionMove)
        mark_nodes(G.g.root())
        update_pgn_message()
    return False

@gui_callback
@documented
def delete_children_callback(*args):
    '''Callback to delete nodes in current game.

    First tries to deletes the children of a node.
    If no children exist, then it deletes the current node.'''
    # TODO: Undo functionality???
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

@gui_callback
@documented
def delete_nonspecial_nodes_callback(*args):
    '''Creates and opens a copy of the current game, but only with only its special nodes.

    The original game stays intact, and can be reopened by 
    jumping to the previous game.'''
    # Opens new game with just special nodes
    game = copy_game(G.g.root(), lambda node : node.special)
    load_new_game_from_game(game)
    return False

@gui_callback
@documented
def opening_test_callback(*args):
    '''Opens an opening test for the descendents of the current node in the repertoire.

    Uses the same point of view as currently being used.'''
    learn_mode = False
    if len(args) > 0:
        learn_mode = args[0]
    if G.rep:
        if G.player == chess.WHITE:
            if learn_mode:
                subprocess.Popen(['python3', 'gui.py', '--ot', '--sr', G.g.readonly_board.fen()])
            else:
                subprocess.Popen(['python3', 'gui.py', '--ot', G.g.readonly_board.fen()])
        else:
            if learn_mode:
                subprocess.Popen(['python3', 'gui.py', '-b', '--ot', '--sr', G.g.readonly_board.fen()])
            else:
                subprocess.Popen(['python3', 'gui.py', '-b', '--ot', G.g.readonly_board.fen()])
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
def board_draw_callback(widget, cr):
    '''Main drawing callback function.
    
    Used to update the board drawing.'''
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
                # TODO: Make global setting and allow change
                cr.set_source_rgb(182/256, 137/256, 100/256) # lichess
                # cr.set_source_rgb(0.450980, 0.53725, 0.713725) # Blue
                # cr.set_source_rgb(201/256, 171/256, 131/256) # Tan
                # cr.set_source_rgb(108/256, 173/256, 76/256) # Green
                cr.rectangle(0, 0, square_size, square_size)
                cr.fill()
            else:
                # Light squares
                #cr.set_source_rgb(0.952941, 0.952941, 0.952941)
                cr.set_source_rgb(241/256, 218/256, 182/256) # lichess
                cr.rectangle(0, 0, square_size, square_size)
                cr.fill()

            # Highlight square if necessary
            if (square, square) in G.g.my_arrows:
                highlight_square(cr, G.g.my_arrows[(square, square)], square_size)

            # Draw the piece, if there is one
            piece = G.g.readonly_board.piece_at(square)
            if piece != None and (G.drag_source == G.NULL_SQUARE or chess.square(x, y) != G.drag_source):
                draw_piece(cr, piece, square_size)

            # Go to next rank
            cr.translate(0, square_size)

        # Go to next file
        cr.translate(square_size, -square_size * 8);

    cr.restore()

    # Draw arrows
    for e in G.g.my_arrows:
        if e[0] == e[1]: continue # These are the highlighted squares, already done
        draw_arrow(cr, G.g.my_arrows[e], square_size, e[0], e[1])

    # Draw little circle for side to move on bottom left
    # and for opening status (if necessary)
    margin = int(math.ceil(0.01 * square_size))
    radius = int(math.ceil(0.05 * square_size))
    centerCoord = margin + radius
    cr.save()
    cr.translate(centerCoord, 8 * square_size - centerCoord) # To get bottom left
    if G.g.readonly_board.turn == chess.WHITE:
        cr.set_source_rgb(1, 1, 1)
    else:
        cr.set_source_rgb(0, 0, 0)
    cr.arc(0, 0, radius, 0, 2 * math.pi)
    cr.fill()
    cr.restore()

    if G.g.book < 2:
        cr.save()
        cr.translate(8 * square_size - centerCoord, 8 * square_size - centerCoord) # Bottom right
        if G.g.book >= 1:
            # Still in book
            cr.set_source_rgb(0, 0.7, 0)
        elif G.g.book >= 0:
            # Left book by going against repertoire
            cr.set_source_rgb(1, 0, 0)
        cr.arc(0, 0, radius, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

    # Dragging pieces
    if G.drag_source != G.NULL_SQUARE:
        cr.save()
        cr.identity_matrix()
        cr.translate(padding + G.mouse_x - square_size // 2, padding + G.mouse_y - square_size // 2)
        draw_piece(cr, G.g.readonly_board.piece_at(G.drag_source), square_size)
        cr.restore()

    return False

@gui_callback
def board_mouse_down_callback(widget, event):
    '''Keeps track of necessary data on mouse down events on the board.'''
    if event.button not in [1, 3]:
        return False

    clicked_square = board_coords_to_square(event.x, event.y)
    if clicked_square != None:
        if event.button == 1 and G.g.readonly_board.piece_at(clicked_square) != None:
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
    '''Board mouse up callback.

    Used for events such as completing a move or arrow.'''
    if event.button == 8:
        if G.ot_board != None:
            return previous_game_callback()
        return play_training_move_callback()
    if event.button == 9:
        return play_move_callback()
    if event.button == 2:
        return analyze_callback()
        
    if event.button == 3:
        # Right click lifted
        if G.arrow_source == G.NULL_SQUARE:
            return False

        arrow_target = board_coords_to_square(event.x, event.y)

        if arrow_target != None and G.arrow_source != None:
            elem = (G.arrow_source, arrow_target)
            if elem in G.g.my_arrows:
                nag = arrow_nag(G.arrow_source, arrow_target, G.g.my_arrows[elem])
                G.g.nags.remove(nag)
                del G.g.my_arrows[elem]
            else:
                modifiers = gtk.accelerator_get_default_mod_mask()
                if event.state & modifiers == gdk.ModifierType.CONTROL_MASK:
                    color_hex = G.colors["blue"]
                    color = gdk.color_parse(color_hex)
                    colorRGBA = color.red_float, color.green_float, color.blue_float, G.arrowRGBA[3]
                elif event.state & modifiers == gdk.ModifierType.SHIFT_MASK:
                    color_hex = G.colors["red"]
                    color = gdk.color_parse(color_hex)
                    colorRGBA = color.red_float, color.green_float, color.blue_float, G.arrowRGBA[3]
                elif event.state & modifiers == gdk.ModifierType.SHIFT_MASK | gdk.ModifierType.CONTROL_MASK:
                    color_hex = G.colors["yellow"]
                    color = gdk.color_parse(color_hex)
                    colorRGBA = color.red_float, color.green_float, color.blue_float, G.arrowRGBA[3]
                else:
                    colorRGBA = tuple(G.arrowRGBA)
                G.g.my_arrows[elem] = colorRGBA
                G.g.nags.add(arrow_nag(G.arrow_source, arrow_target, colorRGBA))

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
    '''Board mouse move callback.

    Used for drag and drop functionality.'''
    if G.drag_source != G.NULL_SQUARE:
        wx, wy = G.board_display.translate_coordinates(G.board_display.get_toplevel(), 0, 0)
        G.mouse_x = event.x + wx
        G.mouse_y = event.y + wy
        G.board_display.queue_draw()
    return False

@gui_callback
def board_scroll_event_callback(widget, event):
    '''Board scroll callback, used to run through game by scrolling.'''
    if event.direction == gdk.ScrollDirection.UP:
        go_back_callback()
    elif event.direction == gdk.ScrollDirection.DOWN:
        var_index = 0
        modifiers = gtk.accelerator_get_default_mod_mask()
        if event.state & modifiers == gdk.ModifierType.CONTROL_MASK:
            var_index = 2
        elif event.state & modifiers == gdk.ModifierType.SHIFT_MASK:
            var_index = 1
        elif event.state & modifiers == gdk.ModifierType.SHIFT_MASK | gdk.ModifierType.CONTROL_MASK:
            var_index = 3
        go_forward_callback(var_index=var_index)
    return False

@gui_callback
def engine_textview_mouse_down_callback(widget, event):
    if event.button == 2:
        # Middle click
        next_engine_callback(initialize_new=True)
        return True
    if event.button == 3:
        # Right click
        next_engine_callback(initialize_new=False)
        return True

    return False # Keeps highlight and copy functionality

@gui_callback
@documented
def load_repertoire_callback(*args):
    try:
        G.repertoire_file_name = args[0]
    except:
        display_status("No repertoire file given.")
        return False
    try:
        rep2 = Repertoire(G.repertoire_file_name)
        if G.rep:
            G.rep.flush()
            G.rep.close()
        G.rep = rep2
    except:
        display_status("Error loading repertoire '%s'." % G.repertoire_file_name)
    mark_nodes(G.g.root())
    update_pgn_message()
    return False

@gui_callback
@documented
def opening_size_callback(*args):
    '''Displays number of positions that would appear in an opening test using the current position.
    
    (See opening_test_callback).'''
    if G.rep:
        opening_game = create_opening_game(None, G.rep, G.player, G.g)
        count = countNodes(opening_game, color=G.player)
        count -= G.g.readonly_board.fullmove_number - 1
        display_status("Opening size: %d" % count)
    else:
        display_status("No repertoire file loaded.")
    return False

@gui_callback
@documented
def delete_opening_node_callback(*args):
    '''Deletes the current node from the repertoire.'''
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
@documented
def set_proper_save_format_callback(*args):
    '''Sets save format to not use extended NAG format.

    (This program can save arrows in PGN files,
    but only by using an extended NAG format that isn't standard.)'''
    G.proper_save_format = True
    return False

@gui_callback
@documented
def set_extended_save_format_callback(*args):
    '''Sets save format to use extended NAG format.

    (This program can save arrows in PGN files,
    but only by using an extended NAG format that isn't standard.)'''
    G.proper_save_format = False
    return False

@gui_callback
@documented
def save_callback(*args):
    '''Saves current game to specified file.
    
    Uses preset save file name if none is specified.'''
    if len(args) > 0:
        save_file_name = args[0]
    else:
        save_file_name = G.save_file_names[G.currentGame]
    save_current_pgn(save_file_name, show_status=True, prelude=None, set_global_save_file=True, proper_format=G.proper_save_format)
    return False

@gui_callback
@documented
def save_as_callback(*args):
    dialog = gtk.FileChooserDialog(title="Choose save location", parent=G.window, action=gtk.FileChooserAction.SAVE)
    dialog.add_buttons(gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL, gtk.STOCK_SAVE, gtk.ResponseType.OK)
    response = dialog.run()
    filename = dialog.get_filename()
    dialog.destroy()
    if response == gtk.ResponseType.OK:
        save_callback(filename)
    return False

@gui_callback
@documented
def open_pgn_textview_callback(*args):
    '''Toggles appearance of textview that displays game PGN.'''
    # Extract modifier keys
    if G.pgn_textview_enabled:
        G.board_h_box.remove(G.scrolled_window)
    else:
        G.board_h_box.pack_end(G.scrolled_window, True, True, 0)
        G.board_h_box.show_all()
    G.pgn_textview_enabled = not G.pgn_textview_enabled
    update_pgn_message()
    return False

@gui_callback
@documented
def analyze_callback(*args):
    '''Opens a separate instance of the program to analyze current game.

    For now, this ignores useful command line args of the original instance
    such as tablebase path, so use cautiously.'''
    movePath = []
    node = G.g
    while node.parent != None:
        movePath.append(node.parent.variations.index(node))
        node = node.parent
    movePath.reverse()
    prelude = '%' + " ".join(map(str, movePath))
    save_current_pgn(save_file_name="game.temp", show_status=False, prelude=prelude)
    # Currently, sys.argv is trimmed in gui.py so that its value here makes sense
    subprocess.Popen(["python3"] + sys.argv + ["game.temp"])
    return False

@gui_callback
@documented
def add_pieces_callback(*args):
    '''Opens a new game starting from the current position with the specified piece additions.

    Args: [w] [white_piece_addition1] ... [b] [black_piece_addition1] ...
    The piece additions above are just the square name for pawns, 
    and the piece letter followed by the square name for pieces.
    All entries up to the 'b' (or some other accepted specifier of black) will
    be assumed to be for the white side.'''
    board = G.g.board()
    color = chess.WHITE
    additions = {} # Saving changes to dictionary before implementing in case of error

    # Parse inputs
    for piece_string in args:
        if len(piece_string) == 2:
            piece = chess.Piece(chess.PAWN, color)
            square = chess.SQUARE_NAMES.index(piece_string)
            additions[square] = piece
        elif len(piece_string) == 3:
            piece = chess.Piece.from_symbol(piece_string[0])
            piece.color = color
            square = chess.SQUARE_NAMES.index(piece_string[-2:])
            additions[square] = piece
        else:
            parse_result = parse_side(piece_string)
            if parse_result == None:
                display_status("Syntax error in piece list. Leaving board unchanged.")
                return
            else:
                color = parse_result

    # Implement changes
    for square, piece in additions.items():
        board.set_piece_at(square, piece)
    load_new_game_from_board(board)

@gui_callback
@documented
def remove_pieces_callback(*args):
    '''Creates new game starting at current position, but with removed pieces at the specified squares.

    Empty squares are ignored without error, 
    but a single syntax error on a square name prevents any changes.'''
    board = G.g.board()
    errors = []
    for square_string in args:
        if square_string.lower() == "all":
            board.clear()
            break
        try:
            square = chess.SQUARE_NAMES.index(square_string)
            board.remove_piece_at(square)
        except ValueError:
            errors.append(square_string)
            break
    if len(errors) > 0:
        display_status("Try again. Errors with these square names: %s", " ".join(errors))
        return
    load_new_game_from_board(board)

@gui_callback
@documented
def set_castling_callback(*args):
    '''Creates new game starting at current position, but with the specified castling rights.
    
    All of the old castling rights are replaced with the new given castling rights.'''
    board = G.g.board()
    if len(args) != 1:
        display_status("Too many or too few arguments. Try again.")
        return
    board.castling_rights = 0
    if 'K' in args[0]:
        board.castling_rights |= chess.BB_H1
    if 'Q' in args[0]:
        board.castling_rights |= chess.BB_H1
    if 'k' in args[0]:
        board.castling_rights |= chess.BB_H8
    if 'q' in args[0]:
        board.castling_rights |= chess.BB_A8
    load_new_game_from_board(board)

@gui_callback
@documented
def set_en_passant_callback(*args):
    '''Creates new game starting at current position, but with the newly specified en_passant square.'''
    board = G.g.board()
    if len(args) != 1:
        display_status("Too many or too few arguments. Try again.")
        return
    try:
        square = chess.SQUARE_NAMES.index(args[0])
        board.ep_square = square
    except ValueError:
        display_status("Invalid square name given.")
        return
    load_new_game_from_board(board)

@gui_callback
@documented
def flip_turn_callback(*args):
    '''Loads new game with current position but opposite (or specified) side to move.'''
    board = G.g.board()
    if len(args) >= 1:
        side = parse_side(args[0])
        if side != None:
            if side == board.turn:
                display_status("It is already that side's turn.")
                return
            else:
                board.turn = side
        else:
            display_status("Invalid arguments.")
            return
    else:
        board.turn = not board.turn
    load_new_game_from_board(board)

@gui_callback
@documented
def toggle_stockfish_callback(*args):
    '''Toggles the main engine.'''
    engine = G.engines[G.current_engine_index]
    if engine.is_initialized() == False:
        # Start up engine
        engine.board = G.g.board()
        engine.engine_async_loop.call_soon_threadsafe(engine.engine_enabled_event.set)
        G.stockfish_textview.show_all()
    elif engine.engine_enabled_event.is_set():
        # Turn stockfish off
        G.stockfish_textview.hide()
        engine.stop()
    else:
        # Turn stockfish on
        engine.cont(G.g.board())
        G.stockfish_textview.show_all()
    return False

@gui_callback
@documented
def start_engine_callback(*args):
    '''Starts engine analysis for current position.'''
    engine = G.engines[G.current_engine_index]
    if not engine.is_initialized() or not engine.engine_enabled_event.is_set():
        # Engine is off, use toggle_stockfish_callback
        return toggle_stockfish_callback()
    # Engine is already on
    engine.cont(G.g.board())
    return False

@gui_callback
@documented
def next_engine_callback(initialize_new=False, *args):
    '''Gets the next engine to analyze.'''
    # Parse text input
    if type(initialize_new) == str:
        lower = initialize_new.lower()
        if lower == "true":
            initialize_true = True
        elif lower == "false":
            initialize_true = False
        else:
            return True # Bad argument, doing nothing
    # Do nothing if old engine isn't displayed and running
    current_engine = G.engines[G.current_engine_index]
    if current_engine.task == None or not current_engine.is_initialized():
        return True 
    current_engine.stop()
    G.current_engine_index = (G.current_engine_index + 1) % len(G.engines)
    if not initialize_new:
        # This can lead to an infinite loop if misused.
        while not G.engines[G.current_engine_index].is_initialized(): 
            G.current_engine_index = (G.current_engine_index + 1) % len(G.engines)
    return start_engine_callback()

@gui_callback
@documented
def engine_match_callback(time_control=G.default_match_time_control, player_engine="leela", other_engine="stockfish"):
    # Set white and black based on perspective
    if G.player == chess.WHITE:
        white_engine, black_engine = player_engine, other_engine
    else:
        white_engine, black_engine = other_engine, player_engine
    
    print("Starting engine match %s vs %s" % (white_engine, black_engine), file=sys.stderr)

    # Start playing thread
    threading.Thread(target=lambda : asyncio.run(engine_match_wrapper(white_engine, black_engine, time_control, G.g)), daemon=True).start()

@gui_callback
@documented
def stop_match_callback():
    if G.current_match_task:
        G.match_async_loop.call_soon_threadsafe(G.current_match_task.cancel)
    return False

@gui_callback
@documented
def toggle_pv_callback(*args):
    '''Toggles whether engine analysis shows pv line or just score.'''
    if len(args) > 0:
        G.show_engine_pv = bool(int(args[0]))
    else:
        G.show_engine_pv = not G.show_engine_pv
    return False

@gui_callback
@documented
def set_multipv_1_callback(*args):
    '''Sets engine multiPV to 1.'''
    G.multipv = 1
    return False

@gui_callback
@documented
def set_multipv_2_callback(*args):
    '''Sets engine multiPV to 2.'''
    G.multipv = 2
    return False

@gui_callback
@documented
def set_multipv_3_callback(*args):
    '''Sets engine multiPV to 3.'''
    G.multipv = 3
    return False

@gui_callback
@documented
def set_multipv_4_callback(*args):
    '''Sets engine multiPV to 4.'''
    G.multipv = 4
    return False

@gui_callback
@documented
def set_multipv_5_callback(*args):
    '''Sets engine multiPV to 5.'''
    G.multipv = 5
    return False

@gui_callback
@documented
def set_multipv_callback(*args):
    try:
        G.multipv = int(args[0])
    except:
        return False

@gui_callback
@documented
def play_move_callback(*args):
    # Casework on whether engine is currently enabled
    engine = G.engines[G.current_engine_index]
    if engine.engine_enabled_event.is_set():
        if engine.board == G.g.board():
            try:
                move = engine.best_move
                make_move(move)
                G.board_display.queue_draw()
                # Start analyzing new position
                start_engine_callback()
            except:
                pass
                display_status("Error finding move.")
        else:
            display_status("Cannot play engine move: engine currently analyzing a different position.")
    else:
        # TODO: This won't work right now
        pass
        
        ## Make sure engine has been initialized
        #if G.stockfish == None:
        #    # Start up stockfish
        #    G.stockfish = engine_init()

        #print(G.playLevel)
        #G.stockfish.process.process.send_signal(signal.SIGCONT)
        #G.stockfish.stop()
        #G.stockfish.info_handlers[0].curr_pos = G.g.board()
        #G.stockfish.isready()
        #G.stockfish.position(G.stockfish.info_handlers[0].curr_pos)
        #G.stockfish.isready()

        #try:
        #    # Use G.playLevel type to determine depth or time
        #    # Depth - int, time - float
        #    if type(G.playLevel) == int:
        #        # Use depth
        #        analysis_result = G.stockfish.go(depth=G.playLevel)
        #    else:
        #        # Use time
        #        analysis_result = G.stockfish.go(wtime=G.playLevel * 1000)
        #    make_move(analysis_result[0])
        #    G.board_display.queue_draw()
        #except Exception as e:
        #    display_status("Unexpected error finding or making engine move.")
        #    print(e)
    return False

@gui_callback
@documented
def play_training_move_callback(*args):
    # Play engine in training mode
    G.weak_engine_async_loop.call_soon_threadsafe(G.weak_engine_enabled_event.set)
    return False

@gui_callback
def load_fen_callback(*args):
    '''Graphical way to load FEN or PGN file.'''
    promptMessage = "Enter FEN or path to PGN file"
    prompt(G.window, promptMessage, load_fen_entry_callback)
    return False

@gui_callback
@documented
def make_report_callback(*args):
    '''Makes opening repertoire based on current position, perspective, and repertoire.'''
    make_report()
    return False

@gui_callback
@documented
def puzzle_file_name_callback(*args):
    try:
        G.puzzle_file = args[0]
    except:
        display_status("No file name given.")
    return False

@gui_callback
@documented
def save_puzzle_callback(*args):
    G.rep.add_initial_position(G.g.board(), save=True)
    color = G.g.board().turn
    for node in real_dfs(G.g):
        if len(args) > 0 and args[0] == 'all':
            indices = range(0, len(node.variations))
        else:
            indices = [0] if len(node.variations) > 0 else []
        for i in indices:
            child = node.variation(i)
            b = node.board()
            if b.turn == color:
                G.rep.appendTactic(b, child.move)
            else:
                G.rep.appendTactic(b, child.move, 1, 0) # Don't learn both sides
    G.rep.flush()

    return False

@gui_callback
@documented
def add_tactics_child_callback(*args):
    '''Adds the parent board and move leading up to current position to tactics repertoire.'''
    if G.g.parent != None:
        parent_board = G.g.parent.readonly_board
        if G.player == parent_board.turn:
            G.rep.appendTactic(parent_board, G.g.move)
        else:
            # Don't learn if move from opposite player
            G.rep.appendTactic(parent_board, G.g.move, 1, 0)

#@gui_callback
#@documented
#def load_puzzle_callback(*args):
#    fil = open(G.puzzle_file, 'r')
#    if len(args) > 0:
#        # A specific puzzle was specified by index
#        try:
#            puzzle_index = int(args[0])
#        except:
#            display_status("Puzzle index entered is not an integer.")
#            fil.close()
#            return False
#        for i in range(2 * puzzle_index):
#            fil.readline()
#        position_fen = fil.readline().strip()
#        position_comment = fil.readline().strip()
#        fil.close()
#        if position_fen != "":
#            load_new_game_from_board(chess.Board(position_fen))
#            display_status(position_comment)
#            return False
#        else:
#            display_status("Puzzle index given too large.")
#            return False
#    else:
#        # Load random puzzle
#        puzzles = []
#        comments = []
#        while True:
#            position = fil.readline().strip()
#            if position == "":
#                break
#            puzzles.append(position)
#            comments.append(fil.readline().strip())
#        fil.close()
#        if len(puzzles) == 0:
#            display_status("No puzzles available!")
#            return False
#        puzzle_number = random.randrange(len(puzzles))
#        load_new_game_from_board(chess.Board(puzzles[puzzle_number]))
#        display_status(comments[puzzle_number])
#        return False

@gui_callback
@documented
def set_to_learn_callback(*args):
    '''Sets up spaced repetition for the current position with current perspective, as well as any parents.'''
    if G.rep:
        # Note the following does nothing if position isn't in repertoire already,
        # or if it is already learnable
        G.rep.make_position_learnable(G.g.board(), G.player)
        G.rep.flush()
        mark_nodes(G.g)
        update_pgn_message()
    return False

@gui_callback
@documented
def unlearn_callback(*args):
    '''Removes a position+move from spaced repetition, but keeps it in repertoire.'''
    if G.rep:
        for var in G.g.variations:
            G.rep.remove_learning_data(G.player, G.g.board(), var.move)
        G.rep.flush()
        mark_nodes(G.g)
        update_pgn_message()
    return False

@gui_callback
@documented
def set_game_to_learn_callback(*args):
    '''Sets up spaced repetition for all special and book nodes in current game.'''
    if G.rep:
        learn_special_nodes(G.g.root())
        G.rep.flush()
        mark_nodes(G.g.root())
        update_pgn_message()
    return False


@gui_callback
@documented
def reset_learn_callback(*args):
    '''Resets spaced repetition learning data as new item.'''
    if G.rep:
        G.rep.make_position_learnable(G.g.board(), G.player, override=True)
        G.rep.flush()
    return False

@gui_callback
@documented
def reset_learn_timer_callback(*args):
    '''Resets spaced repetition information (for use when going afk or mouse slipping in session).'''
    G.ot_info.reset_question_info()
    display_status("Reset training timer.")
    return False

@gui_callback
@documented
def show_learn_info_callback(*args):
    '''Shows learning information stored for a position.
    
    Not implemented yet.'''
    # Select current position, or a position specified by given FEN
    board = G.g.board()
    if len(args) > 0 and type(args[0]) == str:
        try:
            board = chess.Board(fen=args[0])
        except:
            display_status("Invalid FEN given")
            return False
    # TODO: Find position in repertoire, and give stored easiness, number of consecutive
    # correct answers, and the next time to train it
    return False

@gui_callback
@documented
def print_schedule_callback(*args):
    '''Prints schedule of upcoming spaced repetition exercises.'''
    lines = 100
    try:
        lines = int(args[0])
    except:
        pass
    get_learning_schedule(G.g.board(), G.player, max_lines=lines)

@gui_callback
def textview_mouse_pressed_callback(widget, event):
    text_window = gtk.TextWindowType.WIDGET
    pressed_tuple = widget.window_to_buffer_coords(text_window, event.x, event.y)
    G.textview_pressed_text_iter = G.pgn_textview.get_iter_at_location(pressed_tuple[0], pressed_tuple[1])[1] # Yeah...the [1] is necessary, which is ridiculous
    # Now we're looking for the beginning of the word, and gtk's starts_word doesn't work with castling moves
    G.textview_pressed_text_iter.backward_find_char(lambda x, _ : x.isspace())
    G.textview_pressed_text_iter.forward_char()
    return False

@gui_callback
def textview_mouse_released_callback(widget, event):
    if G.textview_pressed_text_iter != None:
        text_window = gtk.TextWindowType.WIDGET
        released_tuple = widget.window_to_buffer_coords(text_window, event.x, event.y)
        text_iter = G.pgn_textview.get_iter_at_location(released_tuple[0], released_tuple[1])[1] # Yeah...the [1] is necessary, which is ridiculous
        # Now we're looking for the beginning of the word, and gtk's starts_word doesn't work with castling moves
        text_iter.backward_find_char(lambda x, _ : x.isspace())
        text_iter.forward_char()
        if G.textview_pressed_text_iter.equal(text_iter): # The == operator isn't overloaded
            try:
                G.g = G.bufferToNodes[text_iter.get_offset()]
                update_pgn_textview_move(G.g)
            except KeyError:
                pass
            G.board_display.queue_draw()
    G.textview_pressed_text_iter = None
    return False

@gui_callback
def pgn_textview_key_press_callback(widget, event):
    return True

@gui_callback
@documented
def enter_analysis_mode_callback(*args):
    '''Starts the (default) analysis mode.

    Intended to be used to switch back to analysis mode from opening test mode.
    This switch also happens automatically when an opening test is completed.'''
    G.move_completed_callback = lambda x : None
    return False

@gui_callback
@documented
def enter_opening_test_mode_callback(*args):
    '''Starts test mode using current position (from current perspective) as start.
    
    Unlike opening_test_callback, this does not start a new subprocess.
    To get back to analysis mode, see enter_analysis_mode_callback.
    Not sure if this still works.'''
    if G.ot_board == None:
        G.ot_board = chess.Board(G.g.readonly_board.fen()) # To strip board history
        G.ot_gen = None
    setup_ot_mode()
    return False

@gui_callback
@documented
def reset_test_mode_callback(*args):
    '''Restarts an opening test mode from the start.
    
    This does not necessarily produce the exact same test again.
    (For example, when using learn mode.)'''
    G.ot_board = G.g.board()
    G.ot_gen = None
    setup_ot_mode()
    return False

@gui_callback
@documented
def run_script_callback(*args):
    '''Runs a script.

    A script here is a file with a list of commands that could be input
    in the entry bar.'''
    # TODO: Create scripting language to allow arguments, loops, etc
    try:
        fil = open(args[0])
    except:
        display_status("Could not open file '%s'" % args[0])
        return False
    for line in fil:
        words = shlex.split(line)
        if words[-1] == "&":
            words = words[:-1]
            entry_bar_callback(" ".join(words))
        else:
            thread = entry_bar_callback(" ".join(words))
            thread.join()
    return False

@gui_callback
@documented
def insert_mode_callback(*args):
    G.entry_bar.grab_focus()
    return False

@gui_callback
def entry_bar_callback(widget):
    if type(widget) == str:
        text = widget
    else:
        text = widget.get_text()
    
    def f():
        args = shlex.split(text)
        while True:
            # Check for &&
            try:
                separator_index = args.index('&&')
                rest = args[separator_index + 1:]
                args = args[:separator_index]
            except ValueError:
                rest = []

            # Save in history
            if args:
                G.command_history.append(text)

            while args:
                # Try to parse moves
                move = None
                try:
                    move = G.g.readonly_board.parse_san(args[0])
                except ValueError:
                    pass

                if move:
                    # Legal move given
                    make_move(move)
                    G.board_display.queue_draw()
                    if type(widget) != str: 
                        GLib.idle_add(widget.set_text, "")
                    G.command_index = 0
                    del args[0]
                else:
                    # Command given
                    if args[0] in G.command_callbacks:
                        future_callback = G.command_callbacks[args[0]](*args[1:])
                        if type(widget) != str: 
                            GLib.idle_add(widget.set_text, "")
                        if callable(future_callback):
                            future_callback()
                        G.command_index = 0
                    break
            
            if rest:
                args = rest
            else:
                break
    thread = threading.Thread(target=f)
    thread.start()

    if type(widget) == str:
        # Internal calls don't need to return booleans like GTK ones
        return thread

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
                moves = map(lambda m: G.g.readonly_board.san(m), G.g.readonly_board.legal_moves)
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
            # For now, we'll just assume this should be file, color, engine, or NAG completion
            partial = words[-1]
            prev = " ".join(words[:-1]) + " "
            path, tail = os.path.split(partial)
            try:
                # File completion
                candidates = list(filter(lambda x: x[0:len(tail)] == tail, os.listdir(path if path != '' else '.')))
            except:
                return True
            # NAG or color completion
            # TODO: Only apply these for appropriate commands
            candidates += list(filter(lambda x : x[0:len(tail)] == tail, G.nag_set.union(set(G.colors)).union(set(G.engine_commands))))
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
    # Return focus outside of entry
    if event.keyval in G.escapeKeys:
        G.board_display.grab_focus()
        return False
    
    # Check if focus is on entry bar
    # Shortcuts with modifiers should be handled regardless, 
    # except Ctrl-C and Ctrl-V
    if G.entry_bar.is_focus() and (event.state & G.modifier_mask == 0 or (event.state & G.modifier_mask == gdk.ModifierType.CONTROL_MASK and event.keyval in [gdk.KEY_c, gdk.KEY_v])):
        return False

    # Select dictionary for current modifiers
    # TODO: Add support for Shift + F?, which currently is unsupported
    # as G.modifier_mask does not include Shift (to avoid conflicts
    # with letter being pressed using shift or not).
    try:
        binding_map = G.key_binding_maps[event.state & G.modifier_mask]
    except:
        return False

    # Run callback
    if event.keyval in binding_map:
        value = binding_map[event.keyval]
        # This is for compatability with delayed entry bar callbacks
        while callable(value):
            value = value()
        return True

    return False

@gui_callback
@documented
def exit_callback(*args):
    '''Wrapper for destroy_main_window_callback to destroy main window.'''
    return destroy_main_window_callback()

# Other callbacks

@gui_callback
@documented
def destroy_main_window_callback(widget=None):
    '''Destroy main window callback. Provides cleanup code for things like stockfish, etc, as well.'''
    G.glib_mainloop.quit()
    for e in G.engines:
        if e.transport != None:
            e.transport.send_signal(signal.SIGCONT)
    return False

def signal_handler(signum=None):
    '''Signal handling (SIGINT or SIGTERM). Cleans up child processes and exits.'''
    # signum is ignored because this handler is only registered elsewhere
    # for SIGINT and SIGTERM. If that changes, this function needs to be changed
    # appropriately.
    exit(0)
