# HuggingFace Benchmark Pipeline — Run Instructions

This guide walks you through regenerating `grade_baselines.json` and
`src/lib/grade-benchmarks.ts` after pulling the latest `main` branch.

---

## Prerequisites

- Python 3.10+
- Git (already pulled `main`)

---

## One-Time Setup

```bash
cd /path/to/Slippi-Ranked-Stats

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install peppi-py numpy huggingface_hub
```

---

## Step 1 — Run the Parser

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate

python scripts/parse_hf_replays.py
```

**What it does:**
- Lists all ~42 k Falco replays from the HuggingFace dataset
- Downloads in batches of 500, parses with peppi-py, accumulates stat percentiles
- Saves progress to `scripts/parse_hf_checkpoint.json` after every batch
- Deletes each batch from disk immediately after parsing (conserves space)
- Writes final output to `scripts/grade_baselines.json`

**Expected runtime:** 45–120 minutes depending on network speed.

**Progress output (one line per batch):**
```
Batch 12: downloading 500 files...
  Progress: 5500/42318 total (13.0%)
  Downloaded 500 files in 38.2s
  Parsed 487 games (13 errors) in 4.1s
  Total: 5500/42318 (13.0%) in 512s
```

**If it crashes or is interrupted:** just re-run the exact same command.
The checkpoint file resumes automatically from where it stopped.

---

## Step 2 — Regenerate TypeScript Benchmarks

```bash
python scripts/regen_benchmarks.py
```

This reads `scripts/grade_baselines.json` and writes
`src/lib/grade-benchmarks.ts` with all 18 stat percentile thresholds.

Sample output:
```
Source: huggingface/erickfm/slippi-public-dataset-v3.7/FALCO · 42318 replays
Overall sample_size: 84636
Included 24 chars (>= 50 samples) + _overall:
  Falco                n=84636
  ...
Wrote src/lib/grade-benchmarks.ts
```

---

## Step 3 — Commit and Push

```bash
git add scripts/grade_baselines.json src/lib/grade-benchmarks.ts
git commit -m "Regenerate benchmarks: 18 stats, expanded stat set"
git push
```

---

## Optional: Multi-Character Run

To add Fox, Marth, etc. on top of Falco (uses `--merge` to keep existing data):

```bash
python scripts/parse_hf_replays.py --character FOX   --merge
python scripts/parse_hf_replays.py --character MARTH --merge
python scripts/regen_benchmarks.py
```

Each character run has its own checkpoint. Delete
`scripts/parse_hf_checkpoint.json` between characters if you want a fresh run.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'peppi_py'`**
```bash
pip install --upgrade peppi-py
```

**New stats (stage_control, edgeguard, recovery) all come back `null`:**
Position field names vary by peppi-py version. Run this to check:
```python
import peppi_py as peppi
game = peppi.read_slippi('path/to/any.slp')
port = game.frames.ports[0].leader.post
print(dir(port))          # look for: position, position_x, position_y
pos = port.position
print(type(pos), dir(pos))  # look for: x, y  (or use .field('x') for PyArrow)
```
Then open a GitHub issue with the output and the peppi-py version (`pip show peppi-py`).

**Start from scratch (ignore checkpoint):**
```bash
rm scripts/parse_hf_checkpoint.json
python scripts/parse_hf_replays.py
```

**Check peppi-py version:**
```bash
pip show peppi-py
```
