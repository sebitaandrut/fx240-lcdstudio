"""Frozen executable entry point; double-click opens the desktop interface."""
import sys
from fx240.cli import main

if __name__=='__main__':
    raise SystemExit(main(['gui'] if len(sys.argv)==1 else None))
