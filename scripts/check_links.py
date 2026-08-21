#!/usr/bin/env python3
"""Verifica se URLs internas resolvem (200) no site ao vivo. Uso: python scripts/check_links.py <path_ou_url> ..."""
import urllib.request, urllib.error, sys
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://metakosmos.com.br"
for a in sys.argv[1:]:
    url = a if a.startswith("http") else BASE + a
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            print(f"{r.status}  {a}")
    except urllib.error.HTTPError as e:
        print(f"{e.code}  {a}  <== NAO USAR")
    except Exception as e:
        print(f"ERR {a}  {repr(e)[:50]}")
