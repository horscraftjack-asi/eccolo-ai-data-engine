"""Put the repo root on sys.path so tests can `from core import build_workbook`.

The engine is a package (`core/`), imported the same way app.py imports it, so tests
exercise exactly the code path the web app and CLI use.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
