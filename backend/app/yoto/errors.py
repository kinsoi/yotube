class YotoError(Exception):
    """A Yoto API call failed."""


class AuthRequired(YotoError):
    """There is no valid Yoto session; the user must log in again."""


class ContentNotFound(YotoError):
    """The Yoto playlist (card content) no longer exists."""


class LoginError(YotoError):
    """The OAuth login could not be completed."""
