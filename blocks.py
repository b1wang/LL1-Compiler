# Author: Brandon Wang
#
# Blocks class is a dynamic Tree structure that holds instruction ids

from instructions import InstructionList, InstructionNode
from op_codes import OP
import copy

# BlockTree is a tree with max of 2 children each BlockNode
# Each BlockNode holds instruction IDs and its own symtable. PTRS to PARENT, CHILDREN, and PREV DOM BLCK


class BlockNode:
    BASIC = 0
    BRANCH = 1
    FALL = 2
    JOIN = 3
    WHILE_JOIN = 4
    FOLLOW = 5

    # Create a new block
    #   - Empty blocks should still have an "Empty" instruction, unless there is an instruction that overwrites
    def __init__(self, idx):
        self.idx = idx  # Index of block
        self.instructions = []  # List to hold instruction ids
        self.dom_instructions = (
            {}
        )  # LinkedList of prev dom instructions for each operator
        self.parents = [None] * 2  # Parent(s) of node
        self.children = [None] * 2  # List to hold children (if branching, max 2)
        self.symtable = (
            {}
        )  # Symbol table "dict" for the block (used to check dominance)
        self.vartable = {}  # Variant table to keep track of "invariants" in while loops (1 = variant, 0 = invariant)
        self.usedvartable = {} # Table to keep track of which variables were "used" in each variable's assignment 
        self.dom_block = None  # The dominating block (used for CSE)
        self.waiting_on = (
            0,
            0,
        )  # Tells a join block that a previous node is waiting on a link (instr_id, 0:a/1:b)
        self.while_phi_idx = 0  # Index of phi in block (for while loops)
        self.type = BlockNode.BASIC

    def AddInstructionToBlock(self, instr_id):
        self.instructions.append(instr_id)

    def AddInstructionToIndex(self, instr_id, index):
        self.instructions.insert(index, instr_id)

    def AddInstructionToFront(self, instr_id):
        self.instructions.insert(0, instr_id)

    def SetChild(self, block):
        self.children[0] = block
        self.children[1] = None

    def SetChildren(self, block1, block2):
        self.children[0] = block1
        self.children[1] = block2

    def SetParent(self, block):
        self.parents[0] = block
        self.parents[1] = None

    def SetParents(self, block1, block2):
        self.parents[0] = block1
        self.parents[1] = block2


class BlockTree:
    def __init__(self):
        self.index = 0
        self.list_of_vars = []
        self.instrList = (
            InstructionList()
        )  # Init an instruction list to hold instructions in sequential order
        self.root = None  #   Initial block 0 to hold constants
        self.current_block = None  # Add block 1 to begin program
        self.current_join_blocks = (
            []
        )  # List (stack) of join blocks (in order of innermost-outermost branches)
        
    def Create(self):
        self.root = self.AddRoot()  #   Initial block 0 to hold constants
        self.current_block = self.AddBlock(self.root)  # Add block 1 to begin program


    # Sets the current block
    def SetCurrent(self, block):
        self.current_block = block

    # Lookup variable's instruction ID in current block's symtable
    #   Return: Instruction ID of variable
    def Lookup(self, var) -> int:
        return self.current_block.symtable[var]

    # Add / update to current block's symtable
    def AddSymbol(self, var, instr_id) -> None:
        print(
            "BB" + str(self.current_block.idx) + ":" + str(var) + " = " + str(instr_id)
        )
        self.current_block.symtable[var] = instr_id

    # Print the current block's symtable
    def PrintSymTable(self) -> None:
        print(self.current_block.symtable)

    def FindDomInstruction(self, op, a, b) -> int:
        if op in OP.DOM_CODES:
            if op == OP.ADDA or op == OP.STORE or op == OP.LOAD:
                dom_list = self.current_block.dom_instructions[OP.LOAD]
            else:
                dom_list = self.current_block.dom_instructions[op]
        else:
            return 0
        if dom_list:
            print("Searching through dom list for " + str(op) + " " + str(a) + " " + str(b))
            for id in dom_list:
                instr = self.FindInstruction(id)
                print("Checking instruction " + str(id) + " " + str(instr.op))
                if instr.op == "kill":
                    print("Found kill")
                    return 0
                if instr and instr.op == op and instr.a == a and instr.b == b:
                    return instr.instr_id
            return 0
        else:
            return 0

    # Adda + Load / Store are considered one instruction, so given adda load and store should be right next to it
    def FindLoadOrStoreInstruction(self, adda) -> int:
        adda_instr = self.FindInstruction(adda)
        return adda_instr.next_instr.instr_id


    # While loop, change all instances of a changed variables
    # 5. Change all following instructions that use { var } to the new { phi_instr } address
    #       a. Instructions in current_join block that use { var } change
    #       b. Instructions in fall block(s) that use { var } add a new instruction
    #           - vars that use i --> updated in sym table to the new instruction
    #           - vars that do not --> left alone
    def ChangeAllSymbols_test(self, block: BlockNode, old_value, new_value):
        orig_block = block
        # First update all instructions in the join block
        for id in orig_block.instructions:
            instruction = self.FindInstruction(id)
            if instruction and instruction.op != OP.PHI:
                if instruction.a == old_value:
                    instruction.a = new_value
                if instruction.b == old_value:
                    instruction.b = new_value
        # Next, update all instructions inside the while loop (following the Fall block)
        seen = []
        seen.append(self.current_block.idx)
        self.SetCurrent(block.children[0])  # Fall block is always child 0
        while (self.current_block.idx not in seen):  # Loop until it sees the same block twice
            for id in self.current_block.instructions:
                instruction = self.FindInstruction(id)
                if (
                    instruction.op != OP.PHI
                    and self.current_block.idx == orig_block.idx
                ) or self.current_block.idx != orig_block.idx:
                    # TODO
                    # If its loop invariant (variable not changed in the loop) want to add the new instruction back
                    # If its loop variant (variable is changed in the loop) want to only modify the instruction
                    # How to know if a variable is loop variant / invariant?
                    # -- In a "while" loop, keep track of all variables that have new assignments. These are loop variants.
                    #  -- All variables not assigned to in the loop is "loop invariant"
                    #   List [ ] of variables that are "variant"
                    #   On a call to Assignment(), if in a while block, append the var being assigned to the list  as necessary
                    #   When this function is called and phi loops down:
                    #       - If instruction to be modified is referenced by an "invariant" var in the symtable:
                    #           - Still modify the original instruction, but then add back the old instruction
                    #           - assign symtable[the invariant variable] = to the new instruction
                    if instruction.a == old_value and instruction.b != old_value:
                        instruction.a = new_value
                        """
                        copy = self.AddInstruction(instruction.op, new_value, instruction.b)
                        for sym in self.current_block.symtable:
                            if self.current_block.symtable[sym] == instruction.instr_id:
                                self.current_block.symtable[sym] = copy
                        """
                    elif instruction.a != old_value and instruction.b == old_value:
                        instruction.b = new_value
                        """
                        copy = self.AddInstruction(instruction.op, instruction.a, new_value)
                        for sym in self.current_block.symtable:
                            if self.current_block.symtable[sym] == instruction.instr_id:
                                self.current_block.symtable[sym] = copy
                        """
                    elif instruction.a == old_value and instruction.b == old_value:
                        instruction.a = new_value
                        instruction.b = new_value
                        """
                        copy = self.AddInstruction(instruction.op, new_value, new_value)
                        for sym in self.current_block.symtable:
                            if self.current_block.symtable[sym] == instruction.instr_id:
                                self.current_block.symtable[sym] = copy
                        """
            seen.append(self.current_block.idx)
            self.SetCurrent(self.current_block.children[0])

        self.SetCurrent(orig_block)

    def ChangeAllSymbols(self, block, old_value, new_value):
        # Change the symbol for all instructions after the given instruction
        # First modify the rest of the current join block
        print("Change All Symbols")
        curr_block = block
        print("Changing instructions below phi")
        for i, instr in enumerate(curr_block.instructions):
            if (i >= block.while_phi_idx):
                print("Current: " + str(instr))
                self.ChangeSymbol(self.FindInstruction(instr), curr_block, old_value, new_value)
        # Next, modify the rest of the blocks all children
        stack = []
        seen_join = []
        seen_while_join = []
        curr_block = None
        stack.append(block.children[0])
        print("Block child 0 : " + str(block.children[0].idx))
        stack.append(block.children[1])
        print("Block child 1 : " + str(block.children[1].idx))
        seen_while_join.append(block.idx)
        # Search through the rest of the blocks
        while len(stack) > 0:
            curr_block = stack.pop(0)

            print("Block: " + str(curr_block.idx))
            for i in range(len(curr_block.instructions)):
                instructions = curr_block.instructions[i]
                print("For instruction " + str(instructions))
                instruction = self.FindInstruction(instructions)
                add = self.ChangeSymbol(instruction, curr_block, old_value, new_value)
                if (add):
                    i += 1
                i += 1
            for children in reversed(curr_block.children):
                if children:
                    if children.type == BlockNode.JOIN:
                        if children.idx in seen_join:
                            stack.insert(0, children)
                        else:
                            seen_join.append(children.idx)
                    elif children.type == BlockNode.WHILE_JOIN:
                        # if children.idx not in seen_while_join:
                        #     stack.insert(0, children)
                        #    seen_while_join.append(children.idx)
                        continue
                    else:
                        stack.insert(0, children)

    # Return if an instruction was added
    def ChangeSymbol(self, curr_instruction, curr_block, old_value, new_value) -> bool:
        # Change the symbol for all instructions in the block
        if curr_instruction.a == old_value or curr_instruction.b == old_value:
            print("Modifying instruction " + str(curr_instruction.instr_id) + " " +
                    str(curr_instruction.op) + " " + str(curr_instruction.a) + " " + str(curr_instruction.b))
            # Standard case: Modify instruction
            # ONLY if uses invariant: Modify instruction + Add back old instruction
            old_op = curr_instruction.op
            old_a = curr_instruction.a
            old_b = curr_instruction.b
            # 1. Modify instruction
            if curr_instruction.a == old_value:
                curr_instruction.a = new_value
            if curr_instruction.b == old_value:
                curr_instruction.b = new_value
            # 2. Check if its an invariant and if so, add a copy of the old instruction
            # Get a list of variables that are mapped to this instruction
            vars_to_adjust = []
            for sym in curr_block.symtable:
                if curr_block.symtable[sym] == curr_instruction.instr_id:
                    vars_to_adjust.append(sym)
            print("Vars to adjust: " + str(vars_to_adjust))
            # Check through each of the above variables for invariants
            used_invariant = []
            # For each var that points to that instruction
            for vars in vars_to_adjust:
                if (curr_block.usedvartable[vars] is not None):
                    # For each variable that var uses
                    for check_var in curr_block.usedvartable[vars]:
                        # Check if its an invariant 
                        if curr_block.vartable[check_var] == 0:   
                            # Used invariant
                            used_invariant.append(vars)
            print("Vars to adjust that used invariant: " + str(used_invariant))
            # If there were any instructions that used invariants
            if len(used_invariant) > 0:
                # Create a copy of the instruction
                orig_block = self.current_block
                self.SetCurrent(curr_block)
                id = self.AddInstruction(old_op, old_a, old_b)
                for var in used_invariant:
                    curr_block.symtable[var] = id
                self.SetCurrent(orig_block)
                return True
        return False


    def FindInstructionBlock(self, id) -> BlockNode:
        stack = []
        seen_join = []
        seen_while_join = []
        curr_block = None
        stack.append(self.root)
        # Construct the nodes first
        while len(stack) > 0:
            curr_block = stack.pop(0)
            for instr in curr_block.instructions:
                if instr == id:
                    return curr_block
            for children in reversed(curr_block.children):
                if children:
                    if children.type == BlockNode.JOIN:
                        if children.idx in seen_join:
                            stack.insert(0, children)
                        else:
                            seen_join.append(children.idx)
                    elif children.type == BlockNode.WHILE_JOIN:
                        if children.idx not in seen_while_join:
                            stack.insert(0, children)
                            seen_while_join.append(children.idx)
                    else:
                        stack.insert(0, children)
    # ------------------------------------------------------------------------------------

    # Add root (called on creation)
    #   Return: New block
    def AddRoot(self) -> BlockNode:
        new_block = BlockNode(self.index)
        new_block.dom_instructions = (
            {  # List of previous dom instruction ids (only those that has CSE enabled)
                OP.CONST: [],
                OP.ADD: [],
                OP.SUB: [],
                OP.MUL: [],
                OP.DIV: [],
                OP.CMP: [],
                OP.LOAD: [],  # also includes stores and adda
            }
        )
        for i in self.list_of_vars:
            new_block.vartable[i] = 0
            new_block.usedvartable[i] = []
        self.SetCurrent(new_block)
        self.index += 1
        return new_block

    # Adds a const instruction to the root
    def AddConst(self, instr) -> None:
        self.root.instructions.append(instr)

    # Add block directly below the arg block
    #   Return: New block
    def AddBlock(self, block) -> BlockNode:
        new_block = BlockNode(self.index)
        block.children[0] = new_block
        new_block.parents[0] = block
        new_block.symtable = block.symtable.copy()
        new_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        self.SetCurrent(new_block)
        new_block.dom_block = block
        for i in self.list_of_vars:
            new_block.vartable[i] = 0
            new_block.usedvartable[i] = []
        self.index += 1
        return new_block

    # Add If block: Fall-join
    #   Returns: List of new blocks: list[fall block, join block]
    def AddIfBranch(self, block) -> tuple:
        # Save the block's children for connection later
        after_block = block.children[0]
        # Create "fall-through" path
        fall_block = BlockNode(self.index)
        fall_block.symtable = block.symtable.copy()
        fall_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        fall_block.dom_block = block
        for i in self.list_of_vars:
            fall_block.vartable[i] = 0
            fall_block.usedvartable[i] = []
        fall_block.type = BlockNode.FALL  # Designate as a branch block
        self.index += 1
        # Create "join" block
        join_block = BlockNode(self.index)
        join_block.symtable = block.symtable.copy()
        join_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        join_block.dom_block = block
        for i in self.list_of_vars:
            join_block.vartable[i] = 0
            join_block.usedvartable[i] = []
        join_block.type = BlockNode.JOIN  # Designate as a join block
        self.index += 1
        # Finish connections
        block.SetChildren(fall_block, join_block)
        fall_block.SetParent(block)
        fall_block.SetChild(join_block)
        join_block.SetParents(fall_block, block)
        # Update the new current join_block
        self.current_join_blocks.insert(0, join_block)
        # If a block came after, set the "After block"""
        if after_block is not None:
            join_block.SetChild(after_block)
            if after_block.parents[0].idx == block.idx:
                after_block.SetParent(join_block)
            else:
                after_block.SetParents(after_block.parents[0], join_block)
        return [fall_block, join_block]

    # Add Else branch as a "sibling" to the given fall_branch
    #   Return created branch block
    def AddElseBranch(
        self,
        block: BlockNode,
        top_fall_block: BlockNode,
        bot_fall_block: BlockNode,
        join_block: BlockNode,
    ) -> BlockNode:
        # Create "fall through" path
        branch_block = BlockNode(self.index)
        branch_block.symtable = block.symtable.copy()
        branch_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        branch_block.dom_block = block
        branch_block.type = BlockNode.BRANCH  # Designate as a branch block
        for i in self.list_of_vars:
            branch_block.vartable[i] = 0
            branch_block.usedvartable[i] = []
        self.index += 1
        # Finish connections
        branch_block.SetParent(block)
        branch_block.SetChild(join_block)
        block.SetChildren(top_fall_block, branch_block)
        join_block.SetParents(bot_fall_block, branch_block)
        self.printBlock(branch_block, branch_block.idx)
        return branch_block

    # Add the while branch blocks given the current block (Join block, Fall block, Follow block)
    def AddWhileBranch(self, block: BlockNode) -> tuple:
        # print("################################### DEBUG ##################################### ")
        # print("Before While branch")
        # self.print()
        after_block = block.children[0]
        # Create join block
        join_block = BlockNode(self.index)
        join_block.symtable = block.symtable.copy()
        join_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        join_block.dom_block = block
        join_block.type = BlockNode.WHILE_JOIN
        for i in self.list_of_vars:
            join_block.vartable[i] = 0
            join_block.usedvartable[i] = []
        self.index += 1
        # Create Fall block
        fall_block = BlockNode(self.index)
        fall_block.symtable = block.symtable.copy()
        fall_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        fall_block.dom_block = join_block
        fall_block.type = BlockNode.FALL
        for i in self.list_of_vars:
            fall_block.vartable[i] = 0
            fall_block.usedvartable[i] = []
        self.index += 1
        # Create Follow block
        follow_block = BlockNode(self.index)
        follow_block.symtable = block.symtable.copy()
        follow_block.dom_instructions = copy.deepcopy(block.dom_instructions)
        follow_block.dom_block = join_block
        follow_block.type = BlockNode.FOLLOW
        for i in self.list_of_vars:
            follow_block.vartable[i] = 0
            follow_block.usedvartable[i] = []
        self.index += 1
        # Create connections
        block.SetChild(join_block)
        fall_block.SetParent(join_block)
        join_block.SetChildren(fall_block, follow_block)
        follow_block.SetParent(join_block)
        # Create "loop back" connection
        fall_block.SetChild(join_block)
        join_block.SetParents(block, fall_block)
        # Update the new current join_block
        self.current_join_blocks.insert(0, join_block)
        # If a block came after, set the "After block"""
        if after_block is not None:
            follow_block.SetChild(after_block)
            if after_block.parents[0].idx == block.idx:
                after_block.SetParent(follow_block)
            else:
                after_block.SetParents(after_block.parents[0], follow_block)
        # print("After While branch")
        # self.print()
        # print("################################### ##################################### ")
        return [join_block, fall_block, follow_block]

    def LinkBlock(self, id, block):
        instr = self.FindInstruction(block.waiting_on[0])
        if block.waiting_on[1] == 0:
            instr.a = id
            block.waiting_on = (0, 0)
        else:
            instr.b = id
            block.waiting_on = (0, 0)

    # ---------------------------------------------------------------------------------------------

    def InsertInstruction(self, block: BlockNode, id):
        print(
            "Inserting to BB"
            + str(block.idx)
            + " | "
            + self.FindInstruction(id).toString()
        )
        block.AddInstructionToBlock(id)
        instr = self.FindInstruction(id)
        if instr.op in OP.DOM_CODES:
            if instr.op == OP.LOAD or instr.op == OP.ADDA or instr.op == OP.STORE:
                block.dom_instructions[OP.LOAD].insert(0, id)
            else:
                block.dom_instructions[instr.op].insert(0, id)
        if block.waiting_on[0] > 0:
            self.LinkBlock(id, block)

    def InsertInstructionAtFront(self, block: BlockNode, id):
        print(
            "Inserting to front of BB"
            + str(block.idx)
            + " | "
            + self.FindInstruction(id).toString()
        )
        block.AddInstructionToFront(id)
        instr = self.FindInstruction(id)
        if instr.op in OP.DOM_CODES:
            if instr.op == OP.LOAD or instr.op == OP.ADDA or instr.op == OP.STORE:
                block.dom_instructions[OP.LOAD].insert(0, id)
            else:
                block.dom_instructions[instr.op].insert(0, id)
        if block.waiting_on[0] > 0:
            self.LinkBlock(id, block)

    def InsertInstructionAtIndex(self, block: BlockNode, id, idx):
        print(
            "Inserting to idx "
            + str(idx)
            + " of BB"
            + str(block.idx)
            + " | "
            + self.FindInstruction(id).toString()
        )
        block.AddInstructionToIndex(id, idx)
        instr = self.FindInstruction(id)
        if instr.op in OP.DOM_CODES:
            if instr.op == OP.LOAD or instr.op == OP.ADDA or instr.op == OP.STORE:
                block.dom_instructions[OP.LOAD].insert(0, id)
            else:
                block.dom_instructions[instr.op].insert(0, id)

    # Inserts a new instruction in the InstructionList in the block tree
    def AddConstInstruction(self, const):
        id = self.FindConst(const)
        if id != 0:
            return id
        id = self.instrList.AddConst(const)
        self.InsertInstruction(self.root, id)
        return id

    def FindConst(self, const) -> int:
        for ids in self.root.instructions:
            instruction = self.FindInstruction(ids)
            if instruction:
                if instruction.op == OP.CONST and instruction.a == const:
                    return instruction.instr_id
        return 0

    # Add an instruction to the current block
    #   Return the instruction ID
    def AddInstruction(self, op, a, b) -> int:
        # If in a "fall block" of a while loop, on new assignments only check for CSE within its block only
        id = self.FindDomInstruction(
            op, a, b
        )  # Check if there is a domating instruction
        print(str(op) + " " + str(a) + " " + str(b) + " | Find dom?: " + str(id))
        if id != 0:
            return id  # If there is, return the dom instruction's ID
        id = self.instrList.AddInstruction(op, a, b)  # Otherwise make a new instruction
        self.InsertInstruction(self.current_block, id)
        return id
    
    def AddInstructionNoCSE(self, op, a, b) -> int:
        print(str(op) + " " + str(a) + " " + str(b) + " | Not looking for a dom")
        id = self.instrList.AddInstruction(op, a, b)  # Otherwise make a new instruction
        self.InsertInstruction(self.current_block, id)
        return id

    def AddInstructionAtIndex(self, index, op, a, b) -> int:
        id = self.instrList.AddInstruction(op, a, b)  # Otherwise make a new instruction
        self.InsertInstructionAtIndex(self.current_block, id, index)
        return id

    # Add a read instruction to the current block
    def AddReadInstruction(self) -> int:
        id = self.instrList.AddReadInstruction()
        self.InsertInstruction(self.current_block, id)
        return id

    # Add a end instruction to the current block
    def AddEndInstruction(self) -> int:
        id = self.instrList.AddEndInstruction()
        self.InsertInstruction(self.current_block, id)
        return id

    # Add a read instruction to the current block
    def AddWriteInstruction(self, output) -> int:
        id = self.instrList.AddWriteInstruction(output)
        self.InsertInstruction(self.current_block, id)
        return id

    # Add a read instruction to the current block
    def AddWriteNLInstruction(self) -> int:
        id = self.instrList.AddWriteNLInstruction()
        self.InsertInstruction(self.current_block, id)
        return id

    # Add a phi (join) function
    def AddPhiInstruction(self, a, b):
        id = self.instrList.AddPhiInstruction(a, b)
        self.InsertInstruction(self.current_block, id)
        return id

    # Function for use in while loops
    def InsertPhiAtFront(self, a, b):
        id = self.instrList.AddPhiInstruction(a, b)
        self.InsertInstructionAtFront(self.current_block, id)
        return id

    # Function for use in while loops
    def InsertPhiAtIndex(self, a, b, idx):
        id = self.instrList.AddPhiInstruction(a, b)
        self.InsertInstructionAtIndex(self.current_block, id, idx)
        return id

    # Add an empty block as a placeholder
    def AddEmptyInstruction(self):
        id = self.instrList.AddEmptyInstruction()
        self.InsertInstruction(self.current_block, id)
        return id

    def AddKillInstruction(self, array_name):
        id = self.instrList.AddKillInstruction(array_name)
        self.InsertInstructionAtFront(self.current_block, id)
        return id

    # --------------------------------------------------------------

    # Finds the instruction in the InstructionList in the block tree
    def FindInstruction(self, id) -> InstructionNode:
        return self.instrList.FindInstruction(id)

    # Search for a block by its ID
    #   Return: The block item, or None if not found
    def FindBlock(self, root, x) -> int:
        if root is None or root.idx == x:
            return root
        print(str(root.idx))
        l = self.FindBlock(root.children[0], x)
        r = self.FindBlock(root.children[1], x)
        if l:
            return l
        if r:
            return r

    def printBlock(self, block, num):
        print("---------------------------")
        print("BB" + str(num) + " " + str(block.type))
        for instr in block.instructions:
            self.instrList.FindInstruction(instr).printInstruction()
        print("Parents: ")
        for parent in block.parents:
            if parent:
                print("BB" + str(parent.idx))
        print("Children: ")
        for child in block.children:
            if child:
                print("BB" + str(child.idx))
        print("Dom instructions:")
        for instr in block.dom_instructions:
            print(str(instr) + " : " + str(block.dom_instructions[instr]))
        print("Sym table:")
        for sym in block.symtable:
            print(str(sym) + " : " + str(block.symtable[sym]))
        print("Invariant table: ")
        for sym in block.vartable:
            print(str(sym) + " : " + str(block.vartable[sym]))
        print("Used Var table:")
        for sym in block.usedvartable:
            print(str(sym) + " : " + str(block.usedvartable[sym])) 

    # Print blocks with "level-order traversal" using FIFO
    def print(self) -> None:
        stack = []
        seen_join = []
        seen_while_join = []
        curr_block = None
        num = 0
        stack.append(self.root)
        # Construct the nodes first
        while len(stack) > 0:
            curr_block = stack.pop(0)
            self.printBlock(curr_block, curr_block.idx)
            num += 1
            for children in reversed(curr_block.children):
                if children:
                    if children.type == BlockNode.JOIN:
                        if children.idx in seen_join:
                            stack.insert(0, children)
                        else:
                            seen_join.append(children.idx)
                    elif children.type == BlockNode.WHILE_JOIN:
                        if children.idx not in seen_while_join:
                            stack.insert(0, children)
                            seen_while_join.append(children.idx)
                    else:
                        stack.insert(0, children)
