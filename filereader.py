# Author: Brandon Wang

class FileReader:

    # EOF Special Character
    Error = 0
    EOF = 255

    def __init__(self, filename):
        self.file = open(filename, "r")
        self.error = 0
        self.pos = 0

    def next(self) -> str:
        if self.error == 1:
            return FileReader.Error
        nextchar = self.file.read(1)
        if not nextchar:
            return FileReader.EOF
        self.pos += 1
        return nextchar

    # FileReader.Error() will output an error message with the current file position and set an internal error state
    def Error(self, errorMsg) -> None:
        # Output an error message
        print(errorMsg)
        print("FileReader: Current file position = %d" % self.pos)
        self.error = 1
 
