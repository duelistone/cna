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
import signal, math
from helper import make_move

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
