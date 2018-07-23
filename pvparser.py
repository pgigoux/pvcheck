import sys
import argparse

from pvtoken import PvToken
from pvlexer import PvLexer

from pvlexer import TOKEN_NONE
from pvlexer import TOKEN_INTEGER, TOKEN_REAL, TOKEN_STRING, TOKEN_PVNAME
from pvlexer import TOKEN_TYPE, TOKEN_UNIT, TOKEN_GROUP, TOKEN_SLEEP
from pvlexer import TOKEN_SEMICOLON, TOKEN_COMMA
from pvlexer import TOKEN_EQUALS, TOKEN_TIMES, TOKEN_DIVIDED, TOKEN_PERCENT
from pvlexer import TOKEN_LEFT_BRACE, TOKEN_RIGHT_BRACE, TOKEN_LEFT_BRACKET, TOKEN_RIGHT_BRACKET
from pvlexer import TOKEN_ERROR


class PvParser:
    class PvSyntaxError(Exception):
        def __init___(self, message):
            Exception.__init__(self, message)

    def __init__(self):
        self.f_in = None
        self.file_name = ''
        self.lex = PvLexer()
        self.token = None
        self.flush_token()

    def pv_error(self):
        """
        :return:
        """
        format_string = 'Syntax error at "{1}"\nIn file {2} at line {3}:\n>> {4}\n'
        line_number, line_text = self.lex.get_last_line()
        dummy, token_value = self.token.get()
        message = format_string.format(token_value, self.file_name, line_number, line_text)
        raise self.PvSyntaxError(message)

    def get_token(self):
        """
        This routine is a front end to the lexer next_token() function.
        It simulates a pushback functionality when the token is not consumed.
        Lexer errors (unknown tokens) are trapped at this point.
        :return: next token
        :rtype: PvToken
        """
        if self.token.match(TOKEN_NONE):
            self.token = self.lex.next_token(self.f_in)
            # trap lexer errors
            if self.token.match(TOKEN_ERROR):
                self.pv_error()
        return self.token

    def flush_token(self):
        self.token = PvToken(TOKEN_NONE, 'none')

    def consume_and_get_token(self):
        """
        Convenient shortcut
        :return: next token
        :rtype: PvToken
        """
        self.flush_token()
        return self.get_token()

    # --------------------------------------------------------
    # - Group
    # --------------------------------------------------------

    def pv_group_head(self):
        if self.get_token().match(TOKEN_GROUP):
            self.flush_token()
            return True
        else:
            return False

    def pv_group_body(self):
        pass

    def pv_group_tail(self):
        if self.get_token().match(TOKEN_SEMICOLON):
            self.flush_token()

    def pv_group(self):
        if self.pv_group_head():
            self.pv_group_body()
            self.pv_group_tail()
            return True
        else:
            return False

    # --------------------------------------------------------
    # - Sleep
    # --------------------------------------------------------

    def pv_sleep(self):
        if self.get_token().match(TOKEN_SLEEP):
            token = self.consume_and_get_token()
            if token.match(TOKEN_INTEGER) or token.match(TOKEN_REAL):
                if not self.consume_and_get_token().match(TOKEN_SEMICOLON):
                    self.pv_error()
            elif token.match(TOKEN_SEMICOLON):
                self.flush_token()
            else:
                self.pv_error()
            return True
        return False

    # --------------------------------------------------------
    # - Single
    # --------------------------------------------------------

    def pv_single(self):
        pass

    # --------------------------------------------------------
    # - Item
    # --------------------------------------------------------

    def pv_item(self):
        # TODO handle end of tokens
        if self.pv_group():
            pass
        elif self.pv_sleep():
            pass
        else:
            self.pv_single()

    # --------------------------------------------------------
    # - File
    # --------------------------------------------------------

    def pv_parse(self, input_file_name):
        """

        :param input_file_name: input file name
        :type input_file_name: str
        :return: file found?
        :rtype: bool
        """
        try:
            self.f_in = open(input_file_name, 'r')
            self.file_name = input_file_name
        except IOError:
            return False

        while self.pv_item():
            pass

        self.f_in.close()
        self.f_in = None
        self.file_name = ''

        return True


if __name__ == '__main__':

    file_list = ['example.pv']

    parser = PvParser()

    for file_name in file_list:
        parser.pv_parse(file_name)
