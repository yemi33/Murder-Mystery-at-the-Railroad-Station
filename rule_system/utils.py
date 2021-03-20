def red(string):
    """Return the given string, bookended with control codes for printing in red."""
    return f"\033[91m{string}\x1b[0m"


def green(string):
    """Return the given string, bookended with control codes for printing in green."""
    return f"\033[92m{string}\x1b[0m"


def blue(string):
    """Return the given string, bookended with control codes for printing in blue."""
    return f"\033[94m{string}\x1b[0m"


def yellow(string):
    """Return the given string, bookended with control codes for printing in yellow."""
    return f"\033[93m{string}\x1b[0m"


class DotDict(dict):
    """Affords dot-notation access to dictionary attributes."""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
