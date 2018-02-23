# engine.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import chess, chess.uci
import global_variables as G
import signal, math

'''Module for functions for working with engine.'''

# Convert score object to string description of score
def score_to_string(score, color):
    if score.cp != None:
        scoreNum = score.cp
        if color == chess.BLACK: scoreNum *= -1
        string_cp = str(scoreNum)
        return string_cp
    mateNum = score.mate
    if color == chess.BLACK: mateNum *= -1
    return "M" + str(mateNum)

# Extract best current move
# The engine should be running on the correct position
def find_current_best_move(engine):
    handler = engine.info_handlers[0]
    with handler:
        return handler.info['pv'][1][0] # This could raise an exception if conditions aren't just right

# Standard infinite go
def engine_go(engine):
    engine.position(engine.info_handlers[0].curr_pos)
    engine.go(infinite=True, async_callback=True)

# Prepare engine
def engine_init():
    engine = chess.uci.popen_engine("stockfish")
    engine.uci()
    engine.setoption({"MultiPV" : G.NUM_VARIATIONS, "Hash" : G.HASH_SIZE, "Threads" : G.NUM_THREADS, "SyzygyPath" : "/home/duelist/tb/tablebases"})
    info_handler = MyInfoHandler()
    engine.info_handlers.append(info_handler)
    engine.isready()
    return engine

def weak_engine_init(level):
    weak_engine = chess.uci.popen_engine("stockfish")
    weak_engine.uci()
    weak_engine.setoption({"Skill Level": level})
    weak_engine.level = level
    info_handler = EvalInfoHandler()
    weak_engine.info_handlers.append(info_handler)
    weak_engine.isready()
    return weak_engine

def score_to_level(score, defaultLevel):
    levelSize = 50
    levelsFromEqual = int(abs(score / levelSize))
    sign = int(score / abs(score))
    proposal = defaultLevel - sign * levelsFromEqual
    print(proposal)
    if proposal < 0: 
        proposal = 0
    elif proposal > 20:
        proposal = 20
    return proposal

def change_level(engine, new_level):
    # Meant for usage with a weak_engine
    engine.setoption({"Skill Level": new_level})
    engine.isready()
    engine.level = new_level

def change_multipv(n):
    if G.stockfish != None:
        G.stockfish.process.process.send_signal(signal.SIGCONT)
        G.stockfish.stop()
    G.NUM_VARIATIONS = n
    if G.stockfish != None:
        G.stockfish.setoption({"MultiPV" : G.NUM_VARIATIONS, "Hash" : G.HASH_SIZE, "Threads" : G.NUM_THREADS, "SyzygyPath" : "/home/duelist/tb/tablebases"})
        G.stockfish.isready()

# Display analysis lines
def display_stockfish_string(s):
    GLib.idle_add(lambda x : G.stockfish_buffer.set_text(x), s)

# Simple handler to keep track of evaluation of search
class EvalInfoHandler(chess.uci.InfoHandler):
    def __init__(self):
        super(EvalInfoHandler, self).__init__()
        self.e = 0 # To store current eval

    def score(self, cp, mate, lowerbound, upperbound):
        if not lowerbound and not upperbound:
            self.e = chess.uci.Score(cp, mate)
        super(EvalInfoHandler, self).score(cp, mate, lowerbound, upperbound)

# Handler to receive data from engine
class MyInfoHandler(chess.uci.InfoHandler):
    def __init__(self):
        super(MyInfoHandler, self).__init__()
        self.curr_pos = None # A board for the current position
        self.curr_depth = None
        self.curr_pv = None
        self.curr_multipv = None
        self.curr_score = None
        self.curr_time = None
        self.curr_tbhits = None
        self.curr_hashfull = 0
        self.curr_nps = None
        self.curr_nodes = None
        self.lines = [""] * (G.NUM_VARIATIONS + 1) # TODO: Fill first info line

    def on_go(self):
        self.lines = [""] * (G.NUM_VARIATIONS + 1)
        super(MyInfoHandler, self).on_go()

    def time(self, x):
        self.curr_time = x / 1000.0
        super(MyInfoHandler, self).time(x)

    def tbhits(self, x):
        self.curr_tbhits = x
        super(MyInfoHandler, self).tbhits(x)

    def hashfull(self, x):
        self.curr_hashfull = x / 10.0
        super(MyInfoHandler, self).hashfull(x)

    def nps(self, x):
        self.curr_nps = x
        super(MyInfoHandler, self).nps(x)

    def nodes(self, x):
        self.curr_nodes = x
        super(MyInfoHandler, self).nodes(x)

    def depth(self, x):
        self.curr_depth = x
        super(MyInfoHandler, self).depth(x)

    def pv(self, moves):
        self.curr_pv = moves
        super(MyInfoHandler, self).pv(moves)

    def multipv(self, num):
        self.curr_multipv = num
        super(MyInfoHandler, self).multipv(num)

    def score(self, cp, mate, lowerbound, upperbound):
        if not lowerbound and not upperbound:
            self.curr_score = chess.uci.Score(cp, mate)
        else:
            self.curr_score = None
        super(MyInfoHandler, self).score(cp, mate, lowerbound, upperbound)

    def post_info(self):
        # First line (stats)
        if None not in [self.curr_time, self.curr_tbhits, self.curr_hashfull, self.curr_nps, self.curr_nodes]:
            self.lines[0] = "Time: %.1f TB: %d Hash: %.1f%% NPS: %.0f Nodes: %d" % (self.curr_time, self.curr_tbhits, self.curr_hashfull, self.curr_nps, self.curr_nodes)

        # Received line
        if None not in [self.curr_depth, self.curr_pv, self.curr_multipv, self.curr_score]:
            words = []
            words.append(str(self.curr_depth))
            words.append(score_to_string(self.curr_score, self.curr_pos.turn))
            # Go through move list
            sanList = []
            p = self.curr_pos.copy()
            for move in self.curr_pv:
                try:
                    sanMove = p.san(move)
                    p.push(move)
                except:
                    break
                if p.turn == chess.BLACK:
                    sanList.append(str(p.fullmove_number) + '. ' + sanMove)
                else:
                    sanList.append(sanMove)
            if len(sanList) > 0 and self.curr_pos.turn == chess.BLACK:
                sanList[0] = str(self.curr_pos.fullmove_number) + '...' + sanList[0]
            words.extend(sanList)
            self.lines[self.curr_multipv] = " ".join(words)

        display_stockfish_string("\n".join(self.lines))
        super(MyInfoHandler, self).post_info()

