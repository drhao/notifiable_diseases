"""
check_coverage.py - Guardrail against silent parsing regressions.

The CDC occasionally changes its page/PDF layout. When that happens the scrapers
keep running but produce records with empty section fields, or drop diseases
entirely — and without a check the broken data would be committed and published.

This script inspects the freshly-scraped diseases.json / disease_manuals.json and
fails (exit 1) if parsing quality has collapsed, so the CI run stops before
committing and the existing "open an issue on failure" step alerts a maintainer.

Two signals are checked per dataset:
  * well-parsed rate -- fraction of records whose key sections are populated
    (catches "records present but fields empty" layout breaks);
  * shrinkage -- record count dropping sharply vs the previously committed data
    (catches "diseases silently disappeared" breaks).

Thresholds are env-tunable: COVERAGE_MIN_RATE (default 0.6) and
COVERAGE_MAX_SHRINK (default 0.30).
"""
import os
import sys
import json
import logging
import subprocess

from cdc_common import setup_logging

logger = logging.getLogger(__name__)

# A case-definition record counts as well-parsed if it has any of the core
# textual fields or any structured case definition.
CASE_CORE = ["通報定義", "臨床條件", "疾病分類"]
CASE_STRUCT = ["suspected_case", "probable_case", "confirmed_case"]

# Manual sections; a manual counts as well-parsed with at least MANUAL_MIN of them.
MANUAL_SECTIONS = [
    "疾病概述", "致病原", "流行病學", "傳染窩", "傳染方式", "潛伏期",
    "可傳染期", "感受性及抵抗力", "病例定義", "檢體採檢送驗事項", "防疫措施",
]
MANUAL_MIN = 3


def _nonempty(v):
    return bool(v) and (not isinstance(v, str) or bool(v.strip()))


def case_ok(rec):
    return (any(_nonempty(rec.get(k)) for k in CASE_CORE)
            or any(_nonempty(rec.get(k)) for k in CASE_STRUCT))


def manual_ok(rec):
    return sum(1 for k in MANUAL_SECTIONS if _nonempty(rec.get(k))) >= MANUAL_MIN


def dataset_stats(records, ok_fn):
    total = len(records)
    ok = sum(1 for r in records if ok_fn(r))
    return {"total": total, "ok": ok, "rate": ok / total if total else 1.0}


def evaluate(name, stats, prev_count=None, min_rate=0.6, max_shrink=0.30):
    """Return a list of problem strings (empty == healthy)."""
    problems = []
    if stats["total"] == 0:
        problems.append(f"{name}: dataset is empty (0 records)")
        return problems
    if stats["rate"] < min_rate:
        problems.append(
            f"{name}: only {stats['ok']}/{stats['total']} records well-parsed "
            f"(rate {stats['rate']:.0%} < {min_rate:.0%})"
        )
    if prev_count:
        shrink = (prev_count - stats["total"]) / prev_count
        if shrink > max_shrink:
            problems.append(
                f"{name}: record count fell {shrink:.0%} "
                f"({prev_count} -> {stats['total']}, max allowed {max_shrink:.0%})"
            )
    return problems


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _prev_count(path):
    """Record count in the last committed version of path, or None if unknown."""
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            return len(json.loads(out.stdout))
    except Exception:
        pass
    return None


def _annotate(level, msg):
    # GitHub Actions workflow-command protocol (stdout), surfaced in the run UI.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{msg}")


def main():
    setup_logging()
    min_rate = float(os.environ.get("COVERAGE_MIN_RATE", "0.6"))
    max_shrink = float(os.environ.get("COVERAGE_MAX_SHRINK", "0.30"))

    cases = dataset_stats(_load("diseases.json"), case_ok)
    manuals = dataset_stats(_load("disease_manuals.json"), manual_ok)
    logger.info("Case definitions: %d records, %d well-parsed (%.0f%%)",
                cases["total"], cases["ok"], cases["rate"] * 100)
    logger.info("Disease manuals:  %d records, %d well-parsed (%.0f%%)",
                manuals["total"], manuals["ok"], manuals["rate"] * 100)

    problems = evaluate("case definitions", cases, _prev_count("diseases.json"),
                        min_rate, max_shrink)
    problems += evaluate("disease manuals", manuals, _prev_count("disease_manuals.json"),
                         min_rate, max_shrink)

    if problems:
        for p in problems:
            logger.error(p)
            _annotate("error", p)
        logger.error("Coverage check FAILED — parsing likely broke; aborting before commit.")
        sys.exit(1)

    logger.info("Coverage check passed.")


if __name__ == "__main__":
    main()
