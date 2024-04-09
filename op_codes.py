# File to hold constants for OP codes
# Author: Brandon Wang

class OP: 
    CONST = "const"      
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    CMP = "cmp"
    ADDA = "adda"
    LOAD = "load"
    STORE = "store"
    PHI = "phi"
    END = "end"
    BRA = "bra"
    BNE = "bne"
    BEQ = "beq"
    BLE = "ble"
    BLT = "blt"
    BGE = "bge"
    BGT = "bgt"
    READ = "read"
    WRITE = "write"
    WRITENL = "writeNL"

    DOM_CODES = [CONST, ADD, SUB, MUL, DIV, CMP, ADDA, LOAD, STORE]