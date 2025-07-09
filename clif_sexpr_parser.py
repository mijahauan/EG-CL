import re

class SexprParser:
    """A simple S-expression parser for CLIF strings."""
    def parse(self, clif_string):
        """Parses a string into a nested list."""
        tokens = self._tokenize(clif_string)
        return self._build_from_tokens(tokens)

    def _tokenize(self, s):
        """Splits the string into tokens."""
        s = s.replace('(', ' ( ').replace(')', ' ) ')
        return s.split()

    def _build_from_tokens(self, tokens):
        """Recursively builds the nested list from a stream of tokens."""
        if not tokens:
            raise ValueError("Unexpected EOF while reading")
        token = tokens.pop(0)
        if token == '(':
            L = []
            while tokens and tokens[0] != ')':
                L.append(self._build_from_tokens(tokens))
            if not tokens:
                raise ValueError("Unclosed parenthesis")
            tokens.pop(0)
            return L
        elif token == ')':
            raise ValueError("Unexpected ')'")
        else:
            return token