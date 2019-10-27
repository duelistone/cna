# constants.py

# Global variables that are just fixed constants (like const C++ variables)
ADD_MAIN_VARIATION = 1
ADD_LAST_VARIATION = -1
NULL_SQUARE = -1
DEFAULT_SQUARE_SIZE = 50
SR_FULL_LINE_PROBABILITY = 0.05
WEAK_STOCKFISH_DEFAULT_LEVEL = 4
COMMENT_ENTRY_SIZE = 256

nag_strings = 256 * [""]
nag_strings[1:24] = ["!", "?", "\u203c", "\u2047", "\u2049", "\u2048", "\u25a1", "\u25a1", "", "=", "", "", "\u221e", "\u2a72", "\u2a71", "\u00b1", "\u2213", "+-", "-+", "1-0", "0-1", "\u2a00", "\u2a00"] 
nag_strings[24:30] = 6 * ["\u25cb"]
nag_strings[30:36] = 6 * ["\u27f3"]
nag_strings[36:42] = ["\u2192", "\u2192", "\u2192", "\u2192", "\u2191", "\u2191"]
nag_strings[42:48] = 6 * ["=/\u221e"]
nag_strings[130:136] = 6 * ["\u21c6"]
nag_strings[136:140] = 4 * ["\u2295"]
nag_strings[140:143] = ["\u25B3", "\u25BD", "\u2313"]
nag_strings[145:147] = ["RR", "N"]
nag_strings[238:246] = ["\u25cb", "\u21d4", "\u21d7", "", "\u27eb", "\u27ea", "\u2715", "\u22A5"]

nag_names = 256 * [""]
nag_names[1:24] = ["", "", "!!", "??", "!?", "?!", "box", "", "", "equal", "", "", "unclear", "+=", "=+", "+/-", "-/+", "", "", "", "", "zugswang", "zugswang"]
nag_names[24:30] = 6 * ["space"]
nag_names[30:36] = 6 * ["development"]
nag_names[36:42] = 6 * ["initiative"]
nag_names[42:48] = 6 * ["compensation"]
nag_names[130:136] = 6 * ["counterplay"]
nag_names[136:140] = 4 * ["time_trouble"]
nag_names[140:143] = ["with_idea", "countering", "better_is"]
nag_names[145:147] = ["editorial_comment", "novelty"]
nag_names[238:246] = ["space", "file", "diagonal", "", "kingside", "queenside", "weakness", "endgame"]
