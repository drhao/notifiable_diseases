import requests
from bs4 import BeautifulSoup
import urllib.parse
import pdfplumber
import os

pdf_url = urllib.parse.urljoin("https://www.cdc.gov.tw", "/Uploads/6c9ef7ee-2eda-4a2d-8be4-2e7b9fb30f53.pdf")
headers = {"User-Agent": "Mozilla/5.0"}
print(f"Downloading {pdf_url}...")
r = requests.get(pdf_url, headers=headers)
pdf_path = "sample_manual.pdf"
with open(pdf_path, "wb") as f:
    f.write(r.content)

print(f"Saved {pdf_path}. Size: {len(r.content)} bytes")

print("Extracting text...")
text = ""
with pdfplumber.open(pdf_path) as pdf:
    # Read first 3 pages
    for page in pdf.pages[:3]:
        extract = page.extract_text()
        if extract:
            text += extract + "\n\n---PAGE BREAK---\n\n"

print("Sample Text (first 2000 chars):")
print(text[:2000])

# Try to look for common headers like 一、 or 壹、
print("\n--- Potential Headers ---")
for line in text.split('\n'):
    line = line.strip()
    if line.startswith('一、') or line.startswith('二、') or line.startswith('三、') or line.startswith('四、') or line.startswith('壹、') or line.startswith('貳、'):
        print(line)
