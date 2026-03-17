#!/usr/bin/env bash
# Build SlippiRankedStats.exe using PyInstaller (Streamlit version).
# Run from Git Bash inside slippi-dashboard/:
#   bash build.sh
set -e
cd "$(dirname "$0")"

echo "=== Installing build dependencies ==="
.venv/Scripts/pip install streamlit pywebview pyinstaller

echo ""
echo "=== Cleaning previous build ==="
rm -rf build/ dist/ SlippiRankedStats.spec

echo ""
echo "=== Generating app icon ==="
.venv/Scripts/python -c "
import numpy as np
from PIL import Image
img = Image.open('Slippi Ranked Stats Crest.png').convert('RGBA')
d = np.array(img)
d[(d[:,:,0]>220)&(d[:,:,1]>220)&(d[:,:,2]>220),3] = 0
Image.fromarray(d).resize((256,256)).save('crest.ico')
print('crest.ico created.')
"

echo ""
echo "=== Building SlippiRankedStats ==="

.venv/Scripts/pyinstaller \
  --name "SlippiRankedStats" \
  --onedir \
  --windowed \
  --icon "crest.ico" \
  --add-data "app.py;." \
  --add-data "api.py;." \
  --add-data "db.py;." \
  --add-data "replay_parser.py;." \
  --add-data "Slippi Ranked Stats Crest.png;." \
  --collect-all streamlit \
  --collect-all pywebview \
  --collect-all slippi \
  --hidden-import "tkinter" \
  --hidden-import "tkinter.filedialog" \
  launcher.py

echo "." > "dist/SlippiRankedStats/KEEP ALL FILES IN THIS FOLDER TOGETHER.txt"

echo ""
echo "================================================================"
echo "Build complete: dist/SlippiRankedStats/SlippiRankedStats.exe"
echo ""
echo "TEST — run the exe and check:"
echo "  - A desktop window opens (not a browser tab)"
echo "  - Enter connect code and scan replays"
echo ""
echo "Entry point: launcher.py -> app.py (Streamlit)"
echo "================================================================"
