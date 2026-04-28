# Future Feature Log

Ideas noted for later. Move entries into a **Shipped** section when they land, with a link to the relevant doc or commit.

---

## Ideas

### Mac distribution
**Noted:** 2026-04-28 · Source: Joey

Long-term: ship a macOS build alongside the existing Windows installer so Slippi players on Mac can use the app. Currently the release workflow only produces an `.nsis` Windows installer.

**What this requires:**
- Extend `.github/workflows/release.yml` with a macOS job (`runs-on: macos-latest`) that produces a signed `.app` / `.dmg`
- Set `bundle.targets` per-platform (currently hardcoded to `"nsis"`)
- Apple Developer signing + notarization (otherwise Gatekeeper blocks the install). Likely needs an Apple Developer account ($99/yr) and certs stored as GitHub secrets
- `latest.json` updater manifest needs a `darwin-x86_64` / `darwin-aarch64` entry alongside `windows-x86_64`
- Verify the watcher / replay scanning code doesn't have Windows-only path assumptions (Tauri's path APIs should handle this, but worth a real test)

**Decision deferred:** until Mac dev environment is set up and any genuine Mac-only bugs are surfaced, no point in building the distribution pipeline.

---

## Shipped

### Multi-connect-code profiles
**Noted:** 2026-04-19 · **Shipped:** 2026-04-24 (v1.4.0)

Link any number of connect codes in the sidebar; stats, sessions, matchups, and grade history all union across linked codes. No "primary" designation in the UI — codes are equal. Rating history still tracks only the top code in the list (informational note shown when linked codes are active).

See commits `1219acf` (initial multi-code wiring), `e75cd7e` (v1.4.0 UI + grading multi-code support), and `77e19c3` (v1.4.1 count inflation fix).

### Richer session history
**Noted:** 2026-04-19 · **Shipped:** 2026-04-24 (v1.4.0)

Old "Last Session" tab replaced with **Ranked Sessions** — split-panel browser. Session list on the left; clicking any session renders the full breakdown on the right via a new reusable `SessionView.svelte` component (the same view Recent Session used to render inline). `RecentSession.svelte` is now a thin wrapper around `SessionView`.

See commits `1219acf` (SessionView + drill-in), `e75cd7e` (Ranked Sessions tab).

### Post-Set Letter Grade
**Noted:** 2026-04-14 · **Shipped:** 2026-04-17

Became the full Set Grading System — 18 stats, 15 scored across 3 categories (Neutral, Punish, Defense) plus 3 execution stats shown as info-only, graded against community baselines from 177,538 HuggingFace replays. Visible in the Grading tab (free/premium split) and as a post-set card in the Live Session tab (premium-only).

See [`docs/grading_methodology.md`](docs/grading_methodology.md) for how grading works and [`docs/dev_notes.md`](docs/dev_notes.md) for implementation state.
