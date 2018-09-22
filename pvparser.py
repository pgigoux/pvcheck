from pvtoken import PvToken
from pvlexer import PvLexer

from pvlexer import TOKEN_NONE, TOKEN_EOF
from pvlexer import TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_STRING, TOKEN_PVNAME
from pvlexer import TOKEN_TYPE, TOKEN_UNIT, TOKEN_GROUP, TOKEN_SLEEP
from pvlexer import TOKEN_SEMICOLON, TOKEN_COMMA
from pvlexer import TOKEN_EQUALS, TOKEN_TIMES, TOKEN_DIVIDED, TOKEN_PERCENT
from pvlexer import TOKEN_LEFT_BRACE, TOKEN_RIGHT_BRACE, TOKEN_LEFT_BRACKET, TOKEN_RIGHT_BRACKET
from pvlexer import TOKEN_ERROR

# Pvload defines a total of eight possible types for EPICS channels.
# They can be grouped into three different basic types.
TYPE_NONE = 0  # not defined yet
TYPE_INTEGER = 1
TYPE_FLOAT = 2
TYPE_STRING = 3


class PvParser:
    """
    TODO
    """

    class PvSyntaxError(Exception):
        def __init___(self, message):
            Exception.__init__(self, message)

    def __init__(self):
        """
        TODO
        """
        self.f_in = None
        self.file_name = ''
        self.lex = PvLexer()
        self.token = None
        self.debug = False
        self.flush_token()  # clears self.token
        # the following variables are used for simple statement checks
        self.single_data_type = TYPE_NONE
        self.single_name = ''
        self.single_count = 0
        self.single_value_list = []
        self.single_index_list = []
        # handy way to map types to a string representation
        self.type_map = {TYPE_NONE: 'none', TYPE_INTEGER: 'int', TYPE_FLOAT: 'float', TYPE_STRING: 'string'}

    def __str__(self):
        return 'PvParser(' + \
               '[' + self.file_name + '] ' + \
               str(self.token) + ' - ' + \
               self.type_map[self.single_data_type] + ' ' + \
               '[' + str(self.single_name) + ']' + ' ' + \
               str(self.single_count) + ' ' + \
               str(self.single_index_list) + ' ' + \
               str(self.single_value_list) + \
               ')'

    def clear_single(self):
        """
        Clear/reset the variables used to store the latest single stament elements.
        :return: None
        """
        self.single_data_type = TYPE_NONE  # data type
        self.single_name = ''  # pv name
        self.single_count = 1  # array size
        self.single_value_list = []  # value list
        self.single_index_list = []  # index list

    def check_single(self):
        """
        Check for single statement consistency.
        :return: None
        """
        # Check for array consistency
        if self.single_count != len(self.single_value_list):
            self.pv_warning('list of values does not match array size')
        if len(self.single_index_list) != len(set(self.single_index_list)):
            self.pv_warning('repeated indices')
        if len(self.single_index_list) and (len(self.single_value_list) != len(self.single_index_list)):
            self.pv_warning('missing indices?')

        # Check for type consistency
        if self.single_data_type == TYPE_NONE:
            self.pv_warning('type not defined')
        elif self.single_data_type == TYPE_INTEGER:
            for value in self.single_value_list:
                try:
                    int(value)
                except ValueError:
                    self.pv_warning('type mismatch')
                    break
        elif self.single_data_type == TYPE_FLOAT:
            for value in self.single_value_list:
                try:
                    float(value)
                except ValueError:
                    self.pv_warning('type mismatch')
                    break
        elif self.single_data_type == TYPE_STRING:
            for value in self.single_value_list:
                try:
                    int(value)
                    self.pv_warning('type mismatch')
                except ValueError:
                    pass
                try:
                    float(value)
                    self.pv_warning('type mismatch')
                except ValueError:
                    pass

    @staticmethod
    def map_type(token):
        """
        Map the token pvload data type string (stored in it's value) into
        a smaller set of (compatible) data types. This routine is used to check
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

    def pv_error(self, text=''):
        """
        :param text: error message
        :type text: str
        :raises: PvSyntaxError
        """
        line_number, line_text = self.lex.get_last_line()
        token_value = self.token.get_value()
        if text:
            format_string = 'Error: at \'{0}\', file {1}, line {2} -> {3}\n>> {4}'
            message = format_string.format(token_value, self.file_name, line_number, text, line_text)
        else:
            format_string = 'Error: at \'{0}\', file {1}, line {2}\n>> {3}'
            message = format_string.format(token_value, self.file_name, line_number, line_text)
        raise self.PvSyntaxError(message)

    def pv_warning(self, text=''):
        """
        :param text: error message
        :type text: str
        """
        line_number, line_text = self.lex.get_last_line()
        if text:
            format_string = 'Warning: file {0}, line {1} -> {2}\n>> {3}'
            message = format_string.format(self.file_name, line_number, text, line_text)
        else:
            format_string = 'Warning: {0}, line {1}\n>> {2}'
            message = format_string.format(self.file_name, line_number, line_text)
        print message
        return

    def trace(self, text):
        if self.debug:
            print '> ' + text, self.token

    def set_debug(self, debug):
        self.debug = debug

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
            # trap lexer errors here
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

        while True:
            try:
                if not self.pv_item():
                    break
            except self.PvSyntaxError as e:
                print e
                self.flush_token()
                self.clear_single()
                self.lex.flush()

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
                    self.pv_error()  # TODO
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
                if self.flush_and_get_token().match(TOKEN_SEMICOLON):
                    self.flush_token()
                else:
                    self.pv_error('expected \';\'')
            elif token.match(TOKEN_SEMICOLON):
                self.pv_warning('no time specified in sleep')
                self.flush_token()
            else:
                self.pv_error('expected integer or float value')
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
        self.clear_single()
        if self.pv_single_head():
            if self.pv_single_equals():
                if self.pv_single_body():
                    if self.get_token().match(TOKEN_SEMICOLON):
                        self.check_single()
                        self.flush_token()
                        return True
                    else:
                        self.pv_error('expected \';\'')
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
            self.single_data_type = self.map_type(token)
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
            self.single_name = token.get_value()
            self.flush_token()
            return True
        else:
            return False

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
        count = self.pv_single_index_or_count()
        self.single_count = count if count is not None else 1
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
        Note: The current implementation does not allow for lists not enclosed in braces;
              the original BNF seems to allow this syntax.
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
                self.pv_error('expected \'}\'')
        else:
            return self.pv_single_individual_value()

    def pv_single_value_list(self):
        """
        Note: single_bodyn was renamed single_value_list in this implementation
        ---
        single_value_list
            : single_individual_value
            | single_value_list TOKEN_COMMA single_individual_value
            ;
        ---
        """
        self.trace('pv_single_value_list')
        while True:
            if self.pv_single_individual_value():
                if self.get_token().match(TOKEN_COMMA):
                    self.flush_token()
                else:
                    break
            else:
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
        index = self.pv_single_index_or_count()
        if index is not None:
            self.single_index_list.append(index)
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
            self.single_value_list.append(token.get_value())
            self.flush_token()
            return True
        else:
            self.pv_error('expected string, float or integer value')

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
                self.pv_error('expected integer or float value')
        elif self.get_token().match(TOKEN_DIVIDED):
            token = self.flush_and_get_token()
            if token in [TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_UNIT]:
                self.flush_token()
            else:
                self.pv_error('expected integer/float value or unit qualifier')
        else:
            token = self.get_token()
            if token in [TOKEN_INTEGER, TOKEN_FLOAT, TOKEN_UNIT]:
                self.flush_token()
        return True

    def pv_single_index_or_count(self):
        """
        An item is either a group, a single item or a sleep declaration
        ---
        single_index_or_count
            : TOKEN_LEFT_BRACKET TOKEN_INTEGER TOKEN_RIGHT_BRACKET
            | /* empty */
            ;
        ---
        :return: index or count optional, or None of not specified
        :rtype: int
        :raises: PvSyntaxError
        """
        value = None
        self.trace('pv_single_index_or_count')
        if self.get_token().match(TOKEN_LEFT_BRACKET):
            token = self.flush_and_get_token()
            if token.match(TOKEN_INTEGER):
                value = int(token.get_value())
                if self.flush_and_get_token().match(TOKEN_RIGHT_BRACKET):
                    self.flush_token()
                else:
                    self.pv_error('expected \']\'')
            else:
                self.pv_error('integer value expected')
        return value


if __name__ == '__main__':

    file_list = ['example1.pv']

    parser = PvParser()

    for file_name in file_list:
        parser.pv_file(file_name)
