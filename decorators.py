'''Module for decorators used. These are used frequently in callbacks.py.'''

import global_variables as G
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk as gdk

# Decorators

def gui_callback(cb):
    G.handlers[cb.__name__] = cb
    return cb

def documented(cb):
    G.documented_functions.add(cb)
    return cb

# Decorators returning decorators!

def entry_callback(*strings):
    def result(cb):
        G.documented_functions.add(cb)
        for s in strings:
            G.command_callbacks[s] = cb
        return cb
    return result

def press_callback(mask, *keys):
    def result(cb):
        G.documented_functions.add(cb)
        if mask not in G.key_binding_maps:
            G.key_binding_maps[mask] = {}
        for k in keys:
            G.key_binding_maps[mask][k] = cb
        return cb
    return result

def key_callback(*keys):
    return press_callback(0, *keys)

def control_key_callback(*keys):
    return press_callback(gdk.ModifierType.CONTROL_MASK, *keys)

