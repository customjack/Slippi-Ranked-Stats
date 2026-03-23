# Slippi Ranked Stats — Changelog

## 2026-03-21 — Incomplete set detection (v1.2.2)

### Feature
Added logic to detect and exclude sets where an opponent disconnected mid-set (LRAS) from all stats analysis.

### Changes (`src/lib/store.ts`)
- Added `hasLras: boolean` field to `SetResult` interface — `true` if any game in the set ended via disconnect/quit (`lras_win` or `lras_loss`)
- Added `cleanSets` derived store — filters out all LRAS-tainted sets from `sets`
- `headerStats` now derives from `cleanSets` instead of `sets` (win rate, streaks, rating delta all exclude incomplete sets)
- `sessions` now derives from `cleanSets` instead of `sets` (session grouping and per-session stats exclude incomplete sets)

### Why
When an opponent disconnects before a set is finished, Slippi records it as a win but the result is misleading. Excluding these from analysis gives a cleaner picture of actual performance.

---

## 2026-03-21 — Auto-updater fixed (v1.2.0)

### Problem
Existing installations never received update banners despite multiple release attempts. `latest.json` was never uploaded to GitHub releases, so the in-app updater had nothing to check against.

### Root cause
The GitHub Actions workflow was silently skipping signing. Tauri v2's CLI receives `TAURI_SIGNING_PRIVATE_KEY` as an environment variable but does not print any output when it ignores it — meaning no `.sig` file was generated and `tauri-action` skipped `latest.json` with the message "Signature not found for the updater JSON."

### What was tried (and failed)
- Fixing CRLF → LF line endings on `srs.key` — didn't help
- Regenerating keypair with a password — failed due to known Tauri v2 bug (#13485): password via env var is silently broken
- Regenerating keypair without a password — still no signing output from `tauri build`
- Using `TAURI_SIGNING_PRIVATE_KEY_PATH` (file path instead of content) — wrong approach; the file needs decoded content, not the base64 string

### What actually fixed it (confirmed working as of v1.2.1)
`tauri-action` was the root problem — it runs its own internal `tauri build`, producing a *different* binary than the one we signed. This meant the signature never matched the downloaded file. The fix was to **ditch `tauri-action` entirely** and handle the full pipeline manually:

1. Build once with `npm run tauri build`
2. Sign that exact binary with `tauri signer sign` in a **bash** step (not PowerShell — PowerShell drops empty string arguments, breaking the `--password ""` flag)
3. Generate `latest.json` manually in PowerShell using `ConvertTo-Json`
4. Create the GitHub release and upload both the `.exe` and `latest.json` using the `gh` CLI

### Additional issues fixed along the way
- `gh release create` creates an untagged release if a release for that tag already exists — fixed by adding `gh release delete $tag --yes 2>$null` before creating
- GitHub replaces spaces in filenames with dots in download URLs — `[Uri]::EscapeDataString()` was producing `%20` instead of `.`, causing 404. Fixed with `$exeName -replace ' ', '.'`

### Final workflow structure (`.github/workflows/release.yml`)
1. Checkout, setup Node, install Rust, cache Rust artifacts, npm install
2. **Build Tauri app** — `npm run tauri build` (no signing env vars needed here)
3. **Sign installer** (bash) — `tauri signer sign --private-key "$TAURI_SIGNING_PRIVATE_KEY" --password "" <exe>`, outputs `EXE_PATH` and `SIG_PATH` to `$GITHUB_ENV`
4. **Generate latest.json and create release** (pwsh) — reads the `.sig` file, builds the JSON with the correct dot-encoded URL, deletes any existing release, then creates the release and uploads the `.exe` and `latest.json` via `gh release create`

---

### Important notes
- `srs.key` is the private signing key. It lives at `slippi-dashboard-v2/srs.key` and is in `.gitignore` — never commit it
- The public key is embedded in `src-tauri/tauri.conf.json` under `plugins.updater.pubkey`
- `TAURI_SIGNING_PRIVATE_KEY` GitHub secret must contain the exact contents of `srs.key` (a single base64 line)
- No password on the key — `TAURI_SIGNING_PRIVATE_KEY_PASSWORD: ''` in the workflow
- Users on v1.1.8 cannot auto-update to v1.2.0 because the signing key was regenerated during debugging. They must manually reinstall once. From v1.2.0 onwards, auto-updates work correctly.

### Version files to update on every release
All three must match before pushing a tag:
- `src-tauri/tauri.conf.json` → `"version": "x.x.x"`
- `src-tauri/Cargo.toml` → `version = "x.x.x"`
- `package.json` → `"version": "x.x.x"`
