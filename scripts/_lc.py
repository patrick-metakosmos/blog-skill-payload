import urllib.request, sys
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE="https://metakosmos.com.br"
for p in sys.argv[1:]:
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+p, headers={"User-Agent":UA}), timeout=30) as r:
            fin=r.geturl().replace(BASE,'')
            print(f"{r.status}  {p}" + (f"  ->{fin}" if fin!=p else ""))
    except urllib.error.HTTPError as e:
        print(f"{e.code}  {p}  <== 404/erro")
    except Exception as e:
        print(f"ERR {p} {repr(e)[:50]}")
