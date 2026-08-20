#!/usr/bin/env python3
"""Shim de compatibilidad: delega en linkcheck.wrapper.main."""
import sys

from linkcheck.wrapper import main

if __name__ == "__main__":
    sys.exit(main())
