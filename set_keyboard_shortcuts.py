import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
import json, os, sys
import global_variables as G
import callbacks
from shortcut_loader import load_shortcuts_from_config_file

# Load config
shortcuts_filename = "shortcuts.json"
if len(sys.argv) > 1:
    if os.path.isfile(sys.argv[1]):
        shortcuts_filename = sys.argv[1]
    else:
        print("Invalid file given, using default.", file=sys.stderr)
shortcut_list = load_shortcuts_from_config_file(shortcuts_filename)

# Helpers

def get_shortcut_object(callback_name, apply_function=None):
    shortcut_object = None
    for e in shortcut_list:
        try:
            if e["name"] == callback_name:
                shortcut_object = e
                if apply_function != None:
                    apply_function(e)
                break
        except:
            pass
    return shortcut_object

def readable_shortcut(state_value_pair):
    state = state_value_pair[0]
    keyval = state_value_pair[1]

    result_parts = []
    if state & gdk.ModifierType.CONTROL_MASK:
        result_parts.append("Ctrl")
    result_parts.append(gdk.keyval_name(keyval))

    return ' '.join(result_parts)

# Callbacks (and callback constructors)

def do_nothing(*args):
    return True

def save_callback(*args):
    os.system("cp %s %s.backup" % (shortcuts_filename, shortcuts_filename))
    fil = open(shortcuts_filename, 'w')
    json.dump(shortcut_list, fil, indent=2)

def create_delete_callback(callback_name, entry1, entry2):
    def delete_function(shortcut_object):
        shortcut_object["shortcuts"] = []

    def cb(widget):
        get_shortcut_object(callback_name, delete_function)
        entry1.set_text("")
        entry2.set_text("")

    return cb

def create_entry_keypress_callback(callback_name, index, entry):
    # Creates the callback and also adds appropriate text
    # Search for entry
    def set_entry(shortcut_object):
        try:
            state_key_pair = shortcut_object["shortcuts"][index]
            entry.set_text(str(state_key_pair) + " " + readable_shortcut(state_key_pair))
        except (IndexError, KeyError):
            pass
    shortcut_object = get_shortcut_object(callback_name, set_entry)

    # Special case where shortcut object not present in JSON
    if shortcut_object == None:
        # Make new entry
        shortcut_object = {}
        shortcut_object["name"] = callback_name
        shortcut_object["entries"] = []
        shortcut_object["shortcuts"] = []
        shortcut_list.append(shortcut_object)
        return do_nothing

    # Normal callback
    def cb(widget, event):
        state = event.state & G.modifier_mask
        key = event.keyval
        if "shortcuts" not in shortcut_object:
            shortcut_object["shortcuts"] = []

        # How to continue depends on whether index already exists
        # in the shortcuts list
        num_shortcuts = len(shortcut_object["shortcuts"])
        if num_shortcuts > index:
            shortcut_object["shortcuts"][index] = [state, key]
        elif num_shortcuts == index:
            shortcut_object["shortcuts"].append([state, key])
        else:
            # Appending in this case would lead to a mismatched
            # index, so we do nothing in this case
            return True
        widget.set_text(str([state, key]) + " " + readable_shortcut([state, key]))
        return True

    return cb

# Constructing each page

def construct_shortcut_page(parent_notebook):
    scrolled_window = gtk.ScrolledWindow()
    label = gtk.Label()
    label.set_text("Keyboard Shortcuts")
    notebook.append_page(scrolled_window, tab_label=label)
    grid = gtk.Grid()
    scrolled_window.add(grid)

    for i, callback in enumerate(sorted(G.documented_functions, key=lambda x:x.__name__)):
        # Label
        label = gtk.Label()
        label.set_text(callback.__name__)

        # Entries to capture keyboard presses
        shortcut1_area = gtk.Entry()
        shortcut1_area.connect("key-press-event", create_entry_keypress_callback(callback.__name__, 0, shortcut1_area))
        shortcut1_area.connect("key-release-event", do_nothing)
        shortcut2_area = gtk.Entry()
        shortcut2_area.connect("key-press-event", create_entry_keypress_callback(callback.__name__, 1, shortcut2_area))
        shortcut2_area.connect("key-release-event", do_nothing)

        # Delete area
        delete_area = gtk.Button()
        delete_img = gtk.Image()
        delete_img.set_from_icon_name("edit-delete", gtk.IconSize.BUTTON)
        delete_area.set_image(delete_img)
        delete_area.connect("clicked", create_delete_callback(callback.__name__, shortcut1_area, shortcut2_area))

        # TODO: Show when a change has been made to a row, perhaps by underlining
        # callback name or adding an asterisk at the end of it

        # Place these widgets in grid
        grid.attach(label, 0, i, 1, 1)
        grid.attach(shortcut1_area, 1, i, 1, 1)
        grid.attach(shortcut2_area, 2, i, 1, 1)
        grid.attach(delete_area, 3, i, 1, 1)

    # Button to save
    save_button = gtk.Button(label="Save")
    save_button.connect("clicked", save_callback)
    grid.attach(save_button, 0, i + 1, 3, 1)

def construct_menu_page(parent_notebook):
    scrolled_window = gtk.ScrolledWindow()
    label = gtk.Label()
    label.set_text("Menus")
    notebook.append_page(scrolled_window, tab_label=label)
    grid = gtk.Grid()
    scrolled_window.add(grid)
    
    # TODO


window = gtk.Window()
notebook = gtk.Notebook()
construct_shortcut_page(notebook)
construct_menu_page(notebook)
window.add(notebook)
# Final preparations and start mainloop
window.connect("destroy", gtk.main_quit)
window.show_all()
window.grab_focus()
gtk.main()
