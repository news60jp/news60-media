"""自分の投稿(直近7日)に付いたコメントへ返信する(news60_jp)。他人の投稿には触らない。
使い方: python3 reply_comments.py            … 未返信コメント一覧をJSONで出す
        python3 reply_comments.py replies.json … {"comment_id": "返信文", ...} を投稿する
"""
import sys, json, datetime
import post_reel as p

def pending():
    out = []
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
    for m in p.get(f"{p.IG}/media", fields="id,permalink,timestamp,caption", limit=15)["data"]:
        if m["timestamp"] < since: continue
        cs = p.get(f"{m['id']}/comments", fields="id,text,username,timestamp,replies{username,text}").get("data", [])
        for c in cs:
            if c.get("username") == "news60_jp": continue
            if any(r.get("username") == "news60_jp" for r in c.get("replies", {}).get("data", [])): continue
            out.append({"comment_id": c["id"], "user": c["username"], "text": c["text"],
                        "post": m["permalink"], "caption": (m.get("caption") or "")[:60]})
    return out

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(json.dumps(pending(), ensure_ascii=False, indent=1))
    else:
        for cid, msg in json.load(open(sys.argv[1])).items():
            print(cid, p.call(f"{cid}/replies", message=msg))
