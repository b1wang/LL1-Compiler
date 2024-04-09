# Author: Brandon Wang
#
# Instruction class is a dynamic LinkedList that holds compiler instructions

from op_codes import OP


class InstructionNode:
    def __init__(self):
        self.op = None
        self.a = 0
        self.b = 0
        self.instr_id = 0
        self.prev_instr = None
        self.next_instr = None
        self.prev_dom_instr = None

    def printInstruction(self):
        print(
            str(self.instr_id)
            + " | "
            + str(self.op)
            + " "
            + str(self.a)
            + " "
            + str(self.b)
        )

    # Convert to string for DOT
    def toString(self) -> str:
        s = str(self.instr_id) + ": "
        if self.op == None:  # Empty block
            return s
        elif self.op == OP.CONST:  # Const block
            s = s + str(self.op) + " #" + str(self.a)
            return s
        else:
            s = s + str(self.op)
            if isinstance(self.a, int):
                if self.a > 0:
                    s = s + " (" + str(self.a) + ")"
                if self.b > 0:
                    s = s + " (" + str(self.b) + ")"
            else:
                s = s + " " + str(self.a)
                if isinstance(self.b, int) and self.b > 0:
                    s = s + " (" + str(self.b) + ")"
            return s


class InstructionList:
    DEFAULT = 0

    def __init__(self):
        self.head = None
        self.tail = None
        self.next_instr_num = 1

    def AddNode(self, op, a, b) -> int:
        node = InstructionNode()
        node.op = op
        node.a = a
        node.b = b
        node.instr_id = self.next_instr_num
        node.prev_instr = self.tail
        if self.head is None:
            self.head = node
        else:
            self.tail.next_instr = node
        self.tail = node
        self.next_instr_num += 1
        return node.instr_id

    # Add instruction with CSE integrated
    #   Returns: New instr id OR Prev instr ID (CSE)
    def AddInstruction(self, op, a, b) -> int:
        id = self.AddNode(op, a, b)
        return id

    # Add an empty instruction (used on new blocks, will replace once done)
    def AddEmptyInstruction(self) -> int:
        return self.AddInstruction(None, 0, 0)

    # Add an array kill instruction (special: {kill a})
    def AddKillInstruction(self, array) -> int:
        return self.AddInstruction("kill", array, 0)

    # No check for CSE
    #   Returns: New instr ID for read node
    def AddConst(self, const) -> int:
        return self.AddInstruction(OP.CONST, const, 0)

    # No check for CSE
    #   Returns: New instr ID for read node
    def AddReadInstruction(self) -> int:
        return self.AddNode(OP.READ, 0, 0)

    def AddEndInstruction(self) -> int:
        return self.AddNode(OP.END, 0, 0)

    #   No check for CSE
    #   Returns: New instr ID for read node
    def AddWriteInstruction(self, var) -> int:
        return self.AddNode(OP.WRITE, var, 0)

    #   No check for CSE
    #   Returns: New instr ID for read node
    def AddWriteNLInstruction(self) -> int:
        return self.AddNode(OP.WRITENL, 0, 0)

    # Add a phi instruction (No CSE)
    #   Returns: New instr ID for phi node
    def AddPhiInstruction(self, a, b) -> int:
        return self.AddNode(OP.PHI, a, b)

    # Find an instruction by its ID and return the instruction node
    #   Not found: Return None
    def FindInstruction(self, id) -> InstructionNode:
        curr_node = self.tail
        while curr_node is not None:
            if curr_node.instr_id == id:
                return curr_node
            curr_node = curr_node.prev_instr
        print("InstructionList: Did not find ID " + str(id))
        return None

    def PrintInstruction(self, id):
        instr = self.FindInstruction(id)
        if instr is None:
            print("Cannot find instruction")
        else:
            print(
                str(id)
                + " | "
                + str(instr.op)
                + " "
                + str(instr.a)
                + " "
                + str(instr.b)
            )

    # Print to string (for testing)
    def print(self) -> None:
        print("Instruction List: ")
        curr_node = self.head
        if curr_node is None:
            print("No nodes to print.")
        while curr_node is not None:
            print(
                "Node "
                + str(curr_node.instr_id)
                + " | "
                + str(curr_node.op)
                + " "
                + str(curr_node.a)
                + " "
                + str(curr_node.b)
            )
            curr_node = curr_node.next_instr
