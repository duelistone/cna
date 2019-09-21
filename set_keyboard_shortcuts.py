import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import json, os, sys
import global_variables as G
import callbacks
from shortcut_loader import load_shortcuts_from_config_file

shortcuts_filename = "shortcuts.json"
shortcut_list = load_shortcuts_from_config_file(shortcuts_filename)
try:
    shortcut_list = sorted(shortcut_list, key=lambda x:x["name"])
except:
    # Give up on sorting if an entry doesn't have a name
    pass

def do_nothing(*args):
    return True

def save_callback(*args):
    os.system("cp %s %s.backup" % (shortcuts_filename, shortcuts_filename))
    fil = open(shortcuts_filename, 'w')
    json.dump(shortcut_list, fil)
    pass

def create_entry_keypress_callback(callback_name, index, entry):
    # Creates the callback and also adds appropriate text
    # Search for entry
    shortcut_object = None
    for e in shortcut_list:
        try:
            if e["name"] == callback_name:
                shortcut_object = e
                try:
                    entry.set_text(str(e["shortcuts"][index]))
                except:
                    pass
        except:
            pass
    if shortcut_object == None:
        return do_nothing

    def cb(widget, event):
        state = event.state & G.modifier_mask
        key = event.keyval
        widget.set_text(str([state, key]))
        if "shortcuts" not in shortcut_object:
            shortcut_object["shortcuts"] = []
        if len(shortcut_object["shortcuts"]) > index:
            shortcut_object["shortcuts"][index] = [state, key]
        else:
            shortcut_object["shortcuts"].append([state, key])
        return True

    return cb

window = gtk.Window()
scrolled_window = gtk.ScrolledWindow()
window.add(scrolled_window)
grid = gtk.Grid()
scrolled_window.add(grid)

for i, callback in enumerate(G.documented_functions):
    label = gtk.Label()
    label.set_text(callback.__name__)
    shortcut1_area = gtk.Entry()
    shortcut1_area.connect("key-press-event", create_entry_keypress_callback(callback.__name__, 0, shortcut1_area))
    shortcut1_area.connect("key-release-event", do_nothing)
    shortcut2_area = gtk.Entry()
    shortcut2_area.connect("key-press-event", create_entry_keypress_callback(callback.__name__, 1, shortcut2_area))
    shortcut2_area.connect("key-release-event", do_nothing)
    # TODO: Add delete shortcut buttons
    grid.attach(label, 0, i, 1, 1)
    grid.attach(shortcut1_area, 1, i, 1, 1)
    grid.attach(shortcut2_area, 2, i, 1, 1)

# Button to save
save_button = gtk.Button(label="Save")
save_button.connect("clicked", save_callback)
grid.attach(save_button, 0, i + 1, 3, 1)

window.connect("destroy", gtk.main_quit)
window.show_all()
gtk.main()
