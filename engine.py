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

# async coroutines
# The init functions are started in a separate thread in main

asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())

# Prepare engine
async def engine_init():
    G.engine_async_loop = asyncio.get_running_loop()
    G.engine_enabled_event = asyncio.Event()
    await G.engine_enabled_event.wait()
    G.stockfish = await chess.engine.popen_uci(G.engine_command)
    await G.stockfish[1].configure(G.engine_settings[G.engine_command])
    await engine_go(G.stockfish)

# Read and parse engine lines
async def handle_engine_info(analysis):
    async for info in analysis:
        parse_engine_data(info)
        save_best_move(info)
    
# Standard infinite go
async def engine_go(engine):
    while 1:
        await G.engine_enabled_event.wait()
        with await engine[1].analysis(G.engine_board, multipv=G.multipv, info=chess.engine.INFO_BASIC | chess.engine.INFO_SCORE | chess.engine.INFO_PV) as analysis:
            G.current_engine_task = asyncio.create_task(handle_engine_info(analysis))
            try:
                await G.current_engine_task
            except asyncio.CancelledError:
                pass

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
            if board.is_game_over(claim_draw=True):
                node.comment += " %s" % board.result(claim_draw=True)
                # TODO: If in principal variation, update result
                break
            if G.tablebase != None:
                tb_result = G.tablebase.get_wdl(board)
                if tb_result != None:
                    # Set result to white's perspective
                    if board.turn == chess.BLACK:
                        tb_result *= -1
                    if node.comment:
                        node.comment += " "
                    node.comment += "TB result: %d (%s)" % (tb_result, G.tablebase_results[tb_result])
                    GLib.idle_add(update_pgn_message)
                    # TODO: If in principal variation, update result
                    break

            # Actually play
            limits = chess.engine.Limit(white_clock=wtime, white_inc=winc, black_clock=btime, black_inc=binc)
            if board.turn == chess.WHITE:
                start_time = time.time()
                play_result = await white_engine[1].play(board, limits, info=chess.engine.INFO_SCORE)
                wtime -= time.time() - start_time - winc
            else:
                start_time = time.time()
                play_result = await black_engine[1].play(board, limits, info=chess.engine.INFO_SCORE)
                btime -= time.time() - start_time - binc
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

# Extract best current move
# The engine should be running on the correct position
def find_current_best_move(engine):
    return G.engine_best_move

def save_best_move(info):
    try:
        if info.get("multipv") in [1, None]:
            G.engine_best_move = info.get("pv")[0]
    except:
        pass

def parse_engine_data(info):
    # Skip if no useful data
    if None in map(lambda x : info.get(x), ["depth", "pv", "score"]):
        return

    lines = []

    # First line (stats)
    stats = tuple(map(lambda x : info.get(x), ["time", "tbhits", "hashfull", "nps", "nodes"]))
    for i, e in enumerate(stats):
        if e != None:
            G.latest_engine_stats[i] = e
        if i == 2:
            G.latest_engine_stats[i] /= 10.0
    lines.append("Time: %.1f TB: %d Hash: %.1f%% NPS: %.0f Nodes: %d" % tuple(G.latest_engine_stats))

    if len(G.latest_engine_lines) != G.multipv:
        G.latest_engine_lines = [""] * G.multipv

    # Other lines (PVs)
    # Note that each input has only information about one line
    words = []
    words.append(str(info.get("depth")))
    words.append(str(info.get("score").pov(chess.WHITE)))
    # Go through move list
    sanList = []
    p = G.engine_board.copy()
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
    if len(sanList) > 0 and G.engine_board.turn == chess.BLACK:
        sanList[0] = str(G.engine_board.fullmove_number) + '...' + sanList[0]
    if G.show_engine_pv:
        words.extend(sanList)
    if info.get("multipv") != None:
        G.latest_engine_lines[info.get("multipv") - 1] = " ".join(words)
    else:
        # Some engines (leela) don't specify multipv in multipv=1 mode.
        G.latest_engine_lines[0] = " ".join(words)
    lines.extend(G.latest_engine_lines)

    display_stockfish_string("\n".join(lines))

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
def change_engine_setting(name, value):
    if G.stockfish != None:
        G.stockfish.process.process.send_signal(signal.SIGCONT)
        G.stockfish.stop()
    G.engine_settings[G.engine_command].update({name: value})
    if G.stockfish != None:
        G.stockfish.setoption(G.engine_settings[G.engine_command])
        engine_go(G.stockfish)
        if not G.stockfish_enabled:
            G.stockfish.process.process.send_signal(signal.SIGSTOP)
