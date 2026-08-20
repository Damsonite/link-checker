"""Códigos de color ANSI para la salida."""
import sys

from .constants import IS_WINDOWS


class Color:
    ENABLED = sys.stdout.isatty() and not IS_WINDOWS
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"

    @classmethod
    def disable(cls) -> None:
        cls.ENABLED = False
        for attr in ("RESET", "BOLD", "RED", "GREEN", "YELLOW", "BLUE"):
            setattr(cls, attr, "")

    @classmethod
    def wrap(cls, color: str, text: str) -> str:
        if not cls.ENABLED:
            return text
        return f"{color}{text}{cls.RESET}"
