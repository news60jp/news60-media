# news60 毎朝パイプライン(改良版 2026-11-05)

毎朝、その日いちばん「止まる」ニュースを61〜70秒の縦型動画にして、InstagramとTikTokに自動投稿する。尺・つかみ・字幕などの細かいルールは STYLE.md が最新(README と食い違う場合は STYLE.md を優先)。

## 手順(スケジュール実行時にClaudeが行う)
1. /home/claude/news60/.env と make_video.py, publish.py, post_reel.py, images.py, STYLE.md があることを確認(なければ利用者に報告して終了)
2. add_repo で news60jp/news60-media を push で接続
3. ネタ選び: ジャンルは「日本の最新政治」と「世界の政治」(STYLE.md)。候補6本を採点し最高点を選ぶ。事実は出典2つ以上
4. 台本 script.json を書く(形式は make_video.py 冒頭)。必ず入れるもの:
   - シーン1 = つかみ: heading は「意外な数字」か「結論」。points は「この動画で分かること」を1つだけ。lines は1〜2行、**5秒以内**で終える(「〜を60秒で見ていきます」の決まり文句は言わない。2026-11-09 の週次分析: つかみが12〜17秒あり、平均視聴6〜16秒の視聴者がつかみの途中で離脱していた)
   - 各シーンに image_query(英語キーワードを2〜3個の配列。例 ["japan supermarket food shelf","supermarket groceries"])。写真はOpenverse(商用可CC)から自動取得。見つからなければ単色背景に自動で戻る
   - 1本に最低1つ number 付きシーン
   - 最後のフォロー・いいね画面は自動で付く(台本に書かない)。最終行は問いかけ+「コメントで教えてください」
   - ナレーション合計 280〜340文字、完成尺 61〜70秒(2026-11-09 更新。77秒の2本は視聴割合12%・4%、65秒は24%)。min_seconds=61。尺が足りなければ読み上げ速度を自動で落として61秒以上にする(無音で伸ばさない)
   - 1本に1つ「人に送りたくなる1枚」(比較表・票数や金額の一覧)のシーンを入れる。最後の問いかけは2択
5. python3 make_video.py script.json out/YYYY-MM-DD.mp4 → ffmpeg で冒頭・中盤・終盤のフレームを抜いて確認。字幕のはみ出し・重なりがあれば直して作り直す(1回まで)
6. Instagram: python3 publish.py out/YYYY-MM-DD.mp4 "キャプション"(GitHubへ置いてリール投稿)
7. TikTok: python3 post_tiktok.py <publish.pyが出した公開URL> "<説明文150字以内>"(Buffer API経由。.env に BUFFER_API_KEY と BUFFER_TIKTOK_CHANNEL_ID が必要)。返答の post.id を控え、1〜3分後に status が sent になったか確認(sending のままなら時間をおいて再確認、error があれば報告)
8. SendUserFile で動画、SendUserMessage で投稿URLを報告

## キャプションの型
1行目: 要点+数字(30字以内)。続けて「いつから?何が対象?を60秒で」のように見どころ
空行
「※YYYY年M月D日時点の情報です。出典: …」
「※AI音声・図解で制作 / 写真はCCライセンス素材(Openverse)」
ハッシュタグ: 合計3〜5個(#ニュース #60秒ニュース + テーマの固有名詞1〜3個。2026-11-09 更新)
キャプション末尾に必ず「フォローで明日も1分でニュース👉 @news60_jp」を入れる
最初のコメント: publish.py の3つ目の引数に「視聴者が答えたくなる問いかけ(2択+コメントで教えて)」を渡す。投稿直後に自分で付く

## TikTok用の説明文
1行目の要点 + 出典 + ハッシュタグ(合計150字以内)


## ストーリーズ
publish.py はリール投稿後、つかみ(シーン1。5秒以内)を切り出した予告版を自動でストーリーズにも投稿する(長さは make_video が出す .timing.json の hook_end)(露出アップ用。失敗してもリールは成功扱い)。


## コメント返信(毎晩)
`python3 reply_comments.py` で未返信コメントを出し、1件ずつ丁寧な返信文(30〜60字、質問には答える、意見には感謝+一言、荒らし・誹謗には返信しない)を JSON にして `python3 reply_comments.py replies.json` で投稿する。自分の投稿のコメントだけが対象。他人の投稿へのいいね・コメントは絶対にしない。
