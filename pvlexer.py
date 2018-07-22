import re
from pvtoken import PvToken

# Token definitions
TOKEN_NONE = 0
TOKEN_WHITESPACE = 1
TOKEN_COMMENT = 2
# patterns
TOKEN_INTEGER = 10
TOKEN_REAL = 11
TOKEN_STRING = 12
TOKEN_PVNAME = 13
TOKEN_ARRAY = 14
# reserved words
TOKEN_TYPE = 20
TOKEN_UNIT = 21
TOKEN_GROUP = 22
TOKEN_SLEEP = 23
# symbols
TOKEN_SEMICOLON = 30
TOKEN_COMMA = 31
TOKEN_EQUALS = 32
TOKEN_TIMES = 33
TOKEN_DIVIDED = 34
TOKEN_PERCENT = 35
# parenthesis
TOKEN_LEFT_BRACE = 40
TOKEN_RIGHT_BRACE = 41
TOKEN_LEFT_BRACKET = 42
TOKEN_RIGHT_BRACKET = 43


class PvLexer:

    # Lexer regular expressions. The order matters!
    # In general, regular expressions are ordered with the most complex ones first.
    lexer_patterns = [
        (r'[\s]+', TOKEN_WHITESPACE),
        (r'-?0[xX][\da-fA-F]+', TOKEN_INTEGER),
        (r'[-+]?(\d+([.,]\d*)?|[.,]\d+)([eE][-+]?\d+)?', TOKEN_REAL),
        (r'-?\d+', TOKEN_INTEGER),
        (r'".+"', TOKEN_STRING),
        (r'string|int|short|float|enum|char|long|double', TOKEN_TYPE),
        (r'arcsec|deg', TOKEN_UNIT),
        (r'microns|um', TOKEN_UNIT),
        (r'millimeters|millimetres|mm', TOKEN_UNIT),
        (r'meters|metres|m', TOKEN_UNIT),
        (r'group', TOKEN_GROUP),
        (r'sleep', TOKEN_SLEEP),
        (r'[\w:\(\)\$]+(.[\w]+)?', TOKEN_PVNAME),
        (r'#', TOKEN_COMMENT),
        (r';', TOKEN_SEMICOLON),
        (r'=', TOKEN_EQUALS),
        (r',', TOKEN_COMMA),
        (r'\*', TOKEN_TIMES),
        (r'/', TOKEN_DIVIDED),
        (r'%', TOKEN_PERCENT),
        (r'{', TOKEN_LEFT_BRACE),
        (r'}', TOKEN_RIGHT_BRACE),
        (r'\[', TOKEN_LEFT_BRACKET),
        (r'\]', TOKEN_RIGHT_BRACKET),
    ]

    def __init__(self):
        """
        Initialize a lex object.
        Compile all the lexer regular expressions for speed.
        """
        self.line_number = 0
        self.compiled_patterns = []
        for pattern, token_id in self.lexer_patterns:
            self.compiled_patterns.append((re.compile(pattern), token_id))

    def _get_token_list(self, line):
        """
        Split a line into tokens. This is where most of the lexical analysing
        is done. White spaces and comments are stripped down in this routine.
        :param line:
        :type line: str
        :return: list of Tokens
        :rtype: list
        """
        m = None
        line_pos = 0
        line_length = len(line)
        token_list = []
        # print line_length

        # Traverse the line starting from the first character
        while line_pos < line_length:
            t_id = TOKEN_NONE

            # Loop over all the possible patterns looking for a match.
            # Break the loop if one is found and proceed to the next step.
            # White spaces are ignored at this point.
            for t_pat, t_id in self.compiled_patterns:
                # print str(line_pos) + ': [' + str(line[line_pos:]) + ']'
                m = t_pat.match(line, line_pos)
                if m:
                    # print '+ [' + m.group() + '] ' + str(t_id)
                    if t_id != TOKEN_WHITESPACE:  # ignore white spaces
                        token_list.append(PvToken(t_id, m.group(0)))
                    break

            # Check whether a match is found and move the character counter
            # to the next non-processed character in the line.
            # Comments are stripped at this point by breaking the loop.
            if m:
                if t_id != TOKEN_COMMENT:
                    line_pos += len(m.group())
                else:
                    break  # skip the rest of the line after a comment
            else:
                print 'error'
                break

        return token_list

    def get_line_number(self):
        """
        Return the current line number.
        Useful when reporting error messages.
        :return: line number
        :rtype: int
        """
        return self.line_number

    def next_token(self, f_in):
        """
        Return next token in the file.
        This is the main routine that will be called by the parser.
        :param f_in: input file
        :type f_in: file
        :return: list
        :rtype: list
        """
        for line in f_in:

            line = line.strip()
            self.line_number += 1

            # Ignore comment and blank lines
            if re.search(r'^#', line) or len(line) == 0:
                # print 'ignored', line
                continue

            for token in self._get_token_list(line):
                yield token


if __name__ == '__main__':
    lex = PvLexer()

    with open('example.pv') as f:
        for t in lex.next_token(f):
            print t
