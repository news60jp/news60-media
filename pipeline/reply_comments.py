"""自分の投稿(直近7日)に付いたコメントへ返信する(news60_jp)。他人の投稿には触らない。
使い方: python3 reply_comments.py            … 未返信コメント一覧をJSONで出す
        python3 reply_comments.py replies.json … {"comment_id": "返信文", ...} を投稿する
"""
import sys, json, datetime
import post_reel as p

def pending():
    out = []
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    for m in p.get(f"{p.IG}/media", fields="id,permalink,timestamp,caption", limit=15)["data"]:
        if m["timestamp"] < since: continue
        cs = p.get(f"{m['id']}/comments", fields="id,text,username,timestamp,replies{username,text}").get("data", [])
        # 自分のコメントは API が username を返さない(最初のコメントなど)ので、username なしも自分扱い
        mine = lambda x: x.get("username") in (None, "news60_jp")
        for c in cs:
            if mine(c): continue
            if any(mine(r) for r in c.get("replies", {}).get("data", [])): continue
            out.append({"comment_id": c["id"], "user": c["username"], "text": c.get("text", ""),
                        "post": m["permalink"], "caption": (m.get("caption") or "")[:60]})
    return out

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(json.dumps(pending(), ensure_ascii=False, indent=1))
    else:
        for cid, msg in json.load(open(sys.argv[1])).items():
            print(cid, p.call(f"{cid}/replies", message=msg))
