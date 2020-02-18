# menu_items.py

'''Functions to generate menu item with a given callback.'''

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk

class MenuNode(object):
    def __init__(self, parent=None, has_children=True, label=""):
        self.parent = parent
        self.children = []
        self.label = label
        if self.parent == None:
            self.gtk_object = gtk.MenuBar()
        else:
            if has_children:
                self.gtk_object = gtk.MenuItem(label=label)
                submenu = gtk.Menu()
                self.gtk_object.set_submenu(submenu)
            else:
                self.gtk_object = gtk.MenuItem(label=label)

            # Identify gtk object storing list of items
            if self.parent.parent == None:
                gtk_submenu = self.parent.gtk_object
            else:
                gtk_submenu = self.parent.gtk_object.get_submenu()

            # append to parent with alphabetical insertion sort
            index = 0
            children_list = self.parent.children
            while True:
                if index == len(children_list) or self.is_less_than(children_list[index]):
                    self.parent.children.insert(index, self)
                    gtk_submenu.insert(self.gtk_object, index)
                    break
                index += 1

    def is_less_than(self, other):
        return self.label < other.label

    def get_child_with_label(self, s):
        for child in self.children:
           if child.label == s:
               return child
        
    def add_menu_from_list(self, menu_list, cb=None):
        if len(menu_list) == 0:
            if cb != None:
                self.set_callback(cb)
            return self
        head = menu_list[0]
        menu_list = menu_list[1:]
        child = self.get_child_with_label(head)
        if child == None:
            child = MenuNode(self, len(menu_list) > 0, head)
        return child.add_menu_from_list(menu_list, cb)

    def set_callback(self, cb):
        if self.parent == None:
            print("Cannot add callback to root menu node.")
            return
        def wrapper(*args):
            cb()
            return False
        self.gtk_object.connect("activate", wrapper)

    def insert(self, parent):
        parent.pack_start(self.gtk_object, False, False, 0)
        parent.reorder_child(self.gtk_object, 0)
        
