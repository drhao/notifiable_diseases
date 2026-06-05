"""
build_api.py - Publish a small, static, versioned JSON API to GitHub Pages.

This is NOT a dynamic backend: it just emits plain JSON files that are served as
static assets from the Pages CDN. That keeps it abuse-resilient (no compute to
overload; the CDN caches and answers conditional requests cheaply).

Layout written under ./api :

    api/v1/diseases.json   full case-definition records (presentation-only and
                           local-only fields stripped)
    api/v1/manuals.json    full disease-manual records (same cleaning)
    api/v1/summary.json    compact index — name/english/category/date only;
                           the recommended endpoint for "just list everything"
    api/v1/meta.json       counts, generation time, license and source notes

build_api_payloads() is pure (no IO) so it can be unit-tested.
"""
import os
import json
import logging
from datetime import datetime, timezone

from cdc_common import setup_logging

logger = logging.getLogger(__name__)

API_DIR = os.path.join("api", "v1")

# Fields dropped from the public API: presentation diffs and local-only paths.
_DROP_EXACT = {"pdf_path"}

LICENSE_NOTE = "Code: MIT. Data: Taiwan CDC (衛生福利部疾病管制署) public information."
SOURCE_NOTE = "https://www.cdc.gov.tw"


def _clean(record):
    """Strip presentation (*_diff) and local-only fields from a record."""
    return {
        k: v for k, v in record.items()
        if k not in _DROP_EXACT and not k.endswith("_diff")
    }


def _summary_row(record):
    return {
        "name": record.get("name"),
        "english_name": record.get("english_name"),
        "category": record.get("source_category") or record.get("category"),
        "last_pdf_update": record.get("last_pdf_update"),
    }


def build_api_payloads(cases, manuals, now=None):
    """Return {relative_path: json-serialisable object} for every API file."""
    cases = cases or []
    manuals = manuals or []
    generated = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")

    clean_cases = [_clean(r) for r in cases]
    clean_manuals = [_clean(r) for r in manuals]

    meta = {
        "generated": generated,
        "counts": {"case_definitions": len(clean_cases), "manuals": len(clean_manuals)},
        "license": LICENSE_NOTE,
        "source": SOURCE_NOTE,
        "endpoints": {
            "case_definitions": "diseases.json",
            "manuals": "manuals.json",
            "summary": "summary.json",
        },
    }

    summary = {
        "generated": generated,
        "case_definitions": [_summary_row(r) for r in clean_cases],
        "manuals": [_summary_row(r) for r in clean_manuals],
    }

    return {
        "diseases.json": clean_cases,
        "manuals.json": clean_manuals,
        "summary.json": summary,
        "meta.json": meta,
    }


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    setup_logging()
    cases = _load("diseases.json")
    manuals = _load("disease_manuals.json")
    payloads = build_api_payloads(cases, manuals)

    os.makedirs(API_DIR, exist_ok=True)
    for filename, obj in payloads.items():
        with open(os.path.join(API_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))

    logger.info("Wrote API to %s/ (%d case definitions, %d manuals).",
                API_DIR, len(cases), len(manuals))


if __name__ == "__main__":
    main()
