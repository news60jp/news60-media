"""動画をGitHub(news60-media)に置いてInstagramにリール投稿する。
使い方: python3 publish.py out/video.mp4 "キャプション"
"""
import os, sys, shutil, subprocess, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/claude/news60-media"
sys.path.insert(0, HERE)
from post_reel import post_reel, post_story, media_id_from_permalink, first_comment

def upload(video):
    if not os.path.isdir(os.path.join(REPO, ".git")):
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/news60jp/news60-media", REPO], check=True)
    subprocess.run(["git", "-C", REPO, "config", "user.email", "news60jp@users.noreply.github.com"], check=True)
    subprocess.run(["git", "-C", REPO, "config", "user.name", "news60 bot"], check=True)
    subprocess.run(["git", "-C", REPO, "fetch", "-q", "origin", "main"], check=True)
    subprocess.run(["git", "-C", REPO, "reset", "-q", "--hard", "origin/main"], check=True)
    name = datetime.date.today().isoformat() + "_" + os.path.basename(video)
    os.makedirs(os.path.join(REPO, "videos"), exist_ok=True)
    shutil.copy(video, os.path.join(REPO, "videos", name))
    subprocess.run(["git", "-C", REPO, "add", "-A"], check=True)
    subprocess.run(["git", "-C", REPO, "commit", "-qm", f"Add {name}"], check=True)
    subprocess.run(["git", "-C", REPO, "push", "-q", "origin", "main"], check=True)
    return f"https://raw.githubusercontent.com/news60jp/news60-media/main/videos/{name}"

if __name__ == "__main__":
    url = upload(sys.argv[1]); print("uploaded:", url)
    permalink = post_reel(url, sys.argv[2]); print("posted:", permalink)
    # 3つ目の引数があれば最初のコメント(問いかけ)を自分で付ける
    if len(sys.argv) > 3 and sys.argv[3].strip():
        try: print("first comment:", first_comment(media_id_from_permalink(permalink), sys.argv[3]))
        except Exception as e: print("first comment failed:", e)
    # ストーリーズは60秒以内の制限があるので冒頭20秒の予告版を切り出して流す
    try:
        import subprocess
        teaser = sys.argv[1].rsplit(".",1)[0] + "_story.mp4"
        # 「〜を60秒で見ていきます」(つかみの最後)で終わるように、make_video が書いた timing.json を使う
        import json as _j
        tj = sys.argv[1].rsplit(".",1)[0] + ".timing.json"
        T = min(59.0, _j.load(open(tj))["hook_end"]) if os.path.exists(tj) else 20.0
        cta = max(0.0, T - 4.0); fo = max(0.0, T - 1.0)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",sys.argv[1],"-t",f"{T:.2f}",
            "-vf",f"drawbox=y=1500:h=190:color=black@0.65:t=fill:enable='gte(t,{cta:.2f})',"
                  f"drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc:text='続きはリールで ▶':fontsize=84:fontcolor=white:x=(w-tw)/2:y=1548:enable='gte(t,{cta:.2f})',"
                  f"fade=t=out:st={fo:.2f}:d=1","-af",f"afade=t=out:st={fo:.2f}:d=1",
            "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",teaser], check=True)
        print("story:", post_story(upload(teaser)))
    except Exception as e: print("story failed (reel ok):", e)
