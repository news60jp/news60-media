# NAS(DH2300)で毎朝の60秒ニュースを動かす

対象: /volume1/claude-work で動く Claude Code(ユーザー claude)。aptは使わない。`apt --fix-broken install` は絶対に実行しない。

## 1. 取得
```
cd /volume1/claude-work
git clone https://github.com/news60jp/news60-media.git
cd news60-media/pipeline
```
git がなければ `curl -L https://github.com/news60jp/news60-media/archive/refs/heads/main.tar.gz | tar xz` で取り出す。

## 2. 必要な道具の確認
```
uname -m; python3 --version; python3 -c "import PIL, numpy; print('ok')"; ffmpeg -version | head -1
```
- PIL/numpy/edge-tts がない → `python3 -m pip install --user pillow numpy edge-tts`(pipがなければ先に `python3 -m ensurepip --user`)
- ffmpeg がない → 単体ファイル版(aptは使わない):
```
mkdir -p ~/bin && cd ~/bin
curl -L -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz
tar xf ffmpeg.tar.xz --strip-components=1 --wildcards '*/ffmpeg' '*/ffprobe'
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc; export PATH="$HOME/bin:$PATH"
```
- 日本語フォント: `/usr/share/fonts/opentype/noto/NotoSansCJK-*.ttc` がなければ Google Fonts の Noto Sans JP(Black/Bold/Medium の .ttf)を `~/fonts/` に置き、make_video.py の FD と F() をそのファイル名に合わせる

## 3. 鍵(.env)
pipeline/.env を作る(Gitに入れない。`chmod 600 .env`):
```
IG_ACCESS_TOKEN=(Instagramのシステムユーザートークン)
IG_USER_ID=17841433797322838
GITHUB_TOKEN=(news60-media 用の fine-grained token)
GITHUB_REPO=news60jp/news60-media
BUFFER_API_KEY=(Buffer の API キー。TikTok用)
BUFFER_TIKTOK_CHANNEL_ID=(Buffer の TikTok チャンネルID)
```
publish.py の REPO は NAS では `/volume1/claude-work/news60-media` に変える。push 用に
`git remote set-url origin https://x-access-token:<GITHUB_TOKEN>@github.com/news60jp/news60-media.git`。

## 4. 動作確認
```
python3 make_video.py example_script.json out/test.mp4
```
60秒前後の mp4 ができれば成功。

## 5. 毎朝6:25に自動実行(systemd タイマー。cron は使えない)
`/etc/systemd/system/news60.service`
```
[Unit]
Description=news60 daily video
After=network-online.target

[Service]
Type=oneshot
User=claude
WorkingDirectory=/volume1/claude-work/news60-media/pipeline
Environment=GODEBUG=
Environment=PATH=/home/claude/bin:/home/claude/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/bin/bash -c '/home/claude/.local/bin/claude -p --allowedTools "Bash,Read,Write,Edit,WebSearch,WebFetch" "$(cat DAILY_PROMPT.md)"'
```
`/etc/systemd/system/news60.timer`
```
[Unit]
Description=news60 daily at 06:25

[Timer]
OnCalendar=*-*-* 06:25:00
Persistent=true

[Install]
WantedBy=timers.target
```
`sudo systemctl daemon-reload && sudo systemctl enable --now news60.timer`。NASのタイムゾーンは `timedatectl` で日本時間か確認。
手動テスト: `sudo systemctl start news60.service && journalctl -u news60 --no-pager | tail -50`
