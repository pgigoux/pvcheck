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
        :raises: PvSyntaxError
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

    def flush_and_get_token(self):
        """
        Convenient shortcut
        :return: next token
        :rtype: PvToken
        """
        self.flush_token()
        return self.get_token()
    
    # --------------------------------------------------------
    # The recursive parser routines start here
    # --------------------------------------------------------
    # - File
    # --------------------------------------------------------

    def pv_file(self, input_file_name):
        """
        A file is a list of items
        ---
        file
            : file item
            | item
            |/* empty */
            ;
        ---
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

        try:
            while self.pv_item():
                pass
        except self.PvSyntaxError:
            pass

        self.f_in.close()
        self.f_in = None
        self.file_name = ''

        return True

    # --------------------------------------------------------
    # - Item
    # --------------------------------------------------------

    def pv_item(self):        
        """
        An item is either a group, a single item or a sleep declaration
        ---
        item
            : group
            | single
            | sleep
            ;
        ---
        :return:
        """
        # TODO handle end of tokens
        if self.pv_group():
            pass
        elif self.pv_sleep():
            pass
        else:
            self.pv_single()

    # --------------------------------------------------------
    # - Group
    # --------------------------------------------------------

    def pv_group(self):
        """
        # TODO braces, etc
        A group is a grouped list of single items
        ---
        group: group_head TOKEN_LEFT_BRACE group_body TOKEN_RIGHT_BRACE group_tail
            ;
        ---
        :return:
        :rtype: bool
        """
        if self.pv_group_head():
            if self.get_token().match(TOKEN_LEFT_BRACE):
                self.flush_token()
                self.pv_group_body()
                self.pv_group_tail()
                if self.get_token().match(TOKEN_RIGHT_BRACE):
                    self.flush_token()
                    return True
                else:
                    self.pv_error()
        else:
            return False

    def pv_group_head(self):
        """
        The group head starts with the token TOKEN_GROUP.
        If no head is found, then no group is present.
        ---
        group_head
            :	TOKEN_GROUP
            ;
        ---
        :return: true if start of group found, false otherwise
        """
        if self.get_token().match(TOKEN_GROUP):
            self.flush_token()
            return True
        else:
            return False

    def pv_group_body(self):
        """
        TODO: not sure about this
        The group body is a list on single statements
        ---
        group_body
        : group_body single
        | single
        | /* empty */
        ;
        ---
        :return:
        """
        while self.pv_single():
            pass
        return True

    def pv_group_tail(self):
        """
        The group tail is an optional TOKEN_SEMICOLON
        ---
        group_tail
            :	TOKEN_SEMICOLON
            |	/* empty */
            ;
        ---
        :return:
        """
        if self.get_token().match(TOKEN_SEMICOLON):
            self.flush_token()

    # --------------------------------------------------------
    # - Sleep
    # --------------------------------------------------------

    def pv_sleep(self):
        """
        A sleep statement starts with the token TOKEN_SLEEP.
        If it's not there, then no sleep statement is present.
        ---
        sleep
            : TOKEN_SLEEP TOKEN_SEMICOLON
            | TOKEN_SLEEP TOKEN_INTEGER TOKEN_SEMICOLON
            | TOKEN_SLEEP TOKEN_DOUBLE TOKEN_SEMICOLON
            ;
        ---
        :return: true if a sleep statement was found, false otherwise
        :rtype: bool
        :raises: PvSyntaxError
        """
        if self.get_token().match(TOKEN_SLEEP):
            token = self.flush_and_get_token()
            if token.match(TOKEN_INTEGER) or token.match(TOKEN_REAL):
                if not self.flush_and_get_token().match(TOKEN_SEMICOLON):
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
        """
        # TODO
        A single item is a C like declaration and assignment
        ---
        single
            : single_head single_equals single_body TOKEN_SEMICOLON
        ---
        :return:
        """
        pass

    # --------------------------------------------------------
    # - Single head
    # --------------------------------------------------------

    def pv_single_head(self):
        """
        TODO
        The single statement head contains all the elements before the equal sign
        ---
        single_head
            :	single_start single_type single_name single_count
            ;
        ---
        :return: true if valid head
        :rtype: bool
        :raises: PvSyntaxError
        """
        return self.pv_single_start() and self.pv_single_type() and self.pv_single_name() and self.pv_single_count()

    def pv_single_start(self):
        """
        The single statement start is the optional TOKEN_PERCENT
        ---
        single_start
            : /* empty */
            | TOKEN_PERCENT
            ;
        ---
        :return: always true
        :rtype: bool
        """
        if self.get_token().match(TOKEN_PERCENT):
            self.flush_token()
        return True

    def pv_single_type(self):
        """
        The single type is any of the optional type declarations.
        ---
        single_type
            :	TOKEN_TYPE
            |	/* empty */
            ;
        ---
        :return: always true
        :rtype: bool
        """
        if self.get_token().match(TOKEN_TYPE):
            self.flush_token()
        return True

    def pv_single_name(self):
        """
        The single state name must be a valid pv name
        ---
        single_name
            :	tokenPVNAME
            ;
        ---
        :return: true if name detected
        :raises: PvSyntaxError
        """
        if self.get_token().match(TOKEN_PVNAME):
            return True
        else:
            self.pv_error()

    def pv_single_count(self):
        """
        The single statement count is used to handle arrays
        ---
        single_count
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: true if count detected, false otherwise
        :raises: PvSyntaxError
        """
        return self.pv_single_index_or_count()

    # --------------------------------------------------------
    # - Single equals
    # --------------------------------------------------------

    def pv_single_equals(self):
        """
        The single statement equals must contain the token TOKEN_EQUALS
        ---
        single_equals
            : TOKEN_EQUALS
        ---
        :return: true if equals detected
        :raises: PvSyntaxError
        """
        if self.get_token().match(TOKEN_EQUALS):
            return True
        else:
            self.pv_error()

    # --------------------------------------------------------
    # - Single body
    # --------------------------------------------------------

    def pv_single_body(self):
        """
        TODO
        The single body specifies the value to be assigned
        The implementation here deviates from the original BNF in that it does not
        allow a list of values if it's not enclosed in braces.
        Note: single_bodyn in the original BNF was renamed as single_body_value_list
        ---
        single_body
            : single_individual_value
            | single_body_value_list  <- NOT ALLOWED IN THIS IMPLEMENTATION!!
            | TOKEN_LEFT_BRACE single_body_value_list TOKEN_RIGHT_BRACE
            ;
        ---
        :return:
        """
        if self.get_token().match(TOKEN_LEFT_BRACE):
            self.flush_token()
            self.pv_single_value_list()
            if self.get_token().match(TOKEN_RIGHT_BRACE):
                self.flush_token()
                return True
            else:
                self.pv_error()
        else:
            return self.pv_single_individual_value()

    def pv_single_value_list(self):
        """
        TODO: Not sure about this
        Note: single_bodyn was renamed single_value_list in this implementation
        ---
        single_value_list
            : single_individual_value
            | single_value_list TOKEN_COMMA single_individual_value
            ;
        ---
        """
        self.pv_single_individual_value()
        while True:
            if self.get_token().match(TOKEN_COMMA):
                if not self.pv_single_individual_value():
                    break
        return True

    # --------------------------------------------------------
    # - Single individual value
    # --------------------------------------------------------

    def pv_single_individual_value(self):
        """
        TODO: not sure about this

        ---
        single_individual_value
            : single_index single_value single_scale
            ;
        ---
        :return: true if individual value is found, exception otherwise
        :rtype: bool
        :raises: PvSyntaxError
        """
        return self.pv_single_index() and self.pv_single_value() and self.pv_single_scale()

    def pv_single_index(self):
        """
        ---
        single_index
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: true if index detected, false otherwise
        :raises: PvSyntaxError
        """
        return self.pv_single_index_or_count()

    def pv_single_value(self):
        """
        The single value must be either an integer, real or string.
        ---
        single_value
            :	tokenINTEGER
            |	tokenREAL
            |	tokenSTRING
            ;
        ---
        :return: true if value found, exception otherwise
        :rtype: bool
        :raises: PvSyntaxError
        """
        token = self.get_token()
        if token.is_in([TOKEN_INTEGER, TOKEN_REAL, TOKEN_STRING]):
            self.flush_token()
            return True
        else:
            self.pv_error()

    def pv_single_scale(self):
        """
        ---
        single_scale
            : TOKEN_TIMES TOKEN_INTEGER
            | TOKEN_TIMES TOKEN_REAL
            | TOKEN_DIVIDED TOKEN_INTEGER
            | TOKEN_DIVIDED TOKEN_REAL
            | TOKEN_INTEGER
            | TOKEN_REAL
            | TOKEN_DIVIDED TOKEN_ARCSECS
            | TOKEN_ARCSECS
            | TOKEN_DIVIDED TOKEN_DEGREES
            | TOKEN_DEGREES
            | TOKEN_DIVIDED TOKEN_UM
            | TOKEN_UM
            | TOKEN_DIVIDED TOKEN_MM
            | TOKEN_MM
            | TOKEN_DIVIDED TOKEN_M
            | TOKEN_M
            | /* empty */
            ;
        ---
        :return: true if scale factor found, false otherwise
        :rtype: bool
        :raises: PvSyntaxError
        """
        if self.get_token().match(TOKEN_TIMES):
            token = self.flush_and_get_token()
            if token in [TOKEN_INTEGER, TOKEN_REAL]:
                self.flush_token()
                return True
            else:
                self.pv_error()
        elif self.get_token().match(TOKEN_DIVIDED):
            token = self.flush_and_get_token()
            if token in [TOKEN_INTEGER, TOKEN_REAL, TOKEN_UNIT]:
                self.flush_token()
                return True
            else:
                self.pv_error()
        else:
            token = self.get_token()
            if token in [TOKEN_INTEGER, TOKEN_REAL, TOKEN_UNIT]:
                self.flush_token()
                return True
            else:
                return False

    def pv_single_index_or_count(self):
        """
        An item is either a group, a single item or a sleep declaration
        ---
        single_index_or_count
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: true if '[<integer>]' detected, false otherwise
        :raises: PvSyntaxError
        """
        if self.get_token().match(TOKEN_LEFT_BRACKET):
            if self.flush_and_get_token().match(TOKEN_INTEGER):
                if self.flush_and_get_token().match(TOKEN_RIGHT_BRACKET):
                    return True
                else:
                    self.pv_error()
            else:
                self.pv_error()
        return False


if __name__ == '__main__':

    file_list = ['example.pv']

    parser = PvParser()

    for file_name in file_list:
        parser.pv_file(file_name)
