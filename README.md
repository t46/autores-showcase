# AutoRes Showcase

5/1 ミーティング向けのショーケース。AutoRes 4 components (PaperBench iter, self-improving-agent, reproduce, literature-scout) の実成果を可視化 + Reproduce Pipeline Deep Dive。

**🌐 Live**: <https://t46.github.io/autores-showcase/>

| ページ | URL |
|---|---|
| 結果 | <https://t46.github.io/autores-showcase/index.html> |
| 手法・タスク | <https://t46.github.io/autores-showcase/methods.html> |
| **Reproduce Deep Dive** | <https://t46.github.io/autores-showcase/reproduce-deep-dive.html> |

**🔗 Companion repo**: [t46/autores-reproduce](https://github.com/t46/autores-reproduce) — Reproduce Pipeline 本体コード (deep-dive で見せている数値の出所)

---

## Quick clone (発表 / 説明用)

```bash
# 2 repos clone
git clone https://github.com/t46/autores-showcase.git
git clone https://github.com/t46/autores-reproduce.git

# Showcase をローカルで開く
cd autores-showcase
python3 -m http.server 8080
# → http://localhost:8080/ をブラウザで
```

ブラウザだけで完結する場合は live URL (<https://t46.github.io/autores-showcase/>) を直接開けば OK。

---

## 起動 — もう少し丁寧に

### 前提

- Python 3 (`python3 -m http.server` が動けば OK)
- データ再生成する場合のみ `uv` (https://docs.astral.sh/uv/)

### 動かす

```bash
git clone https://github.com/t46/autores-showcase.git
cd autores-showcase

# 静的サーバを立てる (http://localhost:8080)
python3 -m http.server 8080
```

ブラウザで <http://localhost:8080/> を開けば 結果ページ、`/methods.html` で手法ページ、`/reproduce-deep-dive.html` で Deep Dive。

外部依存は **Chart.js v4 + Mermaid v10 (CDN)** のみ、ビルドツール不要。 fetch は相対パス (`./data/...`) で書かれているので、そのまま GitHub Pages にも置ける。

### live URL を直接開く場合

clone 不要、ブラウザから:

- <https://t46.github.io/autores-showcase/>
- <https://t46.github.io/autores-showcase/methods.html>
- <https://t46.github.io/autores-showcase/reproduce-deep-dive.html>

---

## 構成

```
showcase/
├── index.html                  # 結果ページ (4 component overview + §3 reproduce)
├── methods.html                # 手法・タスク (各 component の「何をどう動かしているか」)
├── reproduce-deep-dive.html    # Reproduce Pipeline Deep Dive
│                                  ├── §0 はじめに / 前提用語
│                                  ├── §1 改善前 / 改善後 (5 論文 baseline vs improved)
│                                  ├── §2 4 つのコード改善
│                                  ├── §3 失敗ケースの正直な開示
│                                  ├── §4 並行実験 — agent に同じ問題を解かせる
│                                  ├── §6 パイプラインレベル改善実験 (4 mode 横並び)
│                                  └── §7 次の一手
├── style.css                   # vanilla CSS (Tailwind 不使用)
├── app.js                      # fetch + Chart.js v4 描画 (index.html 用)
├── data/                       # build-data.py の出力
│   ├── overview.json           #   §5 集約
│   ├── paperbench.json         #   §1 PaperBench Iter
│   ├── self-improving.json     #   §2 Self-Improving Agent
│   ├── reproduce.json          #   §3 Reproduce Pipeline
│   ├── literature-scout.json   #   §4 Literature Scout
│   ├── paperbench-batch.json   #   deep-dive §1 (5 論文 baseline / improved)
│   ├── agent-comparison.json   #   deep-dive §4 (3 主体並列実験)
│   └── pipeline-rethink.json   #   deep-dive §6 (4 mode 比較 + ought-to + ARA mapping)
├── build-data.py               # raw outputs → UI 用 JSON
└── README.md
```

---

## データを更新する

reproduce repo の評価結果や ARA 出力を更新したら、JSON を再生成:

```bash
cd autores-showcase
uv run python build-data.py
# → data/*.json が再生成される。HTML はリロードするだけ
```

`build-data.py` は標準ライブラリのみで動く (`# /// script` shebang)。 入力が見つからなければ警告を出して空 dict を吐く設計 (壊れず生成)。

### データソース対応表

| ページ / セクション | Raw input | Output JSON |
|---|---|---|
| index §1 PaperBench iter | `~/dev/autores/results/stochastic-interpolants/evaluation-{full,improved-v1,improved-v2}.json` | `data/paperbench.json` |
| index §2 self-improving-agent | `~/dev/autores/self-improving-agent/logs/cycle-000{1..5}.json` | `data/self-improving.json` |
| index §3 reproduce | `~/dev/autores/reproduce/results/stochastic-interpolants-e2e-test/report.json` | `data/reproduce.json` |
| index §4 literature-scout | (スタブ — `build-data.py` 内 hard-code) | `data/literature-scout.json` |
| index Hero / §5 | 上記 4 つの集約 | `data/overview.json` |
| **deep-dive §1** | `~/dev/autores/reproduce/results/paperbench-batch/<paper>/{baseline,improved}/evaluation.json` | `data/paperbench-batch.json` |
| **deep-dive §4** | `~/unktok/dev/autonomous-research-agent/runs/2026-04-30-reproduce-automation-{ara,prime}/` の claims / experiments | `data/agent-comparison.json` |
| **deep-dive §6** | `~/dev/autores/reproduce/results/paperbench-batch/<paper>/{baseline,improved,ara-fixes,rubric-aware}/evaluation.json` | `data/pipeline-rethink.json` |

`build-data.py` は absolute path を内部にハードコードしているので、別環境で再生成する場合は `BATCH_ROOT`、`ARA_RUNS` 等の path 定数を該当環境に書き換える必要があります (data/*.json は repo に commit されているので、ブラウザで開くだけなら再生成は不要)。

---

## 4 components 一文サマリ

| # | Component | 一文 | Key metric |
|---|---|---|---|
| 1 | PaperBench iter | generate-then-iterate でコード再現スコアを 43.2% → 67.5% → 94.5% に押し上げる改善ループ | **94.5%** (1 論文、58 nodes) |
| 2 | self-improving-agent | Claude が train.py を自動で書き換える 24/365 自己改善ループ。CIFAR-10 CNN で 5 cycles | best **0.6957** (cycle 4) |
| 3 | reproduce | arXiv URL → 5 stages の end-to-end 再現パイプライン。 詳細は [Deep Dive](https://t46.github.io/autores-showcase/reproduce-deep-dive.html) (5 論文 × 4 mode = 20 evaluations、ARA 並行実験、rubric-aware Stage 2) | baseline mean **45.5** → ara-fixes **53.7** → rubric-aware **75.1** (※ rubric-aware は spec-disclosure 込み) |
| 4 | literature-scout | arXiv + Semantic Scholar を同時検索し、Claude が研究文脈に対する relevance を判定する CLI | (live は外部 API 不調) |

---

## デザイン規範

- Vanilla CSS、Tailwind 不使用 (`trending-paper-reviews` と同じ手法)
- カラー: bg `#fafafa`、text `#1a1a1a`、accent `#0066cc`、border `#e5e5e5`
- フォント: system stack + Noto Sans JP
- ライトモードのみ
- container max-width 1000px (TPR 800 だとチャートが窮屈なため拡張)

---

## 関連

- Reproduce Pipeline 本体: <https://github.com/t46/autores-reproduce>
- 同じスタイル規範のサイト: <https://t46.github.io/trending-paper-reviews/>
