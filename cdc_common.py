"""
cdc_common.py - Shared helpers for the Taiwan CDC scrapers.

Centralises the bits that were previously duplicated across pdf_fetcher.py and
manual_scraper.py: a configured requests Session (consistent User-Agent +
automatic retry/backoff) and the download -> sha256 -> pdfplumber-extract
pipeline used to cache PDFs and detect updates.
"""
import os
import re
import hashlib

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.cdc.gov.tw"

# A real-ish User-Agent: the CDC site serves empty pages to some default
# clients, so every request must send one consistently.
USER_AGENT = (
    "Mozilla/5.0 (compatible; NotifiableDiseasesBot/1.0; "
    "+https://github.com/drhao/notifiable_diseases)"
)

DEFAULT_TIMEOUT = 20

_session = None


def get_session():
    """Return a process-wide Session with retry/backoff and a default UA."""
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        retry = Retry(
            total=4,
            backoff_factor=1,  # waits 0s, 2s, 4s, 8s between attempts
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _session = s
    return _session


def fetch(url, timeout=DEFAULT_TIMEOUT):
    """GET a URL through the shared session. Raises on HTTP error."""
    res = get_session().get(url, timeout=timeout)
    res.raise_for_status()
    return res


def safe_filename(name):
    """Turn a disease name into a filesystem-safe filename stem."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def extract_pdf_text(pdf_path):
    """Extract all text from a local PDF via pdfplumber."""
    import pdfplumber  # local import: keeps the heavy PDF stack out of import time

    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def download_pdf(url, dest_dir, name, expected_hash=None, timeout=DEFAULT_TIMEOUT):
    """
    Download a PDF, save it under dest_dir/<safe_name>.pdf and return
    (text_content, local_path, sha256_hash).

    If expected_hash is given and matches the freshly downloaded bytes, the
    text extraction is skipped and (None, local_path, hash) is returned so the
    caller can treat it as "unchanged".
    """
    os.makedirs(dest_dir, exist_ok=True)

    res = fetch(url, timeout=timeout)
    pdf_bytes = res.content
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()

    pdf_path = os.path.join(dest_dir, f"{safe_filename(name)}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    if expected_hash and current_hash == expected_hash:
        return None, pdf_path, current_hash

    return extract_pdf_text(pdf_path), pdf_path, current_hash
