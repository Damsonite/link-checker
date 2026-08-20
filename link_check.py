#!/usr/bin/env python3
"""Shim de compatibilidad: delega en linkcheck.cli.main."""
import sys

from linkcheck.cli import main

if __name__ == "__main__":
    sys.exit(main())
