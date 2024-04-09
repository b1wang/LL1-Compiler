# Author: Brandon Wang
#
# Dot visualizer for SMPL compiler using PyDot library

import pydot
from blocks import BlockTree, BlockNode
from op_codes import OP

class Visualizer:
    
    def __init__(self, blocks: BlockTree):
        self.graph = pydot.Dot('G', graph_type='digraph')
        self.blocks = blocks
        self.map = {}           # Dict object to map { block idx : block num }

    # Output the BlockTree into a Dot graph
    #   First add all the nodes using a Stack LIFO traversal
    #   Then, traverse down the tree to add edges
    def Construct(self):
        stack = []
        seen_join = []
        seen_while_join = []
        curr_block = None
        num = 0
        stack.append(self.blocks.root)
        # Construct the nodes first 
        print("Visualizer: Construct nodes")
        while (len(stack) > 0):
            curr_block = stack.pop(0)
            name = "BB" + str(num)
            self.map[curr_block.idx] = num
            new_node = pydot.Node(name, label=self.ConvertToRecord(curr_block, num), shape="record")
            self.graph.add_node(new_node)
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
        # Traverse down the graph to add edges
        self.AddEdges()
        print("\n")

    def AddEdges(self):
        stack = []
        seen_join = []
        seen_while_join = []
        curr_block = None
        num = 0
        stack.append(self.blocks.root)
        # Construct the nodes first 
        print("Visualizer: Construct edges")
        while (len(stack) > 0):
            curr_block = stack.pop(0)
            for children in curr_block.children:
                if children:
                    src_num = self.map[curr_block.idx]
                    dst_num = self.map[children.idx]
                    src_label = "BB" + str(src_num) + ":s"
                    dst_label = "BB" + str(dst_num) + ":n"
                    if children.type == BlockNode.BASIC:
                        self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label))
                    elif children.type == BlockNode.FALL:
                        self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="fall-through"))
                    elif children.type == BlockNode.BRANCH:
                        self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="branch"))
                    elif children.type == BlockNode.FOLLOW:
                        self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="follow"))
                    elif children.type == BlockNode.JOIN:
                        last_idx = len(curr_block.instructions)-1
                        instruction = self.blocks.FindInstruction(curr_block.instructions[last_idx])
                        if (instruction):
                            if (instruction.op == OP.BRA):
                                self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="branch"))
                            else:
                                self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="fall-through"))
                    elif children.type == BlockNode.WHILE_JOIN:
                        if (curr_block.idx > children.idx):
                            self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label, label="fall-through"))
                        else:
                            self.graph.add_edge(pydot.Edge(src=src_label, dst=dst_label))

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


    # Convert to a "record" format
    def ConvertToRecord(self, block: BlockNode, num) -> str:
        record = "<b>BB" + str(num) + "| {"
        counter = 0
        for instruction in block.instructions:
            if instruction:
                if (counter == 0):
                    record = record + " " + self.blocks.FindInstruction(instruction).toString() + " "
                    counter += 1
                else:
                    record = record + "| " + self.blocks.FindInstruction(instruction).toString() + " "
        record += "}"
        record += "}"
        return record

    def Output(self) -> str:
        # return self.graph.create_dot()        # GraphViz not working
        return self.graph.to_string()
