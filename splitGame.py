import chess, chess.pgn, sys
from dfs import *

# Load file
fil = open(sys.argv[1], 'r')
root = chess.pgn.read_game(fil)
fil.close()

# Loop through games
visitedNodes = set()
currentNode = root
counter = 1
fil = None
if '-o' in sys.argv:
    fil = open(sys.argv[1] + '.split', 'w')
    
for node in filter(lambda x : x.is_end(), dfs(root)):
    game = chess.pgn.Game.from_board(node.board())
    if '-o' not in sys.argv:
        # Make different pgn file for each line
        fil = open(sys.argv[1] + '-' + str(counter), 'w')
        counter += 1
    if '-h' in sys.argv or '-o' not in sys.argv:
        # Include repeated header
        print(game, file=fil)
    else:
        # Skip headers
        exporter = chess.pgn.FileExporter(fil, headers=False)
        game.accept(exporter)
    print(file=fil) # Print new line
