# Author: Brandon Wang

# ---Token Values---
# 0               # ErrorToken
# '*': 1,         # timesToken
# '/': 2,         # divToken
# '+': 11,        # plusToken
# '-': 12,        # minusToken
# '==': 20,       # eqlToken
# '!=': 21,       # neqToken
# '<': 22,        # lssToken
# '>=': 23,       # geqToken
# '<=': 24,       # leqToken
# '>': 25,        # gtrToken
# '.': 30,        # periodToken
# ',': 31,        # commaToken
# '[': 32,        # openbracketToken
# ']': 34,        # closebracketToken
# ')': 35,        # closeparenToken
# '<-': 40,       # becomesToken
# 'then': 41,     # thenToken
# 'do': 42,       # doToken
# '(': 50,        # openparenToken
# '0...9': 60,    # numbers...
# 'a...z": 61,    # identifiers...
# ';': 70,        # semiToken
# '}': 80,        # endToken
# 'od': 81,       # odToken
# 'fi': 82,       # fiToken
# 'else': 90,     # elseToken
# 'let': 100,     # letToken   
# 'call': 101,    # callToken
# 'if': 102,      # ifToken
# 'while': 103,   # whileToken
# 'return': 104,  # returnToken
# 'var': 110,     # varToken
# 'array': 111,   # arrToken
# 'void': 112,    # voidToken
# 'function': 113, # funcToken
# 'procedure': 114, # procToken
# '{': 150,       # beginToken
# 'computation': 200, # mainToken
# 'end of file': 255 # eofToken
# 
# FileReader.Error =0
# FileReader.EOF = 255

from filereader import FileReader

# Tokenizer class to tokenize input from FileReader 
class Tokenizer:
    
    TOKEN_ERROR = 0
    TOKEN_TIMES = 1
    TOKEN_DIV = 2
    TOKEN_PLUS = 11
    TOKEN_MINUS = 12
    TOKEN_EQ = 20
    TOKEN_NEQ = 21
    TOKEN_LESS = 22
    TOKEN_GEQ = 23
    TOKEN_LEQ = 24
    TOKEN_GTR = 25
    TOKEN_PERIOD = 30
    TOKEN_COMMA = 31
    TOKEN_OPENBRACKET = 32
    TOKEN_CLOSEBRACKET = 34
    TOKEN_CLOSEPAREN = 35
    TOKEN_BECOMES = 40
    TOKEN_THEN = 41
    TOKEN_DO = 42
    TOKEN_OPENPAREN = 50
    TOKEN_SEMI = 70
    TOKEN_END = 80
    TOKEN_OD = 81
    TOKEN_FI = 82
    TOKEN_ELSE = 90
    TOKEN_LET = 100
    TOKEN_CALL = 101
    TOKEN_IF = 102
    TOKEN_WHILE = 103
    TOKEN_RETURN = 104
    TOKEN_VAR = 110
    TOKEN_ARR = 111
    TOKEN_VOID = 112
    TOKEN_FUNC = 113
    TOKEN_PROC = 114
    TOKEN_BEGIN = 150
    TOKEN_MAIN = 200
    TOKEN_EOF = 255
    TOKEN_NUM = 60   # numberToken
    TOKEN_ID = 61    # idToken

    TOKEN_INPUTNUM = 256
    TOKEN_OUTPUTNUM = 257
    TOKEN_OUTPUTNL = 258

    tokens = [None] * 1000
    tokens[TOKEN_ERROR] = "error"
    tokens[TOKEN_TIMES] = "*"
    tokens[TOKEN_DIV] = "/"
    tokens[TOKEN_PLUS] = "+"
    tokens[TOKEN_MINUS] = "-"
    tokens[TOKEN_EQ] = "=="
    tokens[TOKEN_NEQ] = "!="
    tokens[TOKEN_LESS] = "<"
    tokens[TOKEN_GEQ] = ">="
    tokens[TOKEN_LEQ] = "<="
    tokens[TOKEN_GTR] = ">"
    tokens[TOKEN_PERIOD] = "."
    tokens[TOKEN_COMMA] = "," 
    tokens[TOKEN_OPENBRACKET] = "["
    tokens[TOKEN_CLOSEBRACKET] = "]"
    tokens[TOKEN_CLOSEPAREN] = ")"
    tokens[TOKEN_BECOMES] = "<-"
    tokens[TOKEN_THEN] = "then"
    tokens[TOKEN_DO] = "do"
    tokens[TOKEN_OPENPAREN] = "("
    tokens[TOKEN_SEMI] = ";"
    tokens[TOKEN_END] = "}"
    tokens[TOKEN_OD] = "od"
    tokens[TOKEN_FI] = "fi"
    tokens[TOKEN_ELSE] = "else"
    tokens[TOKEN_LET] = "let"
    tokens[TOKEN_CALL] = "call"
    tokens[TOKEN_IF] = "if"
    tokens[TOKEN_WHILE] = "while"
    tokens[TOKEN_RETURN] = "return"
    tokens[TOKEN_VAR] = "var"
    tokens[TOKEN_ARR] = "array"
    tokens[TOKEN_VOID] = "void"
    tokens[TOKEN_FUNC] = "function"
    tokens[TOKEN_PROC] = "procedure"
    tokens[TOKEN_BEGIN] = "{"
    tokens[TOKEN_MAIN] = "main"
    tokens[TOKEN_EOF] = "end of file"
    tokens[TOKEN_INPUTNUM] = "InputNum"        # InputNum()
    tokens[TOKEN_OUTPUTNUM] = "OutputNum"      # OutputNum(x)
    tokens[TOKEN_OUTPUTNL] = "OutputNewLine"   # OutputNewLine()

   

    def __init__(self, filename):
        self.file_reader = FileReader(filename)     # File reader internal object
        self.error = 0                              # Internal error state
        self.inputSym = ''                          # Current character on the input 
        self.val = 0                                # last number encountered 
        self.id = 0                                 # last identifier encountered
        self.id_last_index = 259                    # unused index to add new identifiers 
        self.next()                                 # Cache front-most char on init

    def next(self) -> str:
        self.inputSym = self.file_reader.next()

    def GetNext(self) -> int:
        while (self.inputSym == '' or self.inputSym == ' ' or self.inputSym == '\n' or self.inputSym == '\t'):
            self.next()
        if self.inputSym == FileReader.EOF:                 # if input symbol is EOF, return eof
            return Tokenizer.TOKEN_EOF
        if self.error == 1:                                 # if Tokenizer.Error() has been called, return error token
            return Tokenizer.TOKEN_ERROR
        elif self.inputSym.isnumeric():                     # if input symbol is a number, get the full number, update number variable, and return numberToken
            self.number()
            return Tokenizer.TOKEN_NUM
        elif self.inputSym.isalpha():                       # If input symbol is a letter, check for identifier or if its a reserved keyword, update to id var, and return idToken
            id_str = self.identifier()
            token_id = self.String2Id(id_str)
            if token_id == -1:                              # Token is not found...
                self.tokens[self.id_last_index] = id_str
                self.id = self.id_last_index
                self.id_last_index += 1
                return Tokenizer.TOKEN_ID                   
            else:
                self.id = token_id
                return Tokenizer.TOKEN_ID                 
        else:                                               # If not a number or letter, check if its a symbol
            if (self.inputSym == "="):
                self.next()
                if (self.inputSym == "="):
                    self.next()
                    return self.TOKEN_EQ
            elif (self.inputSym == "!"):
                self.next()
                if (self.inputSym == "="):
                    self.next()
                    return self.TOKEN_NEQ
            elif (self.inputSym == "<"):
                self.next()
                if (self.inputSym == "="):
                    self.next()
                    return self.TOKEN_LEQ
                elif (self.inputSym == "-"):
                    self.next()
                    return self.TOKEN_BECOMES
                else:
                    return self.TOKEN_LESS
            elif (self.inputSym == ">"):
                self.next()
                if (self.inputSym == "="):
                    self.next()
                    return self.TOKEN_GEQ
                else:
                    return self.TOKEN_GTR
            else:
                token_id = self.String2Id(self.inputSym)
                if token_id == -1:                            # Throw syntax error if also not a symbol
                    self.Error("Syntax Error")
                    return Tokenizer.TOKEN_ERROR
                else:
                    self.next()
                    return token_id
            

            self.next()
            if (self.inputSym != ' ' and self.inputSym != '\n' and not self.inputSym.isalpha() and not self.inputSym.isnumeric()):
                sym += self.inputSym
                print(sym)
                self.next()
            token_id = self.String2Id(sym)
            if token_id == -1:                            # Throw syntax error if also not a symbol
                self.Error("Syntax Error: ")
                return Tokenizer.TOKEN_ERROR
            else:
                return token_id

    def number(self):
        self.val = int(self.inputSym)
        self.next()
        while (self.inputSym.isnumeric()):
            if (int(self.inputSym) <= 9 and int(self.inputSym) >= 0):
                self.val = (10 * self.val) + int(self.inputSym)
                self.next()
            else:
                break
        
    def identifier(self) -> str:
        id_str = self.inputSym
        while(True):
            self.next()
            if (self.inputSym.isalpha() or self.inputSym.isnumeric()):
                id_str = id_str + self.inputSym
            else:
                return id_str
            
    def Id2String(self, id) -> str:
        if (id == Tokenizer.TOKEN_ID):
            return self.tokens[self.id]
        return self.tokens[id]

    def String2Id(self, name) -> int:
        # print("String2Id")
        for i, token in enumerate(self.tokens):
            if token == name:
                return i
        return -1
    
    # Insert a variable name into the list of tokens
    def InsertVar(self, var) -> None:
        self.tokens[self.id_last_index] = var
        self.id_last_index += 1


    def Error(self, errorMsg) -> None:
        self.file_reader.Error(errorMsg)
        self.error = 1