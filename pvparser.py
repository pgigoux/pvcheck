import sys
import argparse
import pvlexer as pvl
from pvtoken import PvToken


class PvParser:

    def __init__(self):
        self.lex = pvl.PvLexer()
        pass

    def match(self, token):
        """

        :param token: token
        :type token: PvToken
        :return:
        """

    def parse(self, f_in):
        for token in self.lex.next_token(f_in):
            print token

    def pv_file(self):
        # pv_file()
        # pv_item()
        pass


if __name__ == '__main__':

    file_list = ['example.pv']

    parser = PvParser()

    for file_name in file_list:

        try:
            f = open(file_name, 'r')
        except IOError:
            print 'File not found'
            continue

        parser.parse(f)
        f.close()
