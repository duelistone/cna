# help_helpers.py

# Helper functions related to program's help functionality.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango
from gi.repository import GLib
import global_variables as G

def help_report(callback):
    # Extract info on how to invoke callback
    commands = []
    keys = []
    for s in G.command_callbacks:
        if G.command_callbacks[s] == callback:
            commands.append(s)
    for mask in G.key_binding_maps:
        for k in G.key_binding_maps[mask]:
            if G.key_binding_maps[mask][k] == callback:
                bits = mask
                mask_parts = []
                while bits:
                    bit = bits & -bits
                    mask_parts.append(G.modifier_names[bit] + '+')
                    bits &= ~bit
                mask_part = ''.join(mask_parts)
                keys.append(mask_part + gdk.keyval_name(k))

    # Build report
    entry_piece = "Entry commands: %s" % ", ".join(commands)
    shortcuts_piece = "Keyboard shortcuts: %s" % ", ".join(keys)
    docstring = callback.__doc__ 
    if not docstring: docstring = "(No description available.)"
    return "%s\n%s\n%s\n%s" % (callback.__name__, entry_piece, shortcuts_piece, docstring)
    
def full_help_report():
    reports = []
    callbacks = sorted(G.documented_functions, key=lambda x : x.__name__)
    for cb in callbacks:
        reports.append(help_report(cb))
    return "\n\n\n".join(reports)

