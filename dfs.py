# dfs.py

'''Depth first search module, made to work with game trees created by 
python-chess module. Also includes a random search function.'''

import random

def dfs(node, color=None):
    '''Generates games, one for each line encountered in a
    depth first search from beginning to end.'''
    # Check if in leaf node
    if node.is_end() and (color == None or passesMainTest(node, color)):
        yield node
    # Traverse tree depth first
    children = node.variations
    if color != None:
        children = filter(lambda x : passesMainTest(x, color), children)
    for var in children:
        yield from dfs(var, color)

def passesMainTest(node, color):
    '''Checks if the last move was made by color, or 
    if the node is a main variation node.'''
    return True # node.is_main_variation() or node.board().turn == color

def randomSearchFunction(node, color=None):
    '''Selects a random leaf node starting at a given node. If color != None, it returns None if 
    the selected leaf isn't a PV from color's point of view.'''
    # Check if in leaf node
    if node.is_end() and (color == None or passesMainTest(node, color)):
        return node
    # Recurse
    children = node.variations
    return randomSearchFunction(random.choice(node.variations))

def randomSearch(node, color=None):
    '''Generator corresponding to randomSearchFunction.'''
    while 1:
        result = randomSearchFunction(node, color)
        if result != None: yield result

def countNodes(node, color=None):
    '''Counts number of subnodes, including itself.'''
    if color == None or node.board().turn == color:
        result = 1
    else:
        result = 0
    for v in node.variations:
        result += countNodes(v, color)
    return result
