import requests

url = "https://www.cdc.gov.tw/File/Get/OGeWZUe-8nCfqOKCak9kgg"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.head(url, headers=headers)
print("Content-Type:", r.headers.get("Content-Type"))
print("Content-Disposition:", r.headers.get("Content-Disposition"))
