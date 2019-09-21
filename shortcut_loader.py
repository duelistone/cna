import json
import sys
import global_variables as G

def shortcuts_json_list():
    result = []
    for e in G.handlers:
        d = {}
        d["name"] = e
        d["entries"] = []
        d["shortcuts"] = []
        for s in G.command_callbacks[s] == G.handlers[e]:
            d["entries"].append(s)
        for mask in G.key_binding_maps:
            for k in G.key_binding_maps[mask]:
                if G.key_binding_maps[mask][k] == G.handlers[e]:
                    d["shortcuts"].append([mask][k])
        result.append(d)
    return result

def json_list_from_file(filename):
    # Create file object first if not given one
    if type(filename) == str:
        with open(filename, 'r') as fil:
            return json.load(fil)

    # Caller is in charge of closing file if they created it
    return json.load(filename)

def apply_shortcuts_list(shortcuts_list):
    for o in shortcuts_list:
        try:
            callback = G.handlers[o["name"]]
        except KeyError:
            print("apply_shortcuts_list: The following entry was ignored due to a missing name or no callback existing with that name: %s" % str(o), file=sys.stderr)
            continue
        try:
            for s in o["entries"]:
                G.command_callbacks[s] = callback
        except KeyError:
            pass
        try:
            for shortcut in o["shortcuts"]:
                try:
                    mask = shortcut[0]
                    key = shortcut[1]
                except IndexError:
                    print("apply_shortcuts_list: Invalid format given for shortcut %s for callback %s" % (str(shortcut), o["name"]), file=sys.stderr)
                    continue
                if mask not in G.key_binding_maps:
                    G.key_binding_maps[mask] = {}
                G.key_binding_maps[mask][key] = callback
        except KeyError:
            pass
    return shortcuts_list

def load_shortcuts_from_config_file(filename):
    return apply_shortcuts_list(json_list_from_file(filename))

