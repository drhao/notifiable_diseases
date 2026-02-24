import requests
from bs4 import BeautifulSoup
import urllib.parse

url = "https://www.cdc.gov.tw/Category/DiseaseManual/bU9xd21vK0l5S3gwb3VUTldqdVNnQT09"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
r.encoding = 'utf-8'
soup = BeautifulSoup(r.text, 'html.parser')

print("HTTP Status Code:", r.status_code)
print("Page Title:", soup.title.text if soup.title else "No Title")

# Find content area, usually .lp-list or .content
# Let's just find all links that might lead to diseases
links = soup.select('a[href]')
print("\nSample Links:")
count = 0
for a in links:
    href = a['href']
    text = a.text.strip()
    if ('/Category/MPage/' in href or '/Category/ListContent/' in href or '/Disease/' in href or '/File/' in href):
        full_url = urllib.parse.urljoin("https://www.cdc.gov.tw", href)
        print(f"Title: {text} | URL: {full_url}")
        count += 1
        if count > 30:
            break
print(f"Total potential links found: {count}")

# Check for pagination
pages = soup.select('div.pagination a')
if pages:
    print("\nPagination found:")
    for p in pages:
        print(p.text.strip(), p.get('href'))
else:
    print("\nNo pagination found.")
