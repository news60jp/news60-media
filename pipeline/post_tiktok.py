"""Buffer API 経由で TikTok に投稿する(Bufferの無料プラン、TikTok審査済みアプリ)。
.env に BUFFER_API_KEY と BUFFER_TIKTOK_CHANNEL_ID を入れておく。
使い方: python3 post_tiktok.py <公開URLの動画> "<説明文>"
"""
import os, sys, json, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
for line in open(os.path.join(HERE, ".env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ.setdefault(k, v)
KEY = os.environ.get("BUFFER_API_KEY"); CH = os.environ.get("BUFFER_TIKTOK_CHANNEL_ID")
API = "https://api.buffer.com/graphql"

def gql(query, variables=None):
    req = urllib.request.Request(API, data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)

def post(video_url, text, title=None):
    q = """mutation($i:CreatePostInput!){ createPost(input:$i){ __typename
             ... on PostActionSuccess { post { id status dueAt } }
             ... on MutationError { message } } }"""
    v = {"i": {"channelId": CH, "text": text, "needsApproval": False,
               "assets": [{"video": {"url": video_url}}],
               "metadata": {"tiktok": {"isAiGenerated": True, "title": title or text.split("\n")[0][:90]}},
               "schedulingType": "automatic", "mode": "shareNow"}}
    return gql(q, v)

if __name__ == "__main__":
    if not KEY or not CH: raise SystemExit("BUFFER_API_KEY / BUFFER_TIKTOK_CHANNEL_ID が .env にありません")
    print(json.dumps(post(sys.argv[1], sys.argv[2]), ensure_ascii=False))
