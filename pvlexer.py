import re
from pvtoken import PvToken

# Token definitions
TOKEN_NONE = 0
TOKEN_EOF = 1
TOKEN_WHITESPACE = 2
TOKEN_COMMENT = 3
# patterns
TOKEN_INTEGER = 10
TOKEN_REAL = 11
TOKEN_STRING = 12
TOKEN_PVNAME = 13
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
# used to flag unknown tokens
TOKEN_ERROR = -1


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
        self.last_line = ''
        self.line_number = 0
        self.token_list = []
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
        # print '_get_token_list'
        m = None
        line_pos = 0
        line_length = len(line)
        token_list = []
        # print line_length

        # Traverse the line starting from the first character
        while line_pos < line_length:

            # Assign a default value so the IDE doesn't complain
            t_id = TOKEN_NONE

            # Loop over all the possible patterns looking for a match.
            # Break the loop if one is found and proceed to the next step.
            # Comments and whitespaces are ignored at this point.
            for t_pat, t_id in self.compiled_patterns:
                # print str(line_pos) + ': [' + str(line[line_pos:]) + ']'
                m = t_pat.match(line, line_pos)
                if m:
                    # print '+ [' + m.group() + '] ' + str(t_id)
                    if t_id != TOKEN_WHITESPACE and t_id != TOKEN_COMMENT:
                        token_list.append(PvToken(t_id, m.group(0)))
                    break

            # If a match was found then move the character counter
            # to the next non-processed character in the line.
            # The rest of the comment line is stripped at this point.
            if m:
                if t_id != TOKEN_COMMENT:
                    line_pos += len(m.group())
                else:
                    break  # skip the rest of the line after a comment
            else:
                token_list.append(PvToken(TOKEN_ERROR, m.group()))
                break

        # print '-', token_list
        return token_list

    # def get_line_number(self):
    #     """
    #     Return the current line number.
    #     Useful when reporting error messages.
    #     :return: line number
    #     :rtype: int
    #     """
    #     return self.line_number

    def get_last_line(self):
        return self.line_number, self.last_line

    # def next_token(self, f_in):
    #     """
    #     Return next token in the file.
    #     This is the main routine that will be called by the parser.
    #     :param f_in: input file
    #     :type f_in: file
    #     :return: next token
    #     :rtype:
    #     """
    #     for line in f_in:
    #
    #         line = line.strip()
    #         self.line_number += 1
    #
    #         # Ignore comment and blank lines
    #         if re.search(r'^#', line) or len(line) == 0:
    #             continue
    #
    #         self.last_line = line
    #
    #         for token in self._get_token_list(line):
    #             yield token

    def next_token(self, f_in):
        """
        Return next token in the file.
        This is the main routine that will be called by the parser.
        It was not implemented as an iterator because of the parser requirements.
        :param f_in: input file
        :type f_in: file
        :return: next token
        :rtype: PvToken
        """
        if len(self.token_list) == 0:
            # print 'empty'
            try:
                # Look for the next non comment and non white line in the line
                while True:
                    line = f_in.next().strip()
                    if re.search(r'^#', line) is None and len(line) > 0:
                        break

                self.token_list = self._get_token_list(line)
                self.last_line = line
                self.line_number += 1

            except StopIteration:
                self.token_list = [PvToken(TOKEN_EOF, '')]

        return self.token_list.pop(0)


if __name__ == '__main__':

    lex = PvLexer()

    with open('example1.pv') as f:
        while True:
            t = lex.next_token(f)
            print t
            if t.id == TOKEN_EOF:
                break
