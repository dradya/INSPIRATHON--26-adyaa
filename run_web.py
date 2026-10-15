"""Launch Aegis Web Application in default web browser."""
import os
import sys
from pathlib import Path

# Add aegis directory to python path
root = Path(__file__).resolve().parent
aegis_dir = root / "aegis"
sys.path.insert(0, str(aegis_dir))
os.chdir(str(aegis_dir))

import app

if __name__ == "__main__":
    sys.exit(app.main())
