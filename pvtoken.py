

class PvToken:

    def __init__(self, token_id, token_value):
        """
        :param token_id:
        :type token_id: int
        :param token_value: token value
        :type token_value: str
        """
        self.id = token_id
        self.value = token_value

    def __str__(self):
        return 'Token(' + str(self.id) + ',' + str(self.value) + ')'

    def __eq__(self, token):
        """
        Check whether two tokens are of the same type (id)
        :param token: token
        :type token: PvToken
        :return:
        """
        if self.id == token.id:
            return True
        else:
            return False


if __name__ == '__main__':
    t1 = PvToken(1, "23")
    t2 = PvToken(2, "abc")
    t3 = PvToken(1, "hello")
    print t1 == t2
    print t1 == t3

