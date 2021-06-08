# import bdsim.blocks as b

# print(dir(b))

# bd = BlockDiagram()

class BlockDiagram:
    def __init__(self):
        print('new bd')
        self.parent = self

class Block(BlockDiagram):
    pass

class Function(Block):
    pass

class MULT(Function):
    """
    MULT block(a,b,c)
    """

    def __init__(self, a, b, c):
        pass

b = BlockDiagram()

b.
