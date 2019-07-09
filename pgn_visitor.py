import global_variables as G
import chess
import time

times = []
def game_gui_string_list(game, offset=0, firstMoveOfVariation=False, firstMoveAfterVariation=False, indentationLevel=0):
    strings = []
    indentation_width = 4 # Set constant for now

    # Form string
    if game == game.root():
        # Root node
        G.bufferToNodes = {}
        G.nodesToRanges = {}
        G.specialRanges = []
        G.bookRanges = []
        G.learnRanges = []
        G.commentRanges = []
        # Header
        headerString = "%s vs %s, %s, %s, %s, %s\n\n" % (game.headers["White"], game.headers["Black"], game.headers["Event"], game.headers["Site"], game.headers["Date"], game.headers["Result"])
        strings.append(headerString)
        offset += len(headerString)
        # Move string
        startString = "Start"
        strings.append(startString)
        G.bufferToNodes[offset] = game
        G.nodesToRanges[game] = (offset, offset + len(strings[-1]))
        if game.special: 
            G.specialRanges.append((offset, offset + len(strings[-1])))
        if int(game.book) == 1:
            G.bookRanges.append((offset, offset + len(strings[-1])))
            if game.book % 1 == 0.5:
                G.learnRanges.append((offset, offset + len(strings[-1])))
        if game == G.g:
            G.currentMoveRange = (offset, offset + len(strings[-1]))
        offset += len(strings[-1])
        # Extra
        strings.append(' ')
        offset += 1
        # NAG
        if len(game.nags) > 0:
            for e in game.nags:
                if e > 255: continue
                strings.append('%s ' % G.nag_strings[e])
                offset += len(strings[-1])
        # Comment
        commentLength = len(game.comment)
        if commentLength > 0:
            G.commentRanges.append((offset, offset + commentLength))
            strings.append("%s " & game.comment)
            offset += commentLength + 1
    else:
        # Normal node
        if firstMoveOfVariation and firstMoveAfterVariation:
            piece = ')\n%s( ' % (indentationLevel * indentation_width * ' ')
            strings.append(piece)
            offset += len(piece)
        elif firstMoveOfVariation:
            indentationLevel += 1
            piece = '\n%s( ' % (indentationLevel * indentation_width * ' ')
            strings.append(piece)
            offset += len(piece)
            # Starting comment
            commentLength = len(game.starting_comment)
            if commentLength > 0:
                G.commentRanges.append((offset, offset + commentLength))
                strings.append("%s " % game.starting_comment)
                offset += commentLength + 1
        elif firstMoveAfterVariation:
            piece = ')\n%s' % (indentationLevel * indentation_width * ' ')
            strings.append(piece)
            offset += len(piece)
        # Move number
        if game.parent.readonly_board.turn == chess.WHITE:
            piece = "%d. " % game.parent.readonly_board.fullmove_number
            strings.append(piece)
            offset += len(piece)
        elif firstMoveOfVariation or firstMoveAfterVariation or game.parent == game.root():
            piece = "%d... " % game.parent.readonly_board.fullmove_number
            strings.append(piece)
            offset += len(piece)
        strings.append(game.parent.readonly_board.san(game.move))
        G.bufferToNodes[offset] = game
        G.nodesToRanges[game] = (offset, offset + len(strings[-1]))
        if game.special: 
            G.specialRanges.append((offset, offset + len(strings[-1])))
        if int(game.book) == 1:
            G.bookRanges.append((offset, offset + len(strings[-1])))
            if game.book % 1 == 0.5:
                G.learnRanges.append((offset, offset + len(strings[-1])))
        if game == G.g:
            G.currentMoveRange = (offset, offset + len(strings[-1]))
        offset += len(strings[-1]) + 1
        strings.append(" ")
        # NAG
        if len(game.nags) > 0:
            for e in game.nags:
                if e > 255: continue
                strings.append("%s " % G.nag_strings[e])
                offset += len(strings[-1])
        # Comment
        commentLength = len(game.comment)
        if commentLength > 0:
            G.commentRanges.append((offset, offset + commentLength))
            strings.append("%s " % game.comment)
            offset += commentLength + 1
    return "".join(strings), offset

def game_gui_string(game):
    # The old recursive algorithm has been coverted to this iterative one, as
    # the recursive algorithm was performing linearly worse the more nested
    # recursions there were

    # Testing
    times = []

    stack = []
    strings = []
    offset = 0
    # The offset argument is omitted, as it is kept track of separately
    stack.append((game, False, False, 0))

    while len(stack) > 0:
        args = stack.pop()
        starting_time = time.time()
        new_string, offset = game_gui_string_list(args[0], offset, args[1], args[2], args[3])
        times.append(time.time() - starting_time)
        strings.append(new_string)
        game = args[0]
        indentationLevel = args[3]

        num_children = len(game.variations)
        # Remember that the corresponding calls are done backwards, due to how a stack works
        if num_children > 0:
            stack.append((game.variation(0), False, True if num_children > 1 else False, indentationLevel))
        if num_children > 1:
            for i in range(num_children - 1, 1, -1):
                stack.append((game.variation(i), True, True, indentationLevel + 1))
            stack.append((game.variation(1), True, False, indentationLevel))

    # Testing
    if len(times) > 0:
        print("Avg %f" % (sum(times) / len(times)))
        print("Min %f" % min(times))
        print("Max %f" % max(times))

    return "".join(strings)
