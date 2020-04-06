# engine.py

import gi
import asyncio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.engine
from chess.engine import Cp, Mate, MateGiven
import global_variables as G
import signal, math, time, sys
from helper import make_move, mark_nodes, update_pgn_message

'''Module for functions for working with engine.'''

# The init functions are started in a separate thread in main

asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())

# Class for engine analysis

class AnalysisEngine(object):
    def __init__(self, engine_command):
        # Command and settings
        self.command = engine_command
        self.settings = G.engine_settings[engine_command]
        # Bookkeeping for analysis
        self.board = chess.Board() # Should be set before starting analysis for first time
        self.output = ""
        self.latest_engine_stats = [-1, -1, -1, -1, -1]
        self.latest_engine_lines = []
        #self.displayed = False # For later use
        # Declarations
        self.engine_enabled_event = None # Must be defined in async_init thread. This introduces a race condition.
        self.engine_async_loop = None # Same
        self.transport = None
        self.protocol = None
        self.task = None
        self.best_move = None

    async def async_init(self):
        self.engine_async_loop = asyncio.get_running_loop()
        self.engine_enabled_event = asyncio.Event()
        await self.engine_enabled_event.wait()
        self.transport, self.protocol = await chess.engine.popen_uci(self.command)
        await self.protocol.configure(self.settings)
        await self.go()

    async def go(self):
        while 1:
            await self.engine_enabled_event.wait()
            with await self.protocol.analysis(self.board, multipv=G.multipv, info=chess.engine.INFO_BASIC | chess.engine.INFO_SCORE | chess.engine.INFO_PV) as analysis:
                self.task = asyncio.create_task(self.handle_engine_info(analysis))
                try:
                    await self.task
                except asyncio.CancelledError:
                    self.task = None

    async def handle_engine_info(self, analysis):
        async for info in analysis:
            # Create output to display
            temp = self.parse_engine_data(info)
            if temp != None: 
                self.output = temp
                self.show_latest_info()

            # Save best move
            try:
                if info.get("multipv") in [1, None]:
                    self.best_move = info.get("pv")[0]
            except:
                pass

    def show_latest_info(self):
        # Later on, this will depend on self.displayed
        display_stockfish_string(self.output)

    def is_initialized(self):
        return self.protocol != None

    def stop(self):
        self.transport.send_signal(signal.SIGSTOP)
        self.engine_enabled_event.clear()
    
    def cont(self, board): # Cannot be called continue
        self.transport.send_signal(signal.SIGCONT)
        if self.board != board:
            self.engine_enabled_event.clear() # To make sure self.board is updated in time
            if self.task:
                self.engine_async_loop.call_soon_threadsafe(self.task.cancel)
            self.board = board
        self.engine_enabled_event.set()

    def parse_engine_data(self, info):
        # Skip if no useful data
        if None in map(lambda x : info.get(x), ["depth", "pv", "score"]):
            return

        lines = []

        # First line (stats)
        stats = tuple(map(lambda x : info.get(x), ["time", "tbhits", "hashfull", "nps", "nodes"]))
        for i, e in enumerate(stats):
            if e != None:
                self.latest_engine_stats[i] = e
            if i == 2:
                self.latest_engine_stats[i] /= 10.0
        lines.append("{0} Time: {1:.1f} TB: {2:,} Hash: {3:.1f}% NPS: {4:,} Nodes: {5:,}".format(*([self.command] + self.latest_engine_stats)))

        if len(self.latest_engine_lines) != G.multipv:
            self.latest_engine_lines = [""] * G.multipv

        # Keep track if upper bound or lower bound or normal output line
        bound = " "
        try:
            if info.get("lowerbound"):
                bound = '\u2265'
        except KeyError:
            pass
        try:
            if info.get("upperbound"):
                bound = '\u2264'
        except KeyError:
            pass

        # Other lines (PVs)
        # Note that each input has only information about one line
        words = []
        words.append(str(info.get("depth")))
        words.append(bound + str(info.get("score").pov(chess.WHITE)))

        # Go through move list
        if bound == ' ':
            sanList = []
            p = self.board.copy()
            for move in info.get("pv"):
                try:
                    sanMove = p.san(move)
                    p.push(move)
                except:
                    break
                if p.turn == chess.BLACK:
                    sanList.append(str(p.fullmove_number) + '. ' + sanMove)
                else:
                    sanList.append(sanMove)
            if len(sanList) > 0 and self.board.turn == chess.BLACK:
                sanList[0] = str(self.board.fullmove_number) + '...' + sanList[0]
            if G.show_engine_pv:
                words.extend(sanList)
        else:
            if info.get("multipv") != None:
                try:
                    words += self.latest_engine_lines[info.get("multipv") - 1].split()[2:]
                except IndexError:
                    pass
            else:
                words += self.latest_engine_lines[0].split()[2:]

        # Some engines (leela) don't specify multipv in multipv=1 mode, hence the casework
        if info.get("multipv") != None:
            # try/except is in case G.multipv is changed...this should be made less hacky
            try:
                self.latest_engine_lines[info.get("multipv") - 1] = " ".join(words)
            except IndexError:
                pass
        else:
            self.latest_engine_lines[0] = " ".join(words)
        lines.extend(self.latest_engine_lines)

        return "\n".join(lines)

# Engine match
async def engine_match(white_engine_name, black_engine_name, time_control, start_node):
    try:
        # Init engines
        G.match_async_loop = asyncio.get_running_loop()
        white_engine = await chess.engine.popen_uci(white_engine_name)
        black_engine = await chess.engine.popen_uci(black_engine_name)
        await white_engine[1].configure(G.engine_settings[white_engine_name])
        await black_engine[1].configure(G.engine_settings[black_engine_name])

        # Parse time controls
        wtime, winc, btime, binc = parse_time_control_string(time_control)
        
        # Playing loop
        node = start_node
        board = start_node.board()
        while True:
            # Stop conditions
            if board.is_game_over() or board.halfmove_clock >= 100 or board.is_repetition(3):
                # The second condition above is necessary to not claim a draw 
                # the turn before the repetition might or might not occur
                node.comment += " %s" % board.result(claim_draw=True)
                break
            if G.tablebase != None:
                tb_result = G.tablebase.get_wdl(board)
                if tb_result != None:
                    # Set result to white's perspective
                    if board.turn == chess.BLACK:
                        tb_result *= -1
                    if node.comment:
                        node.comment += " "
                    node.comment += "TB result: %d (%s)" % (tb_result, G.TABLEBASE_RESULTS[tb_result])
                    GLib.idle_add(update_pgn_message)
                    break

            # Actually play
            limits = chess.engine.Limit(white_clock=wtime, white_inc=winc, black_clock=btime, black_inc=binc)
            if board.turn == chess.WHITE:
                start_time = time.time()
                play_result = await white_engine[1].play(board, limits, ponder=True, info=chess.engine.INFO_SCORE)
                wtime -= time.time() - start_time - winc
            else:
                start_time = time.time()
                play_result = await black_engine[1].play(board, limits, ponder=True, info=chess.engine.INFO_SCORE)
                btime -= time.time() - start_time - binc
            print("(White time, Black time) = (%f, %f)" % (wtime, btime), file=sys.stderr)
            # TODO: Flagging, report time

            # Update comment
            if node.comment:
                node.comment += " "
            node.comment += "%s %d/%s" % (white_engine_name if board.turn == chess.WHITE else black_engine_name, play_result.info["depth"], str(play_result.info["score"].pov(chess.WHITE)))

            # Update game, node, and board
            if play_result.move in map(lambda v: v.move, node.variations):
                node = node.variation(play_result.move)
            elif play_result.move in node.readonly_board.legal_moves:
                node = node.add_variation(play_result.move)
            else:
                raise ValueError("Illegal move given by engine, aborting game.")
            mark_nodes(node)
            if node.parent == G.g:
                G.g = node
            GLib.idle_add(G.board_display.queue_draw)
            # TODO: This update can throw errors when the engines are making moves super quickly. 
            # I think this happens when G.g gets updated too quickly for update_pgn_textview_move
            # I think these errors are harmless, but they can briefly wipe out the GUI.
            # Update: Is this still true? (Haven't seen issues pop up in practice.)
            GLib.idle_add(update_pgn_message)
            board = node.board()
    finally:
        # Cleanup the large amount of resources used by engines
        await white_engine[1].quit()
        await black_engine[1].quit()
        GLib.idle_add(update_pgn_message) # A final catchup opportunity when engine moves too quickly

async def engine_match_wrapper(*args, **kwargs):
    # Wraps an engine_match call into a task
    # so it can be cancelled
    try:
        G.current_match_task = asyncio.create_task(engine_match(*args, **kwargs))
        await G.current_match_task
    except asyncio.CancelledError:
        pass

# Prepare weak engine
async def weak_engine_init():
    G.weak_engine_enabled_event = asyncio.Event()
    await G.weak_engine_enabled_event.wait()
    engine = await chess.engine.popen_uci("stockfish") # TODO: Flexible engine path
    score = 0
    board = G.g.board()
    while 1:
        play_result = await engine[1].play(board, limit=chess.engine.Limit(time=1), options={"Skill Level" : score_to_level(score, G.WEAK_STOCKFISH_DEFAULT_LEVEL)}, info=chess.engine.INFO_SCORE)
        GLib.idle_add(make_move, play_result.move)
        GLib.idle_add(G.board_display.queue_draw)
        score = play_result.info['score'].pov(board.turn).score(mate_score=10**6)
        G.weak_engine_enabled_event.clear()
        await G.weak_engine_enabled_event.wait()
        board = G.g.board()

# Helpers

# Display analysis lines
def display_stockfish_string(s):
    GLib.idle_add(G.stockfish_buffer.set_text, s)

def score_to_level(score, defaultLevel):
    levelSize = 50
    levelSizeLower = 2 * levelSize
    levelsFromEqual = int(abs(score / levelSize)) if score < 0 else -int(abs(score / levelSizeLower))
    proposal = defaultLevel + levelsFromEqual
    if proposal < 0: 
        proposal = 0
    elif proposal > 20:
        proposal = 20
    return proposal

def parse_time_control_string(s):
    time_control_strings = s.split(',')
    result = []
    for e in time_control_strings:
        e = e.split('+')
        result.append(60 * float(e[0]))
        result.append(float(e[1]))
    if len(result) == 4:
        return tuple(result)
    return result[0], result[1], result[0], result[1]

# TODO: Update functions below

# Change setting
#def change_engine_setting(name, value):
#    if G.stockfish != None:
#        G.stockfish.process.process.send_signal(signal.SIGCONT)
#        G.stockfish.stop()
#    G.engine_settings[G.engine_command].update({name: value})
#    if G.stockfish != None:
#        G.stockfish.setoption(G.engine_settings[G.engine_command])
#        engine_go(G.stockfish)
#        if not G.stockfish_enabled:
#            G.stockfish.process.process.send_signal(signal.SIGSTOP)
