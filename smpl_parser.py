# Tokenizer + Parser
# Author: Brandon Wang

from tokenizer import Tokenizer
from result import Result
from instructions import InstructionList, InstructionNode
from op_codes import OP

# Simple recursive descent parser for smpl
# SSA Format: op | x | y
# Need three different data structures:
#   Program Variables: Keep table of which program variable has what value at the current time
#       Needed for Copy Propagation
#   CSE - Common Subexpression Elimination. Only 2 blocks that have control flow in our smpl parser:
#       If / while
#       Can hardcode this into our compiler, don't need to compute after the fact
#   Linked list of all add instructions that are generated
#       Pointer to the previous instruction with the same op code that dominates the current place
#       Used for finding CSE, will consider only instructions that have the same OP code and is dominated
#       Array of pointers that point to the previous instruction
#       Don't need to explicitly check for dominance

from blocks import BlockTree, BlockNode


class Parser:
    def __init__(self, filename):
        self.tokenizer = Tokenizer(filename)  # Private tokenizer object
        # self.instrList = InstructionList()      # Create LinkedList of instruction nodes
        self.blocks = BlockTree()
        # Serves as the "current token" that is being read
        self.currToken = 0
        self.inputSym = 0  # Current token on the input
        # Array dict to store sizes of arrays
        self.array_list = {}
        self.error = 0  # Internal error code
        self.next()
        print(
            "Parser created. First token: "
            + str(self.tokenizer.Id2String(self.tokenizer.id))
        )

    def next(self):
        self.currToken = self.inputSym  # Update current token
        self.inputSym = self.tokenizer.GetNext()  # Lookahead 1 token
        if self.inputSym == Tokenizer.TOKEN_ID:
            print(
                "Next (id): "
                + str(self.tokenizer.id)
                + ": "
                + str(self.tokenizer.Id2String(self.tokenizer.id))
            )
        elif self.inputSym == Tokenizer.TOKEN_NUM:
            print("Next (num): " + str(self.tokenizer.val))
        else:
            print(
                "Next (sym): "
                + str(self.inputSym)
                + ": "
                + str(self.tokenizer.Id2String(self.inputSym))
            )

    def CheckFor(self, token):
        if self.inputSym == Tokenizer.TOKEN_ID and self.tokenizer.id == token:
            self.next()
        elif self.inputSym == token:
            self.next()
        else:
            errorMsg = (
                "Expected: "
                + str(self.tokenizer.Id2String(token))
                + "| Got: "
                + str(self.tokenizer.Id2String(self.inputSym))
            )
            self.SyntaxErr(errorMsg)

    def SyntaxErr(self, errMsg):
        print("Syntax Error: " + errMsg)
        self.error = 1

    # ---------------------------------------------------------------------------

    # Start Parse function, returns the full block tree
    def Parse(self) -> InstructionList:
        print(
            "========================== Starting parse ======================================="
        )
        # Check for 'main' to signal program start
        self.CheckFor(Tokenizer.TOKEN_MAIN)
        # Check for var declarations
        if (
            self.inputSym == Tokenizer.TOKEN_ID
            and self.tokenizer.id == Tokenizer.TOKEN_VAR
        ):
            
            self.next()
            vars_done = False
            while not vars_done:
                id = self.tokenizer.id
                self.blocks.list_of_vars.append(self.tokenizer.Id2String(id))
                self.next()
                if self.inputSym == Tokenizer.TOKEN_COMMA:
                    self.next()
                elif self.inputSym == Tokenizer.TOKEN_SEMI:
                    self.next()
                    vars_done = True
                else:
                    self.SyntaxErr("Syntax Error in variable declarations")
                    vars_done = True
                    return

        # Check for array declarations
        arr = False
        arr_name = None
        if (
            self.inputSym == Tokenizer.TOKEN_ID
            and self.tokenizer.id == Tokenizer.TOKEN_ARR
        ):
            arr = True
            self.CheckFor(Tokenizer.TOKEN_ARR)
            self.CheckFor(Tokenizer.TOKEN_OPENBRACKET)  # [
            size = 0
            if self.inputSym == Tokenizer.TOKEN_NUM:
                size = self.tokenizer.val  # next num should be size of array
            else:
                self.SyntaxErr("Array needs an initial size")
                return
            self.next()
            self.CheckFor(Tokenizer.TOKEN_CLOSEBRACKET)  # ]
            if self.inputSym == Tokenizer.TOKEN_ID:
                arr_name = self.tokenizer.Id2String(
                    self.tokenizer.id
                )  # next should be name of the array
                self.blocks.list_of_vars.append(arr_name)
            else:
                self.SyntaxErr("Array has no name")
                return
            self.next()
            self.CheckFor(Tokenizer.TOKEN_SEMI)  # ;

            

        # Create the block tree
        self.blocks.Create()
        for vars in self.blocks.list_of_vars:
            self.blocks.AddSymbol(vars, -1)
        if (arr):
            # To designate arrays, assign the var in the symtable to -2
            self.blocks.AddSymbol(arr_name, -2)
            # Add consts needed for arrays
            self.blocks.AddConstInstruction(4)
            self.blocks.AddConstInstruction(str(arr_name) + "_adr")


        # Check for beginning brace
        self.CheckFor(Tokenizer.TOKEN_BEGIN)
        self.Statement()
        # Check for ending brace
        self.CheckFor(Tokenizer.TOKEN_END)
        # Check for end program period
        self.CheckFor(Tokenizer.TOKEN_PERIOD)
        self.blocks.AddEndInstruction()
        print("--------------------")
        print("Symbol Table:")
        print(self.blocks.PrintSymTable())
        print("--------------------")
        self.blocks.print()
        # Return the Block Tree
        return self.blocks

    # Function should incorporate CSE and Delayed Code Generation
    def Compute(self, op, a, b) -> Result:
        print("Computing")
        x = Result()
        x.variables = a.variables + b.variables
        if a.kind == Result.CONST and b.kind == Result.CONST:  # CONST op CONST
            x.kind = Result.CONST
            if op == OP.ADD:
                x.value = a.value + b.value
            elif op == OP.SUB:
                x.value = a.value - b.value
            elif op == OP.MUL:
                x.value = a.value * b.value
            elif op == OP.DIV:
                x.value = a.value / b.value
        elif a.kind == Result.VAR and b.kind == Result.CONST:  # VAR op CONST
            if a.address == -1:  # Use of uninitialized variable
                const_zero = self.blocks.AddConstInstruction(0)
                self.SyntaxErr("WARNING: Use of un-initialized variable, setting to 0.")
                a.address = const_zero
            instruction = self.blocks.FindInstruction(a.address)
            print("VAR op CONST")
            print(instruction.toString())
            if instruction.op == OP.CONST:
                x.kind = Result.CONST
                val = instruction.a
                if op == OP.ADD:
                    x.value = val + b.value
                elif op == OP.SUB:
                    x.value = val - b.value
                elif op == OP.MUL:
                    x.value = val * b.value
                elif op == OP.DIV:
                    x.value = val / b.value
            else:
                x.kind = Result.VAR
                const_addr = self.blocks.AddConstInstruction(b.value)
                # If assignment uses a variant, create a new instruction without CSE
                for var in x.variables:
                    print("")
                    if self.blocks.current_block.vartable[var] == 1:
                        x.address = self.blocks.AddInstructionNoCSE(op, a.address, const_addr)
                        return x
                x.address = self.blocks.AddInstruction(op, a.address, const_addr)

        elif a.kind == Result.CONST and b.kind == Result.VAR:  # CONST op VAR
            if b.address == -1:  # Use of uninitialized variable
                const_zero = self.blocks.AddConstInstruction(0)
                self.SyntaxErr("WARNING: Use of un-initialized variable, setting to 0.")
                b.address = const_zero
            instruction = self.blocks.FindInstruction(b.address)
            if instruction.op == OP.CONST:
                x.kind = Result.CONST
                val = instruction.a
                if op == OP.ADD:
                    x.value = a.value + val
                elif op == OP.SUB:
                    x.value = a.value - val
                elif op == OP.MUL:
                    x.value = a.value * val
                elif op == OP.DIV:
                    x.value = a.value / val
            else:
                x.kind = Result.VAR
                const_addr = self.blocks.AddConstInstruction(a.value)
                x.address = self.blocks.AddInstruction(op, const_addr, b.address)

        elif a.kind == Result.VAR and b.kind == Result.VAR:  # VAR op VAR
            if a.address == -1:  # Use of uninitialized variable
                const_zero = self.blocks.AddConstInstruction(0)
                self.SyntaxErr("WARNING: Use of un-initialized variable, setting to 0.")
                a.address = const_zero
            if b.address == -1:  # Use of uninitialized variable
                const_zero = self.blocks.AddConstInstruction(0)
                self.SyntaxErr("WARNING: Use of un-initialized variable, setting to 0.")
                b.address = const_zero
            instruction_a = self.blocks.FindInstruction(a.address)
            instruction_b = self.blocks.FindInstruction(b.address)
            if (
                instruction_a.op == OP.CONST and instruction_b.op == OP.CONST
            ):  # Both vars are constants
                x.kind = Result.CONST
                val_a = instruction_a.a
                val_b = instruction_b.a
                if op == OP.ADD:
                    x.value = val_a + val_b
                elif op == OP.SUB:
                    x.value = val_a - val_b
                elif op == OP.MUL:
                    x.value = val_a * val_b
                elif op == OP.DIV:
                    x.value = val_a / val_b
            # Any other case of vars:
            else:
                x.kind = Result.VAR
                x.address = self.blocks.AddInstruction(op, a.address, b.address)
        else:
            # Should not get here
            print("Error occured")
        if x.kind == Result.CONST:
            print("Compute finish (const): " + str(x.value))
        if x.kind == Result.VAR:
            print("Compute finish (Var): " + str(x.address))
        return x

    # Parses an entire statement
    def Statement(self):
        if self.error == 1:
            return
        # Begin statements Loop
        while self.inputSym != Tokenizer.TOKEN_END:
            print("----- Parse statement ----")
            while self.inputSym == Tokenizer.TOKEN_SEMI:
                self.next()
            # Statements should start with a Token
            if self.inputSym == Tokenizer.TOKEN_ID:
                if self.tokenizer.id == Tokenizer.TOKEN_LET:
                    self.Assignment()
                elif self.tokenizer.id == Tokenizer.TOKEN_CALL:
                    self.Function()
                elif self.tokenizer.id == Tokenizer.TOKEN_IF:
                    self.If()
                elif self.tokenizer.id == Tokenizer.TOKEN_WHILE:
                    self.While()
                elif self.tokenizer.id == Tokenizer.TOKEN_ELSE:
                    print("Found else, stop statement.")
                    return
                elif self.tokenizer.id == Tokenizer.TOKEN_FI:
                    print("Found fi, stop statement")
                    return
                elif self.tokenizer.id == Tokenizer.TOKEN_OD:
                    print("Found od, stop statement")
                    return
                else:
                    print("Error: Statement unknown start: " + str(self.tokenizer.id))
                    return
            else:
                self.SyntaxErr(
                    "Invalid statement, starts with: "
                    + str(self.inputSym)
                    + " = "
                    + str(self.tokenizer.Id2String(self.inputSym))
                )
                self.error = 1
                return
            print("----- End statement ----")
        return

    # Parses an Expression
    def E(self) -> Result:
        x = Result()
        y = Result()
        x = self.T()
        while (
            self.inputSym == Tokenizer.TOKEN_PLUS
            or self.inputSym == Tokenizer.TOKEN_MINUS
        ):
            op = 0
            if self.inputSym == Tokenizer.TOKEN_PLUS:
                op = OP.ADD
            else:
                op = OP.SUB
            self.next()
            y = self.T()
            x = self.Compute(op, x, y)
        return x

    # Parses a Term
    def T(self) -> Result:
        x = Result()
        y = Result()
        x = self.F()
        while (
            self.inputSym == Tokenizer.TOKEN_TIMES
            or self.inputSym == Tokenizer.TOKEN_DIV
        ):
            self.next()
            y = self.F()
            x = self.Compute(OP.MUL, x, y)
        return x

    # Parses a Factor
    def F(self) -> Result:
        x = Result()
        if self.inputSym == Tokenizer.TOKEN_OPENPAREN:
            self.next()
            x = self.E()
            self.CheckFor(Tokenizer.TOKEN_CLOSEPAREN)
        elif self.inputSym == Tokenizer.TOKEN_NUM:
            # Factor is a number
            x.kind = Result.CONST
            x.value = self.tokenizer.val
            self.next()
        elif self.inputSym == Tokenizer.TOKEN_ID:
            if self.tokenizer.id == Tokenizer.TOKEN_CALL:
                # Factor is a function
                x.kind = Result.FUNC
                x.function = self.Function()
                self.next()
            elif self.blocks.Lookup(self.tokenizer.Id2String(self.tokenizer.id)) == -2:
                # Factor is an array
                arr_name = self.tokenizer.Id2String(self.tokenizer.id)
                self.next()
                self.CheckFor(Tokenizer.TOKEN_OPENBRACKET)
                if self.inputSym == Tokenizer.TOKEN_ID:
                    # Index is a variable
                    index = self.blocks.Lookup(
                        self.tokenizer.Id2String(self.tokenizer.id)
                    )
                else:
                    # Index is a constant
                    index = self.blocks.AddConstInstruction(self.tokenizer.val)
                self.next()
                self.CheckFor(Tokenizer.TOKEN_CLOSEBRACKET)
                x.kind = Result.VAR
                x.address = self.Load(arr_name, index)
            else:
                # Factor is a variable
                x.kind = Result.VAR
                x.address = self.blocks.Lookup(
                    self.tokenizer.Id2String(self.tokenizer.id)
                )
                x.variables.append(self.tokenizer.Id2String(self.tokenizer.id))
                self.next()

        else:
            self.SyntaxErr("Factor has unexpected symbol: " + str(self.inputSym))
        return x

    # let designator <- expression
    def Assignment(self) -> None:
        # LET
        self.CheckFor(Tokenizer.TOKEN_LET)
        x = Result()
        # DESIGNATOR
        if self.inputSym == Tokenizer.TOKEN_ID:
            var_id = self.tokenizer.Id2String(self.tokenizer.id)
            # Mark var as a "variant" in the block (for while blocks)
            self.blocks.current_block.vartable[var_id] = 1
            self.next()
            index = 0
            if self.inputSym == Tokenizer.TOKEN_OPENBRACKET:
                self.CheckFor(Tokenizer.TOKEN_OPENBRACKET)
                # Designator is an array
                if self.inputSym == Tokenizer.TOKEN_ID:
                    # Index is a variable
                    print("Index is a variable")
                    index = self.blocks.Lookup(
                        self.tokenizer.Id2String(self.tokenizer.id)
                    )
                else:
                    # Index is a constant
                    print("Index is a constant")
                    index = self.blocks.AddConstInstruction(self.tokenizer.val)
                self.next()
                self.CheckFor(Tokenizer.TOKEN_CLOSEBRACKET)
            self.CheckFor(Tokenizer.TOKEN_BECOMES)  # <-
            # Parse the expression
            y = self.E()
            # If any variables were used, assign them in usedvartable
            for vars in y.variables:
                self.blocks.current_block.usedvartable[var_id].append(vars)
            # Assign a const
            if y.kind == Result.CONST:
                id = self.blocks.AddConstInstruction(y.value)
                # Check if array
                if self.blocks.Lookup(var_id) == -2:
                    self.Store(var_id, index, id)
                else:
                    self.blocks.AddSymbol(var_id, id)
                if len(self.blocks.current_join_blocks) > 0:
                    self.Phi(var_id)
            # Assign a var address
            elif y.kind == Result.VAR:
                # Check if array
                if self.blocks.Lookup(var_id) == -2:
                    self.Store(var_id, index, y.address)
                else:
                    self.blocks.AddSymbol(var_id, y.address)
                # Phi handling: Implement the phi function described in BrandisMossenbock
                # Phi steps:
                #   - When parsing branch, on assignment -> create new phi in join block with phi(new_assignment, backup_value)
                #           *backup_value is the original assignment
                #   - Should have a "current join_node pointer" for use that can queue old cur_join_nodes (list with append() and pop())
                #   - When done and now parsing the "else" statement -> Add / update the phi assignments in the join_block
                if len(self.blocks.current_join_blocks) > 0:
                    self.Phi(
                        var_id
                    )  # Check if there is a current join block (current block is in a branch)

            # Read function
            elif y.kind == Result.FUNC:
                self.blocks.AddSymbol(var_id, y.function)
            else:
                self.SyntaxErr("Assignment: unknown result for expression")
        else:
            self.SyntaxErr("Let needs a designator")
            return None

    def Phi(self, var):
        orig_block = self.blocks.current_block
        if len(self.blocks.current_join_blocks) > 0:
            join_block = self.blocks.current_join_blocks[0]
            print("Join block: " + str(join_block.idx))
            old_block = self.blocks.current_block
            self.blocks.SetCurrent(join_block)
            new_value = old_block.symtable[var]
            # Check if an array first
            if new_value == -2:  # Array, no phi, use kill instead
                kill_id = self.blocks.AddKillInstruction(var)
                self.blocks.current_block.dom_instructions[OP.LOAD].insert(0, kill_id)
                # Look through block to see if old commands need to be re-built 
                for i in range(len(self.blocks.current_block.instructions)):
                    instr = self.blocks.current_block.instructions[i]
                    curr_instruction = self.blocks.FindInstruction(instr)
                    a_instr = self.blocks.FindInstruction(curr_instruction.a)
                    b_instr = self.blocks.FindInstruction(curr_instruction.b)
                    if a_instr and a_instr.op == OP.LOAD:
                        print("Found instruction that needs to be reloaded: " + str(curr_instruction.op))
                        instruction_index = self.blocks.current_block.instructions.index(instr)
                        id = self.RebuildLoad(curr_instruction.a, join_block, instruction_index)
                        curr_instruction.a = id
                        i += 5
                    if b_instr and b_instr.op == OP.LOAD:
                        print("Found instruction that needs to be reloaded: " + str(curr_instruction.op))
                        instruction_index = self.blocks.current_block.instructions.index(instr)
                        id = self.RebuildLoad(curr_instruction.b, join_block, instruction_index)
                        curr_instruction.b = id
                        i += 5
                    if a_instr and a_instr.op == OP.STORE:
                        print("Found instruction that needs to be reloaded: " + str(curr_instruction.op))
                        instruction_index = self.blocks.current_block.instructions.index(instr)
                        id = self.RebuildStore(curr_instruction.a, join_block, instruction_index)
                        curr_instruction.a = id
                        i += 5
                    if b_instr and b_instr.op == OP.STORE:
                        print("Found instruction that needs to be reloaded: " + str(curr_instruction.op))
                        instruction_index = self.blocks.current_block.instructions.index(instr)
                        id = self.RebuildStore(curr_instruction.b, join_block, instruction_index)
                        curr_instruction.b = id
                        i += 5
                            
            # Check if in a while loop
            elif join_block.type == BlockNode.WHILE_JOIN:
                # 1. Check if a phi insertion is necessary
                # 2. Insert the phi (No CSE)
                # 3. Save var's old address before change in step 4
                # 4. Change join_block symtable so { var : phi_instr }
                # 5. Change all following instructions that use { var } to the new { phi_instr } address
                #       a. Instructions in current_join block that use { var } change
                #       b. Instructions in fall block(s) that use { var } add a new instruction
                #           - vars that use i --> updated in sym table to the new instruction
                #           - vars that do not --> left alone
                if join_block.symtable[var] != orig_block.symtable[var]:
                    print("WHILE: Inserting Phi into BB" + str(join_block.idx))
                    if join_block.symtable[var] == -1:  # Unintialized variable used
                        return
                    else:
                        orig_value = join_block.symtable[var]
                        phi_instr = 0
                        if self.blocks.current_block.while_phi_idx == 0:
                            phi_instr = self.blocks.InsertPhiAtFront(
                                orig_value, new_value
                            )
                            self.blocks.current_block.while_phi_idx += 1
                        else:
                            phi_instr = self.blocks.InsertPhiAtIndex(
                                orig_value,
                                new_value,
                                self.blocks.current_block.while_phi_idx,
                            )
                            self.blocks.current_block.while_phi_idx += 1
                        print(
                            "Before: "
                            + str(var)
                            + " = "
                            + str(self.blocks.current_block.symtable[var])
                        )
                        self.blocks.AddSymbol(var, phi_instr)
                        print(
                            "After: "
                            + str(var)
                            + " = "
                            + str(self.blocks.current_block.symtable[var])
                        )
                        self.blocks.ChangeAllSymbols(join_block, orig_value, phi_instr)
                        for join_b in self.blocks.current_join_blocks:
                            if join_b.idx == join_block.idx:
                                continue
                            if join_b.symtable[var] == -1:
                                continue
                            mapped_instr = self.blocks.FindInstruction(join_b.symtable[var])
                            if mapped_instr.op == OP.PHI:
                                mapped_instr.b = phi_instr
                                self.blocks.ChangeAllSymbols(join_b, mapped_instr.instr_id, phi_instr)
            # Otherwise in a if branch
            else:
                for join_block in self.blocks.current_join_blocks:
                    if join_block.symtable[var] != old_block.symtable[var]:
                        if (
                            join_block.symtable[var] == -1
                        ):  # Local variable initialized in scope of branch
                            self.blocks.SetCurrent(orig_block)
                        elif (
                            self.blocks.FindInstruction(join_block.symtable[var]).op
                            == OP.PHI
                        ):
                            instr = self.blocks.FindInstruction(join_block.symtable[var])
                            print(
                                "Modifying Phi at "
                                + str(instr.instr_id)
                                + ".b from "
                                + str(instr.b)
                                + " to "
                                + str(new_value)
                            )
                            instr.b = new_value
                            self.blocks.SetCurrent(orig_block)
                            return
                        else:
                            orig_value = join_block.symtable[var]
                            phi_instr = self.blocks.AddPhiInstruction(new_value, orig_value)
                            self.blocks.AddSymbol(var, phi_instr)
                            print(
                                "IF: Inserting Phi into BB"
                                + str(join_block.idx)
                                + " | "
                                + str(phi_instr)
                            )

        self.blocks.SetCurrent(orig_block)

    # Process a function (after a call is made)
    #   Return: id of function node (-1 = error)
    def Function(self) -> int:
        id = -1  # id of node added
        self.CheckFor(Tokenizer.TOKEN_CALL)  # call
        if self.inputSym == Tokenizer.TOKEN_ID:
            func = self.tokenizer.id  # function name
        else:
            self.SyntaxErr("Function not recognized")
        self.next()
        self.CheckFor(Tokenizer.TOKEN_OPENPAREN)  # (

        if func == Tokenizer.TOKEN_INPUTNUM:  # READ function
            id = self.blocks.AddReadInstruction()
        elif func == Tokenizer.TOKEN_OUTPUTNUM:  # WRITE(x) function
            arg = Result()
            if self.inputSym != Tokenizer.TOKEN_CLOSEPAREN:
                arg = self.E()
            if arg.kind == Result.CONST:
                id_const = self.blocks.AddConstInstruction(arg.value)
                id = self.blocks.AddWriteInstruction(id_const)
            else:
                id = self.blocks.AddWriteInstruction(arg.address)

        elif func == Tokenizer.TOKEN_OUTPUTNL:  # WRITE NL function
            self.blocks.AddWriteNLInstruction()
        else:
            self.SyntaxErr("Invalid function call")
        self.CheckFor(Tokenizer.TOKEN_CLOSEPAREN)  # )
        return id

    # Handle If branching statements
    # If follows a control flow diamond-shape (block -> 2 blocks -> join block)
    #   Ex: if a<0 then ... else ... fi;
    def If(self) -> None:
        self.CheckFor(Tokenizer.TOKEN_IF)  # if
        a = self.E()  # expression (LH of compare)
        # relOp (==, !=, <, <=< >, >=)
        relOp = self.inputSym
        self.next()
        b = self.E()  # expression (RH of compare)
        id_a = 0
        id_b = 0
        if a.kind == Result.CONST:  # Add consts if applicable
            id_a = self.blocks.AddConstInstruction(a.value)
        else:
            id_a = a.address
        if b.kind == Result.CONST:
            id_b = self.blocks.AddConstInstruction(b.value)
        else:
            id_b = b.address
        cmp_id = self.blocks.AddInstruction(OP.CMP, id_a, id_b)  # Add CMP instruction
        self.CheckFor(Tokenizer.TOKEN_THEN)  # then
        # Branching
        # If block = Need a branch block and a join block
        op = 0
        # Convert relOp to OP code (opposites, == -> !=)
        if relOp == Tokenizer.TOKEN_EQ:
            op = OP.BNE
        elif relOp == Tokenizer.TOKEN_NEQ:
            op = OP.BEQ
        elif relOp == Tokenizer.TOKEN_LESS:
            op = OP.BGE
        elif relOp == Tokenizer.TOKEN_LEQ:
            op = OP.BGT
        elif relOp == Tokenizer.TOKEN_GTR:
            op = OP.BLE
        elif relOp == Tokenizer.TOKEN_GEQ:
            op = OP.BLT
        relOp_id = self.blocks.AddInstruction(
            op, cmp_id, 0
        )  # Add RelOp instruction, with the second arg NOT FINISHED (still need to link)
        # -----------------------------------------------
        # Create the If / Join blocks
        # print("--------------- Before if call:")
        print("--- IF --- ")
        # self.blocks.print()
        old_block = self.blocks.current_block
        fall_block, join_block = self.blocks.AddIfBranch(self.blocks.current_block)
        # print("--------------- After if call:")
        # self.blocks.print()
        branch_block = join_block
        self.blocks.SetCurrent(fall_block)
        self.Statement()
        # End statements, add a branch instruction to link to join block (to be linked later)
        bra_id = self.blocks.AddInstruction(OP.BRA, 0, 0)

        # -----------------------------------------------

        if self.tokenizer.id == Tokenizer.TOKEN_ELSE:
            print("--- ELSE --- ")
            # if / else - Add an else block
            # print("--------------- Before else call:")
            # self.blocks.print()
            print("=====")
            print("Old: " + str(old_block.idx))
            print("Top fall: " + str(fall_block.idx))
            print("Join: " + str(self.blocks.current_join_blocks[0].idx))
            print("Current: " + str(self.blocks.current_block.idx))
            branch_block = self.blocks.AddElseBranch(
                old_block,
                fall_block,
                self.blocks.current_block,
                self.blocks.current_join_blocks[0],
            )
            # print("--------------- After else call:")
            # self.blocks.print()
            self.CheckFor(Tokenizer.TOKEN_ELSE)
            self.blocks.SetCurrent(branch_block)
            self.Statement()
            if len(branch_block.instructions) == 0:
                # Add an "empty" instruction as placeholder for the block
                print("Add empty placeholder block in branch_block")
                self.blocks.AddEmptyInstruction()

        # -----------------------------------------------

        if self.tokenizer.id == Tokenizer.TOKEN_FI:
            print("--- FI --- ")
            if len(branch_block.instructions) == 0:
                self.blocks.SetCurrent(branch_block)
                # Add an "empty" instruction as placeholder for the block
                print("Add empty placeholder block in either branch / join block")
                self.blocks.AddEmptyInstruction()
            self.CheckFor(Tokenizer.TOKEN_FI)
            self.CheckFor(Tokenizer.TOKEN_SEMI)

        # Finish linkings of previous intructions
        self.blocks.SetCurrent(join_block)
        bra_link = 0
        if (len(join_block.instructions)) == 0:
            join_block.waiting_on = (bra_id, 0)
        else:
            self.blocks.FindInstruction(bra_id).a = join_block.instructions[0]
        self.blocks.FindInstruction(relOp_id).b = branch_block.instructions[0]
        self.blocks.SetCurrent(join_block)
        # Update the current join block
        self.blocks.current_join_blocks.pop(0)

    def While(self) -> None:
        self.CheckFor(Tokenizer.TOKEN_WHILE)  # WHILE
        a = self.E()  # expression (LH of compare)
        # relOp (==, !=, <, <=< >, >=)
        relOp = self.inputSym
        self.next()
        b = self.E()  # expression (RH of compare)
        id_a = 0
        id_b = 0
        if a.kind == Result.CONST:  # Add consts if applicable
            id_a = self.blocks.AddConstInstruction(a.value)
        else:
            id_a = a.address
        if b.kind == Result.CONST:
            id_b = self.blocks.AddConstInstruction(b.value)
        else:
            id_b = b.address
        self.CheckFor(Tokenizer.TOKEN_DO)  # do

        # Create the blocks before parsing (Join block, Fall block, Follow block)
        join_block, fall_block, follow_block = self.blocks.AddWhileBranch(
            self.blocks.current_block
        )
        # -----------------------------------------------
        # Parse the branch / cmp instructions on the join block first
        self.blocks.SetCurrent(join_block)
        cmp_id = self.blocks.AddInstruction(OP.CMP, id_a, id_b)  # Add CMP instruction
        # Start while loop parsing
        op = 0
        # Convert relOp to OP code (opposites, == -> !=)
        if relOp == Tokenizer.TOKEN_EQ:
            op = OP.BNE
        elif relOp == Tokenizer.TOKEN_NEQ:
            op = OP.BEQ
        elif relOp == Tokenizer.TOKEN_LESS:
            op = OP.BGE
        elif relOp == Tokenizer.TOKEN_LEQ:
            op = OP.BGT
        elif relOp == Tokenizer.TOKEN_GTR:
            op = OP.BLE
        elif relOp == Tokenizer.TOKEN_GEQ:
            op = OP.BLT
        relOp_id = self.blocks.AddInstruction(
            op, cmp_id, 0
        )  # Add RelOp instruction (still need to link second arg)
        # -----------------------------------------------
        # Inside the while loop: parse to fall block
        self.blocks.SetCurrent(fall_block)
        self.Statement()

        if self.tokenizer.id == Tokenizer.TOKEN_OD:
            print("--- OD --- ")
            self.CheckFor(Tokenizer.TOKEN_OD)
            self.CheckFor(Tokenizer.TOKEN_SEMI)
            bra_id = self.blocks.AddInstruction(OP.BRA, join_block.instructions[0], 0)

        # -----------------------------------------------
        # While loop finished
        self.blocks.SetCurrent(follow_block)
        follow_block.waiting_on = (relOp_id, 1)
        follow_block.symtable = join_block.symtable.copy()

        # Update the current join block
        self.blocks.current_join_blocks.pop(0)

    def Store(self, arr, index, val):
        print("Store(" + str(arr) + ", " + str(index) + ", " + str(val) + ")")
        # First check if arr[index] has already been stored previously
        # Check if const #4 has been created
        elem_size_id = self.blocks.AddConstInstruction(4)
        print("Position of elem_size_id: " + str(elem_size_id))
        # Check if the mul to find index has been created
        mul = self.blocks.FindDomInstruction(OP.MUL, index, elem_size_id)
        if mul == 0:
            mul = self.blocks.AddInstruction(OP.MUL, index, elem_size_id)
        print("Position of mul: " + str(mul))
        # Check if the const for the base of arr has been created
        base = self.blocks.AddConstInstruction(str(arr) + "_adr")
        # Check if the add to get base array start has been created
        add = self.blocks.FindDomInstruction(OP.ADD, "#BASE", base)
        if add == 0:
            add = self.blocks.AddInstruction(OP.ADD, "#BASE", base)
        # Check if adda has been created or if it encounters a KILL (adda + store = load)
        adda = self.blocks.FindDomInstruction(OP.ADDA, mul, add)
        if adda == 0:
            adda = self.blocks.AddInstruction(OP.ADDA, mul, add)
            store = self.blocks.AddInstruction(OP.STORE, adda, val)
        else:
            # Check if value changed
            store = self.blocks.FindLoadOrStoreInstruction(adda)
            if self.blocks.FindInstruction(store).b != val:
                store = self.blocks.AddInstruction(OP.STORE, adda, val)
        return store
    
    # old_store = Old store command to rebuild
    # block = Block to insert into
    # idx = Index of block to insert into
    def RebuildStore(self, old_store, block, idx):
        store_cmd = self.blocks.FindInstruction(old_store)
        adda = self.blocks.FindInstruction(store_cmd.a)
        mul = self.blocks.FindInstruction(adda.a)
        add = self.blocks.FindInstruction(adda.b)
    
        index = self.blocks.FindInstruction(mul.a)
        val = self.blocks.FindInstruction(store_cmd.b)

        orig_block = self.blocks.current_block
        self.blocks.SetCurrent(block)
        new_mul = self.blocks.AddInstructionAtIndex(idx, OP.MUL, index, mul.b)
        new_add = self.blocks.AddInstructionAtIndex(idx+1, OP.ADD, "#BASE", add.b)
        new_adda = self.blocks.AddInstructionAtIndex(idx+2, OP.ADDA, new_mul, new_add)
        new_store = self.blocks.AddInstructionAtIndex(idx+3, OP.STORE, new_adda, val)
        self.blocks.SetCurrent(orig_block)

        return new_store


    def Load(self, arr, index) -> int:
        # Check if there is a kill first


        print("Load(" + str(arr) + ", " + str(index) + ")")
        # First check if arr[index] has already been loaded previously
        # Check if const #4 has been created
        elem_size_id = self.blocks.AddConstInstruction(4)
        print("Position of elem_size_id: " + str(elem_size_id))
        # Check if the mul to find index has been created
        mul = self.blocks.FindDomInstruction(OP.MUL, index, elem_size_id)
        if mul == 0:
            mul = self.blocks.AddInstruction(OP.MUL, index, elem_size_id)
        print("Position of mul: " + str(mul))
        # Check if the const for the base of arr has been created
        base = self.blocks.AddConstInstruction(str(arr) + "_adr")
        # Check if the add to get base array start has been created
        add = self.blocks.FindDomInstruction(OP.ADD, "#BASE", base)
        if add == 0:
            add = self.blocks.AddInstruction(OP.ADD, "#BASE", base)
        # Check if adda has been created or if it encounters a KILL (adda + load = load)
        adda = self.blocks.FindDomInstruction(OP.ADDA, mul, add)
        if adda == 0:
            adda = self.blocks.AddInstruction(OP.ADDA, mul, add)
            load = self.blocks.AddInstruction(OP.LOAD, adda, 0)
        else:
            load = self.blocks.FindLoadOrStoreInstruction(adda)


        """
        elem_size_id = self.blocks.AddConstInstruction(4)
        mul = self.blocks.FindDomInstruction(OP.MUL, index, elem_size_id)
        base = self.blocks.AddConstInstruction(str(arr) + "_adr")
        add = self.blocks.FindDomInstruction(OP.ADD, "#BASE", base)
        """

        return load

    # old_store = Old store command to rebuild
    # block = Block to insert into
    # idx = Index of block to insert into
    def RebuildLoad(self, old_load, block, idx) -> int:
        load_cmd = self.blocks.FindInstruction(old_load)
        adda = self.blocks.FindInstruction(load_cmd.a)
        mul = self.blocks.FindInstruction(adda.a)
        add = self.blocks.FindInstruction(adda.b)
        index = self.blocks.FindInstruction(mul.a)

        orig_block = self.blocks.current_block
        self.blocks.SetCurrent(block)
        new_mul = self.blocks.AddInstructionAtIndex(idx, OP.MUL, index, mul.b)
        new_add = self.blocks.AddInstructionAtIndex(idx+1, OP.ADD, "#BASE", add.b)
        new_adda = self.blocks.AddInstructionAtIndex(idx+2, OP.ADDA, new_mul, new_add)
        new_store = self.blocks.AddInstructionAtIndex(idx+3, OP.LOAD, new_adda, 0)
        self.blocks.SetCurrent(orig_block)

        return new_store