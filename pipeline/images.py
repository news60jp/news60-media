"""話題に合う写真を Openverse(商用利用可のCC画像)から探してダウンロードする。
返り値: (ローカルパス, クレジット文字列) または (None, None)
"""
import os, json, re, hashlib, urllib.request, urllib.parse
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img_cache"); os.makedirs(CACHE, exist_ok=True)
UA = "news60bot/1.0 (news60jp)"

def _get(url, timeout=30, tries=3):
    import time
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(1.5)

def search(query, n=8):
    q = urllib.parse.urlencode({"q": query, "license_type": "commercial", "page_size": n, "mature": "false"})
    try:
        d = json.loads(_get(f"https://api.openverse.org/v1/images/?{q}", 25))
    except Exception:
        return []
    out = []
    for r in d.get("results", []):
        w, h = r.get("width") or 0, r.get("height") or 0
        url = r.get("url", "")
        if "staticflickr.com" in url and not url.endswith("_b.jpg"): url = re.sub(r"(_[a-z])?\.jpg$", "_b.jpg", url)
        out.append({"url": url, "w": w, "h": h, "title": r.get("title") or "", "creator": r.get("creator") or "",
                    "license": (r.get("license") or "").upper(), "fallback": r.get("url", "")})
    return out

def fetch(query):
    for cand in search(query):
        for url in (cand["url"], cand["fallback"]):
            key = hashlib.md5(url.encode()).hexdigest()[:12]; path = os.path.join(CACHE, key + ".jpg")
            try:
                if not os.path.exists(path):
                    data = _get(url, 40)
                    if len(data) < 20000: continue
                    open(path, "wb").write(data)
                from PIL import Image
                im = Image.open(path); im.verify()
                im = Image.open(path)
                if im.size[0] < 600: continue
                lic = cand["license"].replace("CC0", "CC0").replace("PDM", "Public Domain")
                credit = f"写真: {cand['creator'][:24]} ({lic})" if cand["creator"] else f"写真: Openverse ({lic})"
                return path, credit
            except Exception:
                continue
    return None, None

if __name__ == "__main__":
    import sys; print(fetch(" ".join(sys.argv[1:])))
