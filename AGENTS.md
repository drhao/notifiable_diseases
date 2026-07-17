# AGENTS.md — Operating guide for AI agents working on this repo

> **Audience: you, an AI coding agent** (Claude, GPT/Codex, Gemini, …), not a human onboarding.
> This file is the durable contract for how to change this project safely. Read it fully before
> your first edit. When you learn something the next agent will need, **update this file** — it is
> the memory that survives between sessions and between models.
>
> `CLAUDE.md` just `@import`s this file, so Claude Code loads it automatically. Keep the knowledge
> here, not scattered, so every tool/model reads the same thing.

---

## 1. What this project is (in one breath)

A **fully static, serverless** pipeline that scrapes Taiwan CDC (衛生福利部疾病管制署) **notifiable
disease case definitions (病例定義)** and **control manuals (防治工作手冊)** from PDFs, extracts them
into structured JSON, and publishes three read surfaces to **GitHub Pages**:

- two search dashboards (`index.html`, `manuals.html`),
- an RSS feed (`feed.xml`),
- a versioned JSON API (`api/v1/…`).

There is **no backend, no database, no build server of our own**. Everything runs in a daily GitHub
Actions job and is served as static files from the Pages CDN. Keep it that way unless the user
explicitly decides otherwise — "static on a CDN" is what makes this cheap, abuse-resilient, and
near-zero-maintenance.

---

## 2. Golden rules (violating these breaks production or trust)

1. **Never commit generated artifacts.** `index.html`, `manuals.html`, `feed.xml`, `api/`, the
   CSV exports, and the `pdfs/` / `manual_pdfs/` caches are all in `.gitignore` and rebuilt every
   run. Committing them re-bloats history (the whole reason `main` was history-slimmed once — see
   §7). Only structured data (`diseases.json`, `disease_manuals.json`), `metadata.json`,
   `status_report.md`, and source/docs are version-controlled.
2. **The XSS defense is a two-part invariant — keep both halves in lockstep.** PDF text is
   untrusted and rendered via `innerHTML`. Safety depends on TWO pieces agreeing:
   - `scraper.diff_texts()` emits diff markup using *exactly* these four tag strings and
     HTML-escapes everything else;
   - `dashboard_common.SECURITY_JS`'s `renderDiff()` allow-lists *exactly those same four strings*
     and escapes the rest.
   If you change a diff tag's markup/style in `diff_texts`, you MUST change `DIFF_RE`/`DIFF_TAGS`
   in `SECURITY_JS` identically, or you either break rendering or open an XSS hole. There is no
   test that cross-checks these two across the Python/JS boundary — treat it as a manual invariant.
3. **All data embedded into a page goes through `dashboard_common.embed_json()`**, never raw
   `json.dumps`. It `\u`-escapes `< > &` and U+2028/U+2029 so nothing in PDF-derived data can break
   out of the `<script>`. All user-facing URLs go through `esc(safeUrl(...))` (blocks `javascript:`).
4. **The coverage gate is a safety fuse — don't defang it.** `check_coverage.py` runs in CI
   *before* the commit step and exits non-zero if parsing collapsed (well-parsed rate `<
   COVERAGE_MIN_RATE`, or record count shrank `> COVERAGE_MAX_SHRINK` vs the last commit). That is
   what stops a CDC layout change from committing/publishing empty data. If you add fields or
   change parsing, re-check the thresholds instead of removing the gate.
5. **Use `logging`, never `print()`** in library/pipeline code. `cdc_common.setup_logging()` is
   called by each entry point; modules do `logger = logging.getLogger(__name__)` and use `%`-style
   lazy args (`logger.info("x=%s", x)`), not f-strings. (Exception: GitHub Actions `::error::`
   workflow-command lines in `check_coverage.py` are protocol output, intentionally `print`.)
6. **No new heavy dependencies without a real reason.** `pandas` was deliberately removed in favor
   of stdlib `csv` (`cdc_common.write_csv`); `Jinja2` was deliberately *not* adopted (see §7).
   Runtime deps are just `requests`, `beautifulsoup4`, `lxml`, `pdfplumber`.
7. **Parsers must stay pure + offline-testable.** Text-processing functions take a string and
   return data with no network/PDF/file IO, so they can be unit-tested without the CDC site (which
   blocks sandboxes anyway — see §6). Keep new parsing logic in this shape and add fixtures/tests.

---

## 3. Architecture & data flow

```
                    CDC website (PDFs)                     ← network only in CI (sandbox gets 403)
                          │
        pdf_fetcher.py    │  fetch_disease_links() → get_actual_pdf_url() → download_and_extract_pdf()
        cdc_common.py     │  shared Session (retry/backoff, UA), download_pdf() = download+sha256+extract
                          ▼
   ┌───────────────────── scraper.py (main daily entry, case definitions) ─────────────────────┐
   │  for each disease: hash-cache check → parse_disease_content() → diff vs previous            │
   │  writes: diseases.json, diseases.csv(gitignored), metadata.json, status_report.md           │
   └───────────────────────────────────────────────────────────────────────────────────────────┘
        data_parser.py    │  parse_disease_content(), parse_case_definitions(), normalize_text(),
                          │  deduplicate_chars(), extract_english_name(), clean_section_text()
                          ▼
   manual_scraper.py  → disease_manuals.json   (same shape, control manuals; parse_manual_text())
                          ▼
   build_dashboard.py → index.html      build_manuals_dashboard.py → manuals.html
   build_feed.py      → feed.xml        build_api.py → api/v1/{summary,diseases,manuals,meta}.json
        dashboard_common.py │  SECURITY_JS (esc/safeUrl/renderDiff) + embed_json() — shared, single source
                          ▼
   check_coverage.py  → gate (exit 1 if parsing collapsed)  → commit data → deploy _site/ to Pages
```

Two GitHub Actions workflows:
- `.github/workflows/tests.yml` — runs `pytest` on every push/PR.
- `.github/workflows/daily-scraper.yml` — cron 10:00 UTC: pytest gate → scrape → build → coverage
  gate → commit data to `main` → publish `_site/` to Pages. Opens a `ci-failure` issue on failure.

**The hash cache (important mental model):** each record stores `pdf_hash`. If the freshly
downloaded PDF's sha256 matches, extraction/parsing is skipped and the *previous* record is reused
verbatim. Consequence below in §6.

---

## 4. File map

| File | Role | Pure/testable? |
|---|---|---|
| `cdc_common.py` | shared HTTP session, `download_pdf`, `write_csv`, `setup_logging` | mixed |
| `pdf_fetcher.py` | discover disease links + resolve/download PDFs (case defs) | network |
| `scraper.py` | **daily entry** for case definitions; `diff_texts()`; status report | orchestration |
| `data_parser.py` | all case-definition text parsing + `clean_section_text` | **pure** |
| `manual_scraper.py` | **daily entry** for manuals; listing pagination; `parse_manual_text` | mixed |
| `dashboard_common.py` | `SECURITY_JS` + `embed_json` (shared by both dashboards) | pure |
| `build_dashboard.py` / `build_manuals_dashboard.py` | render the two dashboards | pure-ish |
| `build_feed.py` | RSS 2.0 feed | pure core (`build_feed`) |
| `build_api.py` | static JSON API | pure core (`build_api_payloads`) |
| `check_coverage.py` | CI coverage gate | pure core (`dataset_stats`,`evaluate`) |
| `tests/` | 85 offline tests; `conftest.py` puts repo root on `sys.path` | — |

---

## 5. Conventions (do this)

- **New CSV output** → `cdc_common.write_csv(path, records, columns=…)` (utf-8-sig BOM for Excel).
- **New page/data embedding** → `embed_json()` + `esc`/`safeUrl` for anything from PDF data.
- **New parsing** → add a pure function in `data_parser.py`, then fixtures + tests. Prefer
  whole-line matching for noise removal so you never partially mangle legitimate content (that is
  how `clean_section_text` avoids eating a legit mid-sentence "疾病管制署").
- **New pipeline step** → wire it into `daily-scraper.yml` in the right place relative to the
  coverage gate (data-producing steps before it; publishing after).
- **Commits**: small, one concern each, imperative subject explaining the *why*. Do not commit
  generated artifacts.
- **Tests**: everything must pass offline (`pytest -q`). No test may require the network.

---

## 6. Gotchas (hard-won — you *will* hit these)

- **The CDC site returns 403 to sandbox/CI-less environments.** You cannot fetch `cdc.gov.tw` from
  a dev sandbox to verify scraping/HTML structure. Design parsers to be testable from saved
  fixtures; verify live behavior only in CI.
- **The hash cache means parser changes do NOT retroactively apply.** If you improve a parser,
  existing records whose PDF is unchanged keep their *old* parse until the PDF changes. To apply a
  parser fix to already-stored data you must run a one-time migration over the JSON (pure string
  work, no re-download) — this is exactly how the footer/`【密件】` cleanup was rolled out. Budget
  for a migration whenever you change parsing output.
- **`re.sub` interprets backslashes in the replacement string.** Building JS `\uXXXX` escapes via
  `re.sub` silently halved the backslashes and produced no-op escapes. Use `str.replace` or a
  backslash constant (`bs = "\\"`) for escape-generation, and *test the actual output bytes*.
- **Never type raw U+2028/U+2029 into source.** They are invisible and one got mistaken for a
  space, nearly turning "replace line separators" into "replace all spaces". Use `chr(0x2028)`.
- **Flexbox + wide tables:** a wide table inside a `display:flex` column overflows the whole page
  unless the flex item has `min-width: 0`. That single rule (plus `body{overflow-x:hidden}`) is
  what fixed mobile "爆版".
- **`diseases.json` is overwritten with only successfully-processed records each run** (see §8,
  known issue): a disease that fails download is dropped from the file for that run.

---

## 7. Decision log (why things are the way they are — don't relitigate without cause)

- **Static on GitHub Pages, not a real API server.** No compute to overload; the CDN caches and
  serves conditional requests cheaply. Worst realistic abuse case is the Pages ~100 GB/mo *soft*
  bandwidth limit → a polite email, not a bill or an outage. This is why "won't the API get
  flooded?" is a non-issue here.
- **Did NOT adopt Jinja2 for the dashboards.** Their CSS is only ~49% shared (genuinely different
  layouts), so templating wouldn't remove the real duplication and would add a dependency + a risky
  rewrite of large inline-JS blocks. Instead we extracted the one thing that *must* be shared —
  the security JS — into `dashboard_common.SECURITY_JS`.
- **Removed `pandas`.** It was used only for three small CSV writes; stdlib `csv` does it with no
  heavy dependency and faster installs.
- **`main` was history-slimmed once and force-pushed** to drop ~70 MB of committed PDFs/HTML from
  history. Generated artifacts are gitignored to prevent re-bloat. (The closed PR that referenced
  the old objects may keep them on GitHub's server, but fresh clones are small.)
- **Branch/merge workflow in use:** develop on a `claude/*` feature branch, then **fast-forward
  `main`** to it (`git push origin <sha>:main`). No PR review gate.
- **Data stays in git (decided 2026-06).** `diseases.json` + `disease_manuals.json` are committed
  every daily run. Chosen over publish-only because the per-day git diff is exactly what a future
  version-history page (C2) will read, and ~1.5 MB is years away from being a problem. Revisit if
  `main` history grows unwieldy: periodic squash, or move the largest file to a Pages/Release
  artifact.
- **Fast-forward to `main`, no PR gate (decided 2026-06).** AI work lands via
  `git push origin <sha>:main` once CI is green; acceptable because it's a solo project and the
  pytest + coverage gates are the real guard. Revisit (switch to PR + required checks) when a
  second human/AI contributor joins.

---

## 8. Known issues & backlog (verified, with reasoning)

**Recently fixed — do not reintroduce (see git log, 2026-06):**
- **English name now populated in the daily path.** `scraper.main` and `data_parser.main` share one
  parse path, `data_parser.build_record(content)` (sections + case defs + `english_name`). Existing
  records were backfilled offline from their stored `content` (72/73 have a name; the one without
  simply has no parenthetical English in its PDF). It *was* a dead feature (0/73).
- **Transient failure no longer drops a disease.** `scraper._keep_previous()` re-appends the
  last-known-good record when `get_actual_pdf_url`/download fails, so a CDN hiccup can't silently
  shrink `diseases.json`.
- **Single parse path.** The old drift between `scraper.main` and `data_parser.main` (the root
  cause of the english_name bug, plus a redundant `parse_case_definitions`) is gone.
- **`diseases_raw.json` removed** (was orphaned: 283 entries, tracked, referenced by no code).

**Parser quality (deferred, higher risk — see git history "Strip PDF footer/form noise"):**
1. Table-structured content (e.g. 採檢時程表) is mangled by column-wise PDF text extraction; would
   need `pdfplumber.extract_tables()` for those specific sections.
2. Chinese sentences are hard-wrapped mid-sentence (`\n` inside a sentence); could be re-joined
   conservatively (only lines not ending in punctuation / list markers) with tests.

**Features not yet built:**
- **C2 版本歷史頁** — a per-disease change timeline. Now unblocked: data stays in git (see §7), so
  the per-day diff history is available to build it from.
- **C5 i18n** — an English UI toggle (english_name is now populated, so this is more useful).

---

## 9. Open questions for the human (raise, don't silently assume)

No open questions right now. The two that used to live here — data-in-git vs bloat, and
no-review fast-forward to `main` — were decided in 2026-06 and moved to the §7 decision log
(each with a "revisit when …" trigger). When you hit a judgment call whose answer changes
architecture, add it here and ask the human before building on top of it.

---

## 10. How to work here

```bash
pip install -r requirements-dev.txt     # requests, bs4, lxml, pdfplumber, pytest
python -m pytest -q                      # all offline; must stay green (currently 85 passing)

# Rebuild the published artifacts locally from committed JSON (no network needed):
python build_dashboard.py && python build_manuals_dashboard.py
python build_feed.py && python build_api.py
python check_coverage.py                 # exercise the gate locally

# Scrapers hit the live CDC site — only work where network is allowed (NOT the sandbox: 403):
python scraper.py                        # case definitions
python manual_scraper.py                 # manuals
LOG_LEVEL=DEBUG python scraper.py        # verbose logging
```

Keep this file honest and current. The next agent — maybe a different model — inherits only what
is written down here.
