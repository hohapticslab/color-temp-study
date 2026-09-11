# 色と温度の印象に関するオンライン調査 — ファイルの説明と公開手順

HP URL: https://hohapticslab.github.io/color-temp-study/
Data google sheet: 
https://docs.google.com/spreadsheets/d/1IttiC4SNe3jkb0GFjURQtFkuqO9ERodvOqT2nZaVDpg/edit?usp=sharing

## 1. ファイル構成

| ファイル | 役割 |
|---|---|
| `color_temperature_study.html` | 実験本体。これ1ファイルだけで動きます（外部依存はGoogle Fontsのみ）。言語選択 → 同意 → 画面設定 → 教示 → 練習1試行 → 本番12試行 → 終了画面、という流れです。 |
| `Code.gs` | Google Apps Script のコード。参加者の回答を Google スプレッドシートに書き込む「受け口」です。 |
| `README.md` | 英語版の説明書（本書と同内容＋データ列の詳細）。 |

### 実験の内容

- 刺激：CIELCh の12色相（10°〜340°、30°刻み）、明度 L* = 70 固定、各色相で最大彩度。sRGB 値として提示します。
- 各色を1回ずつ、ランダムな順序で提示（本番12試行＋灰色の練習1試行）。
- 回答：線分上をクリック／タップする VAS（左端「とても冷たい」、右端「とても熱い」）。0〜100 で記録、目盛や数値は参加者に見せません。
- 各試行に1分の制限時間。時間切れになると自動的に次へ進み、`timed_out = 1` として記録されます。
- 試行間には 500 ms の灰色画面（ISI）。
- 背景は中性灰（#8f8f8f）に固定し、OS のダークモード設定は無視します（全員が同じ周囲条件で色を見るため）。
- 教示は日本語・英語・繁体字中国語から参加者が選択。

### データの流れ

1. 参加者が「練習を始める」を押すと、ページがスプレッドシートに問い合わせ、**被験者コード**（S001, S002, …）が自動で割り当てられます。
2. 各試行で「次へ」を押した瞬間に、その1行がシートの `responses` タブに書き込まれます（途中で離脱しても、そこまでのデータは残ります）。
3. 終了時に `subjects` タブの該当者が「completed」に更新されます。
4. 複数人が同時に参加しても問題ありません（書き込みはロックで直列化されます）。

通信に失敗した場合でもページは止まらず、終了画面で参加者に CSV のダウンロードを促し、研究者に送ってもらう形になります。

## 2. 回答用スプレッドシートの準備（約5分）

1. sheets.google.com で新しいスプレッドシートを作成します（例：「color-temp-vas responses」）。
2. メニューの「拡張機能」→「Apps Script」を開きます。最初から入っているコードを消し、`Code.gs` の中身をすべて貼り付けて保存します。
3. 右上の「デプロイ」→「新しいデプロイ」。歯車アイコンから種類を **ウェブアプリ** に。
   - 次のユーザーとして実行：**自分**
   - アクセスできるユーザー：**全員**
4. 「デプロイ」を押すと承認を求められます。自分の Google アカウントを選び、「このアプリは Google で確認されていません」と出たら「詳細」→「（安全ではないページ）に移動」→「許可」。自作のスクリプトなので、この警告は正常です。
5. 表示された **ウェブアプリの URL**（末尾が `/exec`）をコピーします。https://script.google.com/macros/s/AKfycbxLdmTyOn5jF70sgHw4hiFL2F9Tnx5V8OXkSbkH04JnSCA9nLdAEiU-Y8WiX4B7vmzQEA/exec
6. その URL をブラウザで一度開き、`{"ok":true,"service":"color-temp-vas"}` と表示されれば準備完了です。

## 3. HTML に URL を設定する

`color_temperature_study.html` をテキストエディタで開き、`<script>` の先頭付近にある `CONFIG` を編集します。

```js
const CONFIG = {
  STUDY_ID: "color-temp-vas-v1",
  ENDPOINT_URL: "",          // ← ここに手順2の URL を貼り付ける: https://script.google.com/macros/s/AKfycbxLdmTyOn5jF70sgHw4hiFL2F9Tnx5V8OXkSbkH04JnSCA9nLdAEiU-Y8WiX4B7vmzQEA/exec
  REPS: 1,                   // 各色の繰り返し回数（1 = 各色1回）
  ISI_MS: 500,               // 試行間の灰色画面（ms）
  TRIAL_TIMEOUT_MS: 60000,   // 1試行の制限時間（ms）。0 で無制限
  ...
```

変更しそうな設定はすべてこのブロックにあります（送信先 URL、繰り返し回数、ISI、制限時間、練習刺激、12色の RGB 値と L*/C*/色相のメタデータ）。同意文や教示文はすぐ下の `I18N` ブロック（ja / en / zh-Hant）にあります。

`ENDPOINT_URL` を空のままにすると送信は行われず、参加者が終了時に CSV をダウンロードしてメールで送る方式になります。

動作確認は、HTML ファイルをダブルクリックしてブラウザで開くだけでできます（ローカルファイルからでも Apps Script への送信は動きます）。1回通しで回答し、スプレッドシートに `subjects` と `responses` の2タブができて行が追加されていれば成功です。

## 4. ページをオンラインに公開する

静的ファイルを置けるサーバーならどこでも動きます。もっとも簡単なのは GitHub Pages です。

### GitHub Pages を使う場合（無料・約5分）

1. github.com でリポジトリを新規作成します（Public、名前は例えば `color-temp-study`）。
2. 「Add file」→「Upload files」で `color_temperature_study.html` をアップロードします。このとき、ファイル名を **`index.html`** に変更してください。
3. リポジトリの「Settings」→ 左メニュー「Pages」→「Branch」で `main` と `/ (root)` を選び「Save」。
4. 1分ほど待つと `https://＜ユーザー名＞.github.io/color-temp-study/` で公開されます。これが参加者に送る URL です。

### その他の方法

- 研究室のウェブサーバーがあれば、HTML ファイルを1つ置くだけで動きます。
- Netlify Drop（app.netlify.com/drop）はファイルをドラッグ＆ドロップするだけで公開できます。
- Google ドライブは HTML ページを配信しなくなったため、**使えません**。

## 5. 参加者への案内

参加者には URL を送るだけです。終了画面に **被験者コード**（例：S012）と **完了コード**（例：S012-FQPR4DC7）が表示されます。クラウドソーシング（CrowdWorks、Lancers、Prolific など）で募集する場合は、完了コードを報告してもらえば、シート上の `session_id` と照合できます。

同一の PC で参加者を続けて実施する場合は、終了画面の「次の参加者を開始」ボタンで最初に戻れます。

本番前に、PC とスマートフォンからそれぞれ1回ずつ通して回答し、シートに13行（練習1＋本番12）ずつ記録されることを確認してください。

## 6. 運用上の注意

- **被験者番号のリセット**：カウンターはシートではなくスクリプトのプロパティに保存されているので、シートを空にしても S001 には戻りません。Apps Script エディタの「プロジェクトの設定」（歯車）→「スクリプト プロパティ」で `subject_counter` を削除（または任意の数に変更）してから、2つのタブを空にしてください。パイロット後、本番前にこれを行うのがよいです。
- **Code.gs を編集したとき**：Apps Script のウェブアプリは自動更新されません。「デプロイ」→「デプロイを管理」→ 鉛筆アイコン →「バージョン：新バージョン」→「デプロイ」が必要です。URL は変わりません。
- **同意文**：現在の文面は汎用的な仮のものです。倫理審査の承認番号や連絡先など、必要な記載を `I18N` の `consent1` / `consent2` に追加してください。上部の研究室名（「九州大学 ・ ハプティクス研究室」）も同様に変更できます。

## 7. 記録されるデータ

`responses` タブ：1試行1行。

| 列 | 内容 |
|---|---|
| study_id, session_id, subject_code, participant_id, lang | 識別子。`subject_code` はシートが割り当てる連番、`participant_id` は参加者が入力した ID（任意） |
| practice | 練習試行 = 1、本番 = 0 |
| trial, rep | 試行番号（練習含む）と繰り返しブロック |
| color_name, hue_deg, L_star, C_star, r, g, b, hex | 刺激 |
| vas | 評定値 0〜100（0 = とても冷たい、100 = とても熱い）、0.1 刻み。クリック前に時間切れの場合は空欄 |
| timed_out | 1分以内に「次へ」を押さなかった場合 1 |
| rt_first_ms | 刺激提示から最初のクリックまでの時間 |
| rt_submit_ms | 刺激提示から「次へ」までの時間 |
| n_adjust | 「次へ」までにマーカーを動かした回数 |
| timestamp | 「次へ」を押した時刻（ISO 形式） |
| screen_w, screen_h, viewport_w, viewport_h, dpr, color_depth | ディスプレイ情報 |
| gamut_p3 | Display P3 対応ディスプレイと報告された場合 1 |
| prefers_dark | OS がダークモードなら 1（ページ自体は無視） |
| touch, user_agent, tz | デバイス情報 |
| received_at | サーバー側の受信時刻 |

`subjects` タブ：参加者1人1行（subject_code, session_id, participant_id, lang, status, started_at, finished_at, n_trials とデバイス情報）。進行中・離脱した参加者の確認に使えます。

## Web server
Use HoLab GitHub
ID: holab.haptics@gmail.com
Password: Haptics0701
