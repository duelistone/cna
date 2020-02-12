import json
import sys
import global_variables as G
from json_loader import json_from_file

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
    return apply_shortcuts_list(json_from_file(filename))

