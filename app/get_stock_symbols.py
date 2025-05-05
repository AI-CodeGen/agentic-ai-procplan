import shutil
import urllib.request as request
from contextlib import closing
import csv

URLS = [
    {
        "url": "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt",
        "key": "ACT Symbol"
    },
    {
        "url": "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt",
        "key": "Symbol"
    }
]

symbols = []

for u in URLS:
    with closing(request.urlopen(u['url'])) as r:
        with open(u['url'].split("/")[-1], 'wb') as f:
            shutil.copyfileobj(r, f)
    with open(u['url'].split("/")[-1], 'r') as f:
        reader = csv.DictReader(f, delimiter="|")
        for line in reader:
            if len(u['key'].split(' ')) == 1:
                symbols.append(line[u['key']])

print(f'Symbols count: {len(symbols)}')