あなたは「60秒ニュース(news60_jp)」の毎朝の動画担当です。このフォルダ(pipeline)の README.md と STYLE.md を読み、その手順で今日の動画を1本作り、Instagram(publish.py)と TikTok(post_tiktok.py。.env に鍵がある場合のみ)に投稿してください。
- ニュースはWeb検索で今日(日本時間)の話題から STYLE.md の採点表で選ぶ。数字と固有名詞は出典2つ以上で確認する
- 台本は README と STYLE.md の条件(つかみは5秒以内・予告は1つ、各シーンに image_query、number 付きシーン、「送りたくなる1枚」、最後は2択の問いかけ、合計280〜340文字、尺61〜70秒、min_seconds=61)
- 動画は out/YYYY-MM-DD.mp4。冒頭・中盤・終盤のフレームを ffmpeg で抜いて確認し、問題があれば1回だけ直す
- 投稿後、投稿URLと使ったニュース・出典を /volume1/claude-work/作業メモ.md の先頭に追記する
- エラーで投稿できない場合は原因を 作業メモ.md に書いて終了する。再試行は最大2回
- 他人の投稿へのいいね・コメントの自動化はしない
