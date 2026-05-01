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

## 構成

```
showcase/
├── index.html              # 単一ページ
├── style.css               # vanilla CSS (TPR 規範に準拠、Tailwind 不使用)
├── app.js                  # fetch + Chart.js v4 描画
├── data/                   # build-data.py の出力
│   ├── overview.json
│   ├── paperbench.json
│   ├── self-improving.json
│   ├── reproduce.json
│   └── literature-scout.json
├── build-data.py           # raw component outputs → UI 用 JSON
└── README.md
```

外部依存: Chart.js v4 (CDN) のみ。ビルドツール不要。

## 起動

```sh
cd /Users/s30825/dev/autores/showcase
python3 -m http.server 8080
# → http://localhost:8080/ をブラウザで開く
```

## データを更新する

`reproduce/results/` や `self-improving-agent/logs/`、`results/stochastic-interpolants/` のソース JSON を更新したら、再生成:

```sh
cd /Users/s30825/dev/autores/showcase
uv run python build-data.py
# → data/*.json が再生成される。HTML はリロードするだけ
```

`build-data.py` は標準ライブラリのみで動く (`# /// script` shebang)。入力が見つからなければ警告を出して空 dict を吐く設計（壊れず生成）。

## データソース対応表

| Section | Raw input | Output JSON |
|---|---|---|
| §1 PaperBench iter | `docs/score-log.md` + `results/stochastic-interpolants/evaluation-{full,improved-v1,improved-v2}.json` | `data/paperbench.json` |
| §2 self-improving-agent | `self-improving-agent/logs/cycle-000{1..5}.json` | `data/self-improving.json` |
| §3 reproduce | `reproduce/results/stochastic-interpolants-e2e-test/report.json` | `data/reproduce.json` |
| §4 literature-scout | (スタブ — `build-data.py` 内 hard-code) | `data/literature-scout.json` |
| Hero / §5 | 上記4つの集約 | `data/overview.json` |

literature-scout のみライブ取得は arXiv 429 / Semantic Scholar 0件で当面動かない。代わりに代表的な3件の擬似サンプルを表示。発表時に「実体は CLI、本日は live 取得せず代表出力」と注記する。

## 4 components 一文サマリ

| # | Component | 一文 | Key metric |
|---|---|---|---|
| 1 | PaperBench iter | generate-then-iterate でコード再現スコアを 43.2% → 67.5% → 94.5% に押し上げる改善ループ | **94.5%** (1論文、58 nodes) |
| 2 | self-improving-agent | Claude が train.py を自動で書き換える 24/365 自己改善ループ。CIFAR-10 CNN で 5 cycles | best **0.6957** (cycle 4) |
| 3 | reproduce | arXiv URL → 5 stages (Paper Fetching → Code Finding → Env Building → Execution → Verification) end-to-end 再現パイプライン | **score 0.5 / 161s** on Stochastic Interpolants |
| 4 | literature-scout | arXiv + Semantic Scholar を同時検索し、Claude が研究文脈に対する relevance を判定する CLI | (live は外部 API 不調) |

## デザイン規範

- Vanilla CSS、Tailwind 不使用（`trending-paper-reviews` と同じ手法）
- カラー: bg `#fafafa`、text `#1a1a1a`、accent `#0066cc`、border `#e5e5e5`
- フォント: system stack + Noto Sans JP
- ライトモードのみ
- container max-width 1000px (TPR 800 だとチャートが窮屈なため拡張)

## GitHub Pages 互換

すべての fetch を相対パス (`./data/...`) で書いている。そのまま `gh-pages` ブランチに push or `docs/` 配下に置けば動く。

## 関連

- 発表資料本体: `~/knowledgebase/personal/autores/autores-meeting-2026-05-01.md`
- リハーサル台本: `~/knowledgebase/operations/projects/autores-demo-2026-05-01.md`
- 同じスタイル規範のサイト: `~/dev/trending-paper-reviews/` (https://t46.github.io/trending-paper-reviews/)
