'''Module for decorators used. These are used frequently in callbacks.py.'''

import global_variables as G

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

def key_callback(*keys):
    def result(cb):
        G.documented_functions.add(cb)
        for k in keys:
            G.key_binding_map[k] = cb
        return cb
    return result

def control_key_callback(*keys):
    def result(cb):
        G.documented_functions.add(cb)
        for k in keys:
            G.control_key_binding_map[k] = cb
        return cb
    return result

