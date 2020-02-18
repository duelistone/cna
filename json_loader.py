# json_loader.py

'''Loads json config files.'''

import json, sys

def json_from_file(filename):
    # Create file object first if not given one
    if type(filename) == str:
        with open(filename, 'r') as fil:
            return json.load(fil)

    # Caller is in charge of closing file if they created it
    return json.load(filename)

class CallbackConfigManager(object):
    def __init__(self, callbacks):
        self.callbacks = callbacks # The dict of callback names:callbacks for the program
        self.json_list = []
        self.callback_dict = {e : {"name": e} for e in self.callbacks}
        self.ENTRY_SHORTCUTS_NAME = "entries"
        self.KEYBOARD_SHORTCUTS_NAME = "shortcuts"
        self.MENU_NAME = "menu"

    def load_json_from_file(self, filename, also_parse=True):
        try:
            self.json_list = json_from_file(filename)
            assert(type(self.json_list) == list)
        except:
            self.json_list = []
            raise ValueError("Could not parse JSON file correctly")
        if also_parse:
            self.parse()

    def parse(self):
        '''Loads info from json_list into self.callback_dict.
        Does not delete previous data in self.callback_dict, 
        but can override a previous value of a key.'''
        for d in self.json_list:
            if "name" not in d or d["name"] not in self.callbacks:
                print("CallbackConfigManager: The following entry was ignored due to a missing name or no callback existing with that name: %s" % str(d), file=sys.stderr)
                continue
            callback_name = d["name"]
            for k in d:
                self.callback_dict[callback_name][k] = d[k]

    def __contains__(self, callback_name):
        return callback_name in self.callback_dict

    def __getitem__(self, callback_name):
        '''Will throw KeyError if callback_name is invalid.'''
        return self.callback_dict[callback_name]

    def entry_shortcuts(self, callback_name):
        try:
            return self[callback_name][self.ENTRY_SHORTCUTS_NAME]
        except:
            return []

    def keyboard_shortcut_lists(self, callback_name):
        try:
            return self[callback_name][self.KEYBOARD_SHORTCUTS_NAME]
        except:
            return []

    def menu_list(self, callback_name):
        try:
            return self[callback_name][self.MENU_NAME]
        except:
            return []
        
    def advanced_shortcuts_lists(self, callback_name):
        try:
            return self[callback_name]["advanced_" + self.KEYBOARD_SHORTCUTS_NAME]
        except:
            return []

    def advanced_menu_lists(self, callback_name):
        try:
            return self[callback_name]["advanced_" + self.MENU_NAME]
        except:
            return []


    def load_entry_shortcuts(self, entry_cb_dict):
        '''entry_cb_dict is the dictionary of entry name:callback pairs.'''
        def load_entry_shortcut(cb_name):
            cb = self.callbacks[cb_name]
            for shortcut in self.entry_shortcuts(cb_name):
                entry_cb_dict[shortcut] = cb

        for cb_name in self.callbacks:
            load_entry_shortcut(cb_name)

    def load_keyboard_shortcuts(self, key_binding_maps):
        '''key_binding_maps is of the form masks -> keys -> callbacks.'''
        def load(mask, key, cb):
            if mask not in key_binding_maps:
                key_binding_maps[mask] = {}
            key_binding_maps[mask][key] = cb

        def load_keyboard_shortcut(cb_name):
            cb = self.callbacks[cb_name]
            for shortcut in self.keyboard_shortcut_lists(cb_name):
                try:
                    mask = int(shortcut[0])
                    key = int(shortcut[1])
                except:
                    print("load_keyboard_shortcuts: Invalid format given for shortcut %s for callback %s" % (str(shortcut), cb_name), file=sys.stderr)
                    continue
                load(mask, key, cb)

        def load_advanced_keyboard_shortcut(cb_name):
            cb = self.callbacks[cb_name]
            advanced_shortcuts_list = self.advanced_shortcuts_lists(cb_name)
            for i in range(0, len(advanced_shortcuts_list), 2):
                shortcut = advanced_shortcuts_list[i]
                try:
                    args = advanced_shortcuts_list[i + 1]
                except IndexError:
                    print("load_advanced_keyboard_shortcut: Missing args for shortcut %s for callback %s" % (str(shortcut), cb_name), file=sys.stderr)
                    break
                try:
                    mask = int(shortcut[0])
                    key = int(shortcut[1])
                except:
                    print("load_advanced_keyboard_shortcut: Invalid format given for advanced shortcut %s for callback %s" % (str(shortcut), cb_name), file=sys.stderr)
                    continue
                curried_cb = lambda : cb(*args)
                load(mask, key, curried_cb)

        for cb_name in self.callbacks:
            load_keyboard_shortcut(cb_name)
            load_advanced_keyboard_shortcut(cb_name)
                    
    def load_menu_items(self, menu_root):
        # Important to avoid loop-related closure scope issues
        def load(menu_list, cb, arg_list):
            if menu_list:
                menu_root.add_menu_from_list(menu_list, cb=lambda : cb(*arg_list))

        for cb_name in self.callbacks:
            cb = self.callbacks[cb_name]
            # Easy part
            menu_list = self.menu_list(cb_name)
            if menu_list:
                menu_root.add_menu_from_list(menu_list, cb=cb)
            # Advanced part
            advanced_menu_lists = self.advanced_menu_lists(cb_name)
            for i in range(0, len(advanced_menu_lists), 2):
                menu_list = advanced_menu_lists[i]
                try:
                    args = advanced_menu_lists[i + 1]
                except IndexError:
                    print("load_advanced_menu_lists: Missing args for shortcut %s for callback %s" % (str(menu_list), cb_name), file=sys.stderr)
                    break
                load(menu_list, cb, args)

# TODO: EngineConfigManager?

