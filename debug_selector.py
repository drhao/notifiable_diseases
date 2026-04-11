import requests
from bs4 import BeautifulSoup

url = "https://www.cdc.gov.tw/Category/DiseaseManual/bU9xd21vK0l5S3gwb3VUTldqdVNnQT09"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
r.encoding = 'utf-8'
soup = BeautifulSoup(r.text, 'html.parser')

links = soup.select('a[href]')
for a in links:
    if '阿米巴性痢疾' in a.text:
        print("Found 阿米巴性痢疾! CSS path:")
        parent = a.parent
        path = []
        while parent and parent.name != 'body':
            if parent.name:
                classes = ".".join(parent.get('class', []))
                path.append(f"{parent.name}{'.' + classes if classes else ''}")
            parent = parent.parent
        print(" > ".join(reversed(path)))
        break
