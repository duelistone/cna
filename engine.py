# engine.py

import gi
import asyncio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.engine
import global_variables as G
import signal, math

'''Module for functions for working with engine.'''

asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())

# Extract best current move
# The engine should be running on the correct position
def find_current_best_move(engine):
    return G.engine_best_move

# Standard infinite go
async def engine_go(engine):
    while 1:
        with await engine[1].analysis(G.engine_board, multipv=G.multipv) as analysis:
            print("New analysis!")
            old_board = G.engine_board
            old_multipv = G.multipv
            async for info in analysis:
                await G.engine_enabled_event.wait()
                if G.engine_board != old_board or G.multipv != old_multipv:
                    break
                parse_engine_data(info)
                save_best_move(info)

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
    words.extend(sanList)
    if info.get("multipv") != None:
        G.latest_engine_lines[info.get("multipv") - 1] = " ".join(words)
    else:
        # Some engines (leela) don't specify multipv in multipv=1 mode.
        G.latest_engine_lines[0] = " ".join(words)
    lines.extend(G.latest_engine_lines)

    display_stockfish_string("\n".join(lines))

# Prepare engine
async def engine_init():
    G.engine_enabled_event = asyncio.Event()
    await G.engine_enabled_event.wait()
    G.stockfish = await chess.engine.popen_uci(G.engine_command)
    await G.stockfish[1].configure(G.engine_settings[G.engine_command])
    await engine_go(G.stockfish)

# Display analysis lines
def display_stockfish_string(s):
    GLib.idle_add(lambda x : G.stockfish_buffer.set_text(x), s)

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

def weak_engine_init(level):
    weak_engine = uci.popen_engine("stockfish")
    weak_engine.uci()
    weak_engine.setoption({"Skill Level": level})
    weak_engine.level = level
    info_handler = EvalInfoHandler()
    weak_engine.info_handlers.append(info_handler)
    weak_engine.isready()
    return weak_engine

def change_level(engine, new_level):
    # Meant for usage with a weak_engine
    engine.setoption({"Skill Level": new_level})
    engine.isready()
    engine.level = new_level


