# Slippi Ranked Stats

A local desktop analytics dashboard for your Slippi ranked matches. Track your rating over time, see matchup win rates, review session history, and more — all from your own replay files without uploading anything.

![Slippi Ranked Stats Crest](Slippi%20Ranked%20Stats%20Crest.png)

---

## Features

- **Rating Progression** — chart your ranked rating over time with per-snapshot history and rolling win rate
- **Winrate by Matchup** — see your win % against every character you've played (min. 3 games)
- **Win % by Stage** — know which stages favour you
- **Session History** — every play session with sets played, game record, and win rate
- **Opponent History** — full set-by-set breakdown against every opponent you've faced
- **Clutch Stats** — comeback rate (sets won after going down 0-1) and deciding game win %
- **Live Watcher** — automatically captures a rating snapshot after each ranked set while the app is open
- **Incremental Scanning** — only new replay files are processed on each scan; 10,000+ file libraries scan instantly after the first pass

---

## Requirements

- Windows 10 or 11
- Your Slippi replays folder (default: `Documents\Slippi\`)

---

## Installation

1. Download and extract the `SlippiRankedStats` folder anywhere (Desktop or Documents recommended)
2. Double-click **`SlippiRankedStats.exe`**
   - Windows SmartScreen may warn you the first time — click **More info → Run anyway**
   - Windows Firewall may ask to allow network access — click **Allow** (the app only connects to `slippi.gg` and your local machine)

Your stats are saved locally to `Documents\Slippi Ranked Stats\` and persist between sessions.

---

## How to use

1. Enter your **connect code** in the sidebar (e.g. `JOEY#870`)
2. Click **Scan Replays** and point it at your Slippi replays folder
3. Click **Fetch Rating Snapshot** to pull your current rating from the Slippi API
4. Leave the app open while playing ranked — the live watcher auto-captures snapshots after each set

**Subsequent sessions:** just open the app and click Scan Replays to pick up any new files. Already-scanned files are skipped automatically.

---

## Privacy

- Replay files are read locally — they never leave your computer
- The only outbound connection is to `slippi.gg`'s own API to fetch your rating (same as the website)
- No account, login, or telemetry

---

## Closing the app

Close the app window to exit.

---

## Support

Enjoying the app? [Support on Patreon](https://www.patreon.com/joeydonuts)

Issues and feedback: [GitHub Issues link]
