# import sys
# import argparse

from pvtoken import PvToken
from pvlexer import PvLexer

from pvlexer import TOKEN_NONE, TOKEN_EOF
from pvlexer import TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_STRING, TOKEN_PVNAME
from pvlexer import TOKEN_TYPE, TOKEN_UNIT, TOKEN_GROUP, TOKEN_SLEEP
from pvlexer import TOKEN_SEMICOLON, TOKEN_COMMA
from pvlexer import TOKEN_EQUALS, TOKEN_TIMES, TOKEN_DIVIDED, TOKEN_PERCENT
from pvlexer import TOKEN_LEFT_BRACE, TOKEN_RIGHT_BRACE, TOKEN_LEFT_BRACKET, TOKEN_RIGHT_BRACKET
from pvlexer import TOKEN_ERROR

# Pvload defines a total of eight possible types for EPICS channels,
# but they can be grouped into three different categories.
TYPE_NONE = 0
TYPE_INTEGER = 1
TYPE_FLOAT = 2
TYPE_STRING = 3


def map_type(token):
    """
    Map the token pvload data type string (stored in it's value) into
    one of the possible data types. This routine is used to check
    for compatible types in single value statements.
    :param token:
    :type token: PvToken
    :return: token data type
    :rtype: int
    """
    token_value = token.get_value()
    if token_value in ['string', 'char', 'enum']:
        return TYPE_STRING
    elif token_value in ['short', 'int', 'long']:
        return TYPE_INTEGER
    elif token_value in ['float', 'double']:
        return TYPE_FLOAT
    else:
        return TYPE_NONE


class SingleValue:
    def __init__(self):
        self.data_type = TYPE_NONE
        self.name = ''
        self.count = 0
        self.value_list = []
        self.index_list = []
        self.type_map = {TYPE_NONE: 'none', TYPE_INTEGER: 'int', TYPE_FLOAT: 'float', TYPE_STRING : 'string'}

    def __str__(self):
        return '------> ' + self.type_map[self.data_type] + ' [' + str(self.name) + '] ' + \
               str(self.count) + ' ' + str(self.index_list) + ' ' + str(self.value_list)

    def set_name(self, token):
        self.name = token.get_value()

    def append_value(self, token):
        self.value_list.append(token.get_value())
        pass

    def set_count(self, token):
        self.count = int(token.get_value())

    def set_type(self, token):
        self.data_type = map_type(token)

    def check(self):
        print self
        pass


class PvParser:
    class PvSyntaxError(Exception):
        def __init___(self, message):
            Exception.__init__(self, message)

    def __init__(self):
        self.f_in = None
        self.file_name = ''
        self.lex = PvLexer()
        self.token = None  # should not be used in the parser routines
        self.single = None  # used in semantic analysis
        self.flush_token()  # clears self.token

    def pv_error(self, text=''):
        """
        :param text: error message
        :type text: str
        :raises: PvSyntaxError
        """
        # format_string = 'Syntax error at {0}\nIn file {1} at line {2}:\n>> {3}\n'
        if text:
            format_string = 'Syntax error at {0}, {1}\nIn file {2} at line {3}:\n>> {4}\n'
        else:
            format_string = 'Syntax error at {0}{1}\nIn file {2} at line {3}:\n>> {4}\n'
        line_number, line_text = self.lex.get_last_line()
        token_value = self.token.get_value()
        message = format_string.format(token_value, text, self.file_name, line_number, line_text)
        raise self.PvSyntaxError(message)

    def pv_warning(self, text=''):
        """
        :param text: error message
        :type text: str
        """
        return

    def trace(self, text):
        print '> ' + text, self.token

    def get_token(self):
        """
        This routine is a front end to the lexer next_token() function.
        It simulates a push back functionality when the token is not consumed.
        Lexer errors (i.e. unknown tokens) are trapped at this point.
        :return: next token
        :rtype: PvToken
        """
        if self.token.match(TOKEN_NONE):
            self.token = self.lex.next_token(self.f_in)
            # trap lexer errors
            if self.token.match(TOKEN_ERROR):
                self.pv_error()
        self.trace('+')
        return self.token

    def flush_token(self):
        self.trace('flush_token')
        self.token = PvToken(TOKEN_NONE, 'none')

    def flush_and_get_token(self):
        """
        Convenient shortcut
        :return: next token
        :rtype: PvToken
        """
        self.trace('flush_and_get_token')
        self.flush_token()
        return self.get_token()

    # --------------------------------------------------------
    # The recursive parser routines start here
    # --------------------------------------------------------

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
            | /* empty */
            ;
        ---
        :param input_file_name: input file name
        :type input_file_name: str
        :return: file found?
        :rtype: bool
        """
        self.trace('pv_file')
        try:
            self.f_in = open(input_file_name, 'r')
            self.file_name = input_file_name
        except IOError:
            return False

        try:
            while self.pv_item():
                pass
        except self.PvSyntaxError as e:
            print e

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
        :rtype: bool
        """
        self.trace('pv_item')
        if self.pv_group():
            return True
        elif self.pv_sleep():
            return True
        elif self.pv_single():
            return True
        elif self.get_token().match(TOKEN_EOF):
            return False  # end of items
        else:
            self.pv_error()

    # --------------------------------------------------------
    # - Group
    # --------------------------------------------------------

    def pv_group(self):
        """
        A group is a grouped list of single items
        ---
        group: group_head TOKEN_LEFT_BRACE group_body TOKEN_RIGHT_BRACE group_tail
            ;
        ---
        :return:
        :rtype: bool
        """
        self.trace('pv_group')
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
        self.trace('pv_group_head')
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
        self.trace('pv_group_body')
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
        self.trace('pv_group_tail')
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
        self.trace('pv_sleep')
        if self.get_token().match(TOKEN_SLEEP):
            token = self.flush_and_get_token()
            if token.match(TOKEN_INTEGER) or token.match(TOKEN_FLOAT):
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
        A single item is a C like declaration and assignment
        ---
        single
            : single_head single_equals single_body TOKEN_SEMICOLON
        ---
        :return:
        """
        self.trace('pv_single')
        self.single = SingleValue()
        print self.single
        if self.pv_single_head():
            if self.pv_single_equals():
                if self.pv_single_body():
                    if self.get_token().match(TOKEN_SEMICOLON):
                        self.single.check()
                        self.flush_token()
                        return True
                    else:
                        self.pv_error()
        return False

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
        self.trace('pv_single_head')
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
        :return: always true; percent is optional
        :rtype: bool
        """
        self.trace('pv_single_start')
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
        :return: always true; type optional
        :rtype: bool
        """
        self.trace('pv_single_type')
        token = self.get_token()
        if token.match(TOKEN_TYPE):
            assert isinstance(self.single, SingleValue)
            self.single.set_type(token)
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
        self.trace('pv_single_name')
        token = self.get_token()
        if token.match(TOKEN_PVNAME):
            assert isinstance(self.single, SingleValue)
            self.single.set_name(token)
            self.flush_token()
            return True
        else:
            return False

    # def pv_single_count(self):
    #     """
    #     The single statement count is used to handle arrays
    #     ---
    #     single_count
    #         : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
    #         | /* empty */
    #         ;
    #     ---
    #     :return: true if count detected, false otherwise
    #     :raises: PvSyntaxError
    #     """
    #     self.trace('pv_single_count')
    #     return self.pv_single_index_or_count()

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
        self.trace('pv_single_count')
        assert isinstance(self.single, SingleValue)
        count = self.pv_single_index_or_count()
        self.single.set_count(PvToken(TOKEN_INTEGER, str(count)))
        return True

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
        self.trace('pv_single_equals')
        if self.get_token().match(TOKEN_EQUALS):
            self.flush_token()
            return True
        else:
            self.pv_error('\'=\' expected')

    # --------------------------------------------------------
    # - Single body
    # --------------------------------------------------------

    def pv_single_body(self):
        """
        The single body specifies the value to be assigned
        The implementation here deviates from the original BNF in that it does not
        allow a list of values if it's not enclosed in braces.
        Note: single_bodyn in the original BNF was renamed as single_value_list
        ---
        single_body
            : single_individual_value
            | single_value_list  <- NOT ALLOWED IN THIS IMPLEMENTATION!!
            | TOKEN_LEFT_BRACE single_body_value_list TOKEN_RIGHT_BRACE
            ;
        ---
        :return:
        """
        self.trace('pv_single_body')
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
        self.trace('pv_single_value_list')
        self.pv_single_individual_value()
        while True:
            if self.get_token().match(TOKEN_COMMA):
                self.flush_token()
                if not self.pv_single_individual_value():
                    break
        return True

    # --------------------------------------------------------
    # - Single individual value
    # --------------------------------------------------------

    def pv_single_individual_value(self):
        """

        ---
        single_individual_value
            : single_index single_value single_scale
            ;
        ---
        :return: true if individual value is found, exception otherwise
        :rtype: bool
        :raises: PvSyntaxError
        """
        self.trace('pv_single_individual_value')
        return self.pv_single_index() and self.pv_single_value() and self.pv_single_scale()

    def pv_single_index(self):
        """
        ---
        single_index
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: always true; index optional
        :raises: PvSyntaxError
        """
        self.trace('pv_single_index')
        # TODO
        # return self.pv_single_index_or_count()
        return True

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
        self.trace('pv_single_value')
        token = self.get_token()
        if token.is_in([TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_STRING]):
            assert isinstance(self.single, SingleValue)
            self.single.append_value(token)
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
        :return: always true; scale optional
        :rtype: bool
        :raises: PvSyntaxError
        """
        self.trace('pv_single_scale')
        if self.get_token().match(TOKEN_TIMES):
            token = self.flush_and_get_token()
            if token in [TOKEN_INTEGER, TOKEN_FLOAT]:
                self.flush_token()
            else:
                self.pv_error()
        elif self.get_token().match(TOKEN_DIVIDED):
            token = self.flush_and_get_token()
            if token in [TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_UNIT]:
                self.flush_token()
            else:
                self.pv_error()
        else:
            token = self.get_token()
            if token in [TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_UNIT]:
                self.flush_token()
        return True

    # def pv_single_index_or_count(self):
    #     """
    #     An item is either a group, a single item or a sleep declaration
    #     ---
    #     single_index_or_count
    #         : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
    #         | /* empty */
    #         ;
    #     ---
    #     :return: always true; index or count optional
    #     :raises: PvSyntaxError
    #     """
    #     self.trace('pv_single_index_or_count')
    #     if self.get_token().match(TOKEN_LEFT_BRACKET):
    #         token = self.flush_and_get_token()
    #         if token.match(TOKEN_INTEGER):
    #             assert isinstance(self.single, SingleValue)
    #             self.single.set_count(token)
    #             if self.flush_and_get_token().match(TOKEN_RIGHT_BRACKET):
    #                 self.flush_token()
    #                 return True  # index found
    #             else:
    #                 self.pv_error()
    #         else:
    #             self.pv_error()
    #     return True  # index not found, ok anyway

    def pv_single_index_or_count(self):
        """
        An item is either a group, a single item or a sleep declaration
        ---
        single_index_or_count
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: always true; index or count optional
        :raises: PvSyntaxError
        """
        value = 0
        self.trace('pv_single_index_or_count')
        if self.get_token().match(TOKEN_LEFT_BRACKET):
            token = self.flush_and_get_token()
            if token.match(TOKEN_INTEGER):
                value = token.get_value()
                if self.flush_and_get_token().match(TOKEN_RIGHT_BRACKET):
                    self.flush_token()
                else:
                    self.pv_error()
            else:
                self.pv_error()
        return value


if __name__ == '__main__':

    file_list = ['example2.pv']

    parser = PvParser()

    for file_name in file_list:
        parser.pv_file(file_name)
