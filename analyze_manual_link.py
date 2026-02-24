import requests
from bs4 import BeautifulSoup

url = "https://www.cdc.gov.tw/File/Get/OGeWZUe-8nCfqOKCak9kgg"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
print("Final URL:", r.url)
print("Content-Type:", r.headers.get("Content-Type"))

# If it's HTML, let's see what's inside
if 'html' in r.headers.get("Content-Type", ""):
    soup = BeautifulSoup(r.text, 'html.parser')
    print("Page Title:", soup.title.text if soup.title else "No Title")
    print("PDF links found:")
    for a in soup.select('a[href]'):
        if '.pdf' in a['href'].lower() or '/File/' in a['href']:
            print(" -", a.text.strip(), a['href'])
else:
    print(f"Downloaded content. Length: {len(r.content)} bytes")
    with open("sample_download", "wb") as f:
        f.write(r.content[:1024]) # Check first KB
