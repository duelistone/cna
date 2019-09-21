'''Module for decorators used. These are used frequently in callbacks.py.'''

import global_variables as G

# Decorators

def gui_callback(cb):
    G.handlers[cb.__name__] = cb
    return cb

def documented(cb):
    G.documented_functions.add(cb)
    return cb
