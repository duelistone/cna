# lichess_helpers.py

# Helper functions related to accessing lichess API

import requests, io
import global_variables as G
import chess, chess.pgn

def lichess_opening_response(position):
    '''Returns (possibly cached) lichess opening explorer response.

    See https://github.com/niklasf/lila-openingexplorer for formatting.'''
    board_fen = position.fen() if type(position) != str else position
    if board_fen in G.cached_lichess_responses:
        return G.cached_lichess_responses[board_fen]
    else:
        http_board_fen = board_fen.replace(" ", "%20")
        url = "https://explorer.lichess.ovh/master?fen=" + http_board_fen
        try:
            request = requests.get(url, timeout=(0.5, 4))
            request.raise_for_status()
            json_response = request.json()
        except:
            return
        G.cached_lichess_responses[board_fen] = json_response
        return json_response

def lichess_game_response(game_id):
    '''Requests the lichess game with given game id from lichess.

    The response is a PGN string.'''
    # Note that no cache is used here intentionally, in case it affects
    # future live game functionality or something similar.
    url = "https://explorer.lichess.ovh/master/pgn/" + game_id
    try:
        request = requests.get(url, timeout=(0.5, 8))
        request.raise_for_status()
        return request.text
    except:
        return

def lichess_opening_moves(position):
    '''Returns opening moves appearing in lichess master database.
    Input could be a board object or fen string.
    Returns None if an error is encountered.'''
    json_response = lichess_opening_response(position)
    result = []
    for i in range(len(json_response["moves"])):
        result.append(json_response["moves"][i]["san"])
        total = json_response["moves"][i]["white"] + json_response["moves"][i]["draws"] + json_response["moves"][i]["black"]
        score = (json_response["moves"][i]["white"] + 0.5 * json_response["moves"][i]["draws"]) / total
        result.append("(%d, %d%%)" % (total, int(100 * score)))
    return result

def lichess_top_games(position):
    '''Returns top games appearing in the lichess master database
    from an opening position.'''
    json_response = lichess_opening_response(position)
    info_list = []
    id_list = []
    for i in range(len(json_response["topGames"])):
        result = "1/2-1/2" 
        if json_response["topGames"][i]["winner"] == "white":
            result = "1-0"
        elif json_response["topGames"][i]["winner"] == "black":
            result = "0-1"
        info = "%s (%d) v %s (%d) %s" % (
            json_response["topGames"][i]["white"]["name"], 
            json_response["topGames"][i]["white"]["rating"], 
            json_response["topGames"][i]["black"]["name"], 
            json_response["topGames"][i]["black"]["rating"], 
            result)
        info_list.append(info)
        id_list.append(json_response["topGames"][i]["id"])
    return info_list, id_list

def lichess_game(game_id):
    '''Returns lichess game given game id, or None if an error occurs.'''
    pgn_string = lichess_game_response(game_id)
    pgn_file = io.StringIO(pgn_string)
    return chess.pgn.read_game(pgn_file)
