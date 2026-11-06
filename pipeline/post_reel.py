"""Instagramリールを自動投稿する(news60_jp)。
使い方: python3 post_reel.py <公開URLの動画> "<キャプション>"
動画はインターネット上の公開URLである必要がある(Meta側がダウンロードする)。
"""
import os, sys, time, json, urllib.request, urllib.parse

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
for line in open(ENV):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ.setdefault(k, v)
TOKEN, IG = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
API = "https://graph.facebook.com/v25.0"

def call(path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(f"{API}/{path}", data=data, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit("APIエラー: " + e.read().decode())

def get(path, **params):
    params["access_token"] = TOKEN
    with urllib.request.urlopen(f"{API}/{path}?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)

def _wait_and_publish(cid):
    for _ in range(60):  # 最大5分待つ
        st = get(cid, fields="status_code,status")
        if st["status_code"] == "FINISHED": break
        if st["status_code"] == "ERROR": raise SystemExit("動画の処理に失敗: " + json.dumps(st, ensure_ascii=False))
        time.sleep(5)
    else:
        raise SystemExit("タイムアウト: 動画の処理が終わりません")
    return call(f"{IG}/media_publish", creation_id=cid)["id"]

def post_reel(video_url, caption, share_to_feed=True):
    c = call(f"{IG}/media", media_type="REELS", video_url=video_url, caption=caption,
             share_to_feed="true" if share_to_feed else "false")
    mid = _wait_and_publish(c["id"])
    return get(mid, fields="permalink")["permalink"]

def post_story(video_url):
    """同じ動画をストーリーズにも流す(24時間で消える。露出を増やすため)"""
    c = call(f"{IG}/media", media_type="STORIES", video_url=video_url)
    return _wait_and_publish(c["id"])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    print("投稿しました:", post_reel(sys.argv[1], sys.argv[2]))
    try: print("ストーリーズにも投稿:", post_story(sys.argv[1]))
    except SystemExit as e: print("ストーリーズは失敗(リールは成功):", e)
