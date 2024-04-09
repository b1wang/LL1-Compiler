# Author: Brandon Wang
#
# Abstract data structure for storing parser results

# class Result {
#   int kind, <- 0 = const, 1 = var, 2 = reg
#   int value,   (if const)
#   int address, (if var)
#   int register (if reg)
# }
class Result:

    CONST = 0
    VAR = 1
    FUNC = 2

    def __init__(self):
        self.kind = -1       # Default value -1 to signal that no kind was assigned yet
        self.value = 0       # value if it is a constant
        self.address = 0     # address if it is a variable
        self.function = 0    # ID of function node
        self.variables = []     