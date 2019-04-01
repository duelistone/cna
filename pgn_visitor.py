import global_variables as G
import chess

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
                strings.append(G.nag_strings[e])
                offset += len(strings[-1])
                strings.append(" ")
                offset += 1
        # Comment
        commentLength = len(game.comment)
        if commentLength > 0:
            G.commentRanges.append((offset, offset + commentLength))
            strings.append(game.comment)
            strings.append(' ')
            offset += commentLength + 1
    else:
        # Normal node
        if firstMoveOfVariation and firstMoveAfterVariation:
            piece = ')\n' + indentationLevel * indentation_width * ' ' + '( '
            strings.append(piece)
            offset += len(piece)
        elif firstMoveOfVariation:
            indentationLevel += 1
            piece = '\n' + indentationLevel * indentation_width * ' ' + '( '
            strings.append(piece)
            offset += len(piece)
        elif firstMoveAfterVariation:
            piece = ')\n' + indentationLevel * indentation_width * ' '
            strings.append(piece)
            offset += len(piece)
        # Comment
        if firstMoveOfVariation:
            commentLength = len(game.starting_comment)
            if commentLength > 0:
                G.commentRanges.append((offset, offset + commentLength))
                strings.append(game.starting_comment)
                strings.append(' ')
                offset += commentLength + 1
        # Move number
        if game.parent.board().turn == chess.WHITE:
            piece = "%d. " % game.parent.board().fullmove_number
            strings.append(piece)
            offset += len(piece)
        elif firstMoveOfVariation or firstMoveAfterVariation or game.parent == game.root():
            piece = "%d... " % game.parent.board().fullmove_number
            strings.append(piece)
            offset += len(piece)
        strings.append(game.parent.board().san(game.move))
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
        strings.append(" ")
        offset += 1
        # NAG
        if len(game.nags) > 0:
            for e in game.nags:
                if e > 255: continue
                strings.append(G.nag_strings[e])
                offset += len(strings[-1])
                strings.append(" ")
                offset += 1
        # Comment
        commentLength = len(game.comment)
        if commentLength > 0:
            G.commentRanges.append((offset, offset + commentLength))
            strings.append(game.comment)
            strings.append(' ')
            offset += commentLength + 1

    # PGN order recursion
    children = game.variations
    num_children = len(game.variations)
    if num_children > 1:
        newString, offset = game_gui_string_list(game.variation(1), offset=offset, firstMoveOfVariation=True, indentationLevel=indentationLevel)
        strings.extend(newString)
        for i in range(2, num_children):
            newString, offset = game_gui_string_list(game.variation(i), offset=offset, firstMoveOfVariation=True, firstMoveAfterVariation=True, indentationLevel=indentationLevel+1)
            strings.extend(newString)
    if num_children > 0:
        newString, offset = game_gui_string_list(game.variation(0), offset=offset, firstMoveAfterVariation=True if num_children > 1 else False, indentationLevel=indentationLevel)
        strings.extend(newString)

    return strings, offset

def game_gui_string(game):
    return "".join(game_gui_string_list(game)[0])
