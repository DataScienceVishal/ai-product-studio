"""Lets `python3 -I mapper/run.py` work: -I drops the current directory from sys.path, so add the product folder."""
import os
import sys


def ensure_path() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
