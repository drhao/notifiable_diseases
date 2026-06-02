"""Pytest configuration: make the project root importable from tests/."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
