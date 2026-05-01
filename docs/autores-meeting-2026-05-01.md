# AutoRes ミーティング 2026-05-01 — Reproduce Pipeline 強化と「再現はどうあるべきか」の問い直し

> **発表者**: 高木 史朗
> **日時**: 2026 年 5 月 1 日 AutoRes 研究グループミーティング
> **共有 URL**: <https://github.com/t46/autores-showcase/blob/main/docs/autores-meeting-2026-05-01.md>

---

## TL;DR

過去 1 ラウンドの強化で Reproduce Pipeline (= arXiv URL → 再現コード自動生成 → 数値検証 の 5 stage パイプライン) を 5 論文 × 4 mode で測定。 細かいバグ修正だけでなく、**「再現とは何をすることか」というパイプラインレベルの設計** を実装に落とし、さらに **同じ研究タスクを自律研究エージェント (ARA) にも並行で解かせる** メタ実験を行いました。

主要結果:

| mode | 5 論文 mean hierarchical_score |
|---|---|
| baseline (原型) | 45.51 |
| improved (4 局所改善) | 49.08 (+3.57) |
| ara-fixes (ARA-提案 fix を取り込み) | 53.72 (+4.64 vs improved) |
| rubric-aware (rubric を Stage 2 prompt に直接注入) | 75.15 (+21.42 vs ara-fixes、※ spec-disclosure 込み) |

ただし rubric-aware は **「judge が見る要件を agent に事前に見せる」** 構造で、benchmark の絶対値比較としては不公正 (test-disclosure に近い)。 重要なのは数値そのものより、**「再現はどう設計されるべきか」を実装で問い直して 4 mode で測れる体系を作った** ことと、**「人間が改善案を考えるより agent にループを閉じさせる方が深い改善が出る」可能性** を部分的に実証したこと。

実物 ➡ <https://t46.github.io/autores-showcase/reproduce-deep-dive.html>

---

## 共有してほしい URL (発表後に見返す用)

| | |
|---|---|
| **Reproduce Deep Dive (今回の主成果ページ)** | <https://t46.github.io/autores-showcase/reproduce-deep-dive.html> |
| 結果ページ (4 component overview) | <https://t46.github.io/autores-showcase/> |
| 手法・タスクページ (背景知識ゼロから読める) | <https://t46.github.io/autores-showcase/methods.html> |
| Reproduce Pipeline 本体コード | <https://github.com/t46/autores-reproduce> |
| Showcase 本体コード | <https://github.com/t46/autores-showcase> |

---

## §1 取り組んできたこと (要約)

AutoRes グループの目標 = ML 論文の実験結果を end-to-end で自動再現するシステム。 過去の実装ストックを 4 component に整理:

| # | Component | 一文 | 現在地 |
|---|---|---|---|
| 1 | PaperBench Iter | generate-then-iterate でコード再現スコアを 43.2% → 67.5% → 94.5% に押し上げる改善ループ | 1 論文で実証済 |
| 2 | Self-Improving Agent | Claude が train.py を自動で書き換える自己改善ループ。 CIFAR-10 CNN で 5 cycles | best 0.6957 (cycle 4) |
| 3 | Reproduce Pipeline | arXiv URL → 5 stages の end-to-end 再現パイプライン | **今回 5 論文 × 4 mode で測定 (本資料の中心)** |
| 4 | Literature Scout | arXiv + Semantic Scholar の同時検索 + Claude が relevance 判定 | live 動作確認済 |

詳細手法と各コンポーネントの仕組みは <https://t46.github.io/autores-showcase/methods.html> 参照。

---

## §2 出発点 — 1 論文で再現スコア 0.5 だった

最初の Reproduce Pipeline 実走 (Stochastic Interpolants 論文, arXiv:2310.03725) で:

- 5 stage は完走 (Paper Fetching → Code Finding → Env Building → Execution → Verification)
- ただし 3 件の数値主張 (FID 系) が **3 件全て untested** (実行出力に該当 metric なし)
- hierarchical_score = 0.5 は untested の partial credit (当時 0.5) で底上げされた値
- 実質「動くが何も検証できていない」状態

→ ここを起点に Reproduce Pipeline を強化することにした。

---

## §3 局所改善 4 件 + 5 論文での再測定

5 stage のうちボトルネック 3 stage に局所改善を入れた:

| 改善 | 対象 Stage | 内容 |
|---|---|---|
| ① metric alias 拡張 | Stage 5 (Verification) | 12 alias → 40+ (FID-50k, LPIPS, BERTScore 等) |
| ② success 厳密化 | Stage 4 (Execution) | returncode=0 だが silent failure を success と誤判定する問題を修正 |
| ③ pdfplumber 導入 | Stage 1 (Paper Fetching) | PyPDF2 → pdfplumber、Table 抽出可能に |
| ④ max_tokens 緩和 | Stage 2 (Code Finding) | 8192 → 16384 tokens (生成 cut-off 緩和) |

PaperBench から 5 論文 × 2 variants (baseline / improved) = 10 evaluations で再測定:

| paper | baseline | improved | Δ |
|---|---|---|---|
| stochastic-interpolants | 48.59 | 49.53 | +0.94 |
| semantic-self-consistency | 64.53 | 51.21 | -13.32 |
| sequential-NSE | 53.0 | 80.5 | +27.5 |
| mechanistic-understanding | 23.12 | 34.91 | +11.79 |
| robust-clip | 38.29 | 29.23 | -9.06 |
| **mean** | **45.51** | **49.08** | **+3.57** |

**主成分は「測定インフラの整備」**。 3 改善 / 2 regress、生成コード本体の質はほぼ動いていない。 Code-Dev mode (= judge による静的採点、実行不要) なので metric alias / success 厳密化は効果薄、効くのは pdfplumber と max_tokens のみ。

---

## §4 並行実験 — agent に同じ問題を解かせる

「Reproduce Pipeline を強くする」というタスクを、人間 + Claude の手作業 (上記 §3) と並行して **自律研究エージェント (ARA)** にも独立に解かせた。

3 主体並列:

| 主体 | harness | スキル | 結果 |
|---|---|---|---|
| A: 人間 + Claude | Claude Code 標準 | — | mean +3.6pt (5 論文) |
| **B: ARA (15 skills)** | sustainer 2 cycle × 4 phase 自律 | ARA 同梱 15 | **既存バグ 4 件発見** + H4 仮説で **subset 7 ノードで +24.3pp** |
| C: ARA + research-prime (123 skills) | ARA harness + Orchestra スキル群 | ARA 16 + Orchestra 95 + new/ 12 | failure pattern 4 クラスタ分類、Layer 0 validator 2 プロトタイプ (CLIIntrospector が F2 実証) |

主体 B が見つけた既存 reproduce repo のバグ (人間が見落としていた):

| Claim | 内容 |
|---|---|
| C-008 | `evaluate_paperbench.py` の glob が non-recursive で submission サブディレクトリを評価対象から漏らす |
| C-007 | code 候補ディレクトリ選択がボトルネック |
| C-010 | evaluation.json の paper_id が hardcoded |
| C-011 | Stage 2 prompt の "simplify / standard datasets" 指示が論文固有タスクを落とす scope failure を誘発 |

C-011 + H4 (targeted prompt fix) を組み合わせて stochastic-interpolants の rubric subset 7 ノードを 15.7% → 40.0% (+24.3pp) に押し上げ。

主体 B の Self-Evaluator は同セッション内で「+24.3pp は subset 7 ノードのみ、全 rubric ノードでは未検証」と自身で flag — agent が誇張を盛らない built-in mechanism が機能。

詳細: <https://t46.github.io/autores-showcase/reproduce-deep-dive.html#meta-experiment>

---

## §5 パイプラインレベル rethink — 「再現はどうあるべきか」

§3 の 4 改善は「細かい修正」レベル。 本来は **「再現とは何をすることか」というパイプラインレベルの設計** が問われていない、という Director 指摘を受けて、「再現に求められる ought-to」を 4 つ明示し、うち 2 つを実装に落とした。

### 4 つの ought-to

| key | 一文 | 今回 |
|---|---|---|
| **rubric-ground** | 再現は要件ツリー (rubric) に直接根拠を持つべき | ✅ rubric-aware mode で実装 |
| **decompose** | 再現はタスク単位に分解されるべき | ✅ ara-fixes / rubric-aware の H4 enforcement で実装 |
| verify | 要件単位で実行 + 数値一致まで検証されるべき | (Full mode、GPU 必要、scope 外) |
| iterate | 1 発生成ではなく v1 → 失敗 leaf 抽出 → v2 の反復であるべき | (2-pass loop は設計済、本実験では 1-pass のみ) |

### Rubric-Aware Stage 2 の実装

`code_finder.py` に新 mode を追加:
- rubric.json の leaf 要件 (= judge が後で採点する具体項目、weight 付き) を再帰展開
- 各 leaf を Stage 2 prompt に **重み付き checklist として直接注入**
- Claude は「judge が何を見るか」を事前に知ってコードを書く

これは **test-driven reproduction** という設計原則に対応する。

### ARA → Pipeline 対応 (どの ARA 提案がどこに入ったか)

| ARA Claim | 取り込み先 | 修正ファイル |
|---|---|---|
| C-008 (glob 非再帰) | ara-fixes / rubric-aware | `scripts/evaluate_paperbench.py` (glob → rglob + skip-dir) |
| C-010 (paper_id hardcoded) | ara-fixes / rubric-aware | `scripts/evaluate_paperbench.py` (rubric path から auto-derive) |
| H4 + C-011 (Stage 2 prompt scope failure) | ara-fixes / rubric-aware | `src/autores_reproduce/code_finder.py` (simplify 許可削除、ALL tasks / EXACT datasets を mandatory) |
| C-007 (code dir selection) | scope 外 | (次の一手) |

### 4 mode 横並び結果 (5 論文)

| paper | baseline | improved | ara-fixes | rubric-aware |
|---|---|---|---|---|
| stochastic-interpolants | 48.59 | 49.53 | 40.6 ↓ | 99.21 ↑↑ |
| semantic-self-consistency | 64.53 | 51.21 | 88.73 ↑ | 97.57 ↑ |
| sequential-NSE | 53.0 | 80.5 | 61.05 ↓ | 77.14 ↓ |
| mechanistic-understanding | 23.12 | 34.91 | 39.28 ↑ | 53.06 ↑ |
| robust-clip | 38.29 | 29.23 | 38.95 ↑ | 48.79 ↑ |
| **mean** | **45.51** | **49.08** | **53.72** | **75.15** |

mean delta:
- baseline → improved: +3.57 (局所改善 4 件)
- improved → ara-fixes: +4.64 (ARA fix 取込、ただし論文間で +37 〜 -19 の divergent)
- ara-fixes → rubric-aware: +21.42 (※ spec-disclosure 込み、benchmark としては不公正)
- baseline → rubric-aware: +29.64 (全部入り、上記 caveat 込み)

詳細: <https://t46.github.io/autores-showcase/reproduce-deep-dive.html#pipeline-rethink>

---

## §6 重要な caveat と反証可能性

### Caveat 1: rubric-aware = spec-disclosure に近い

rubric-aware mode では、本来 judge が採点に使う rubric の leaf 要件を生成 prompt に**事前に**注入している。 ML 的に厳密な意味の「test set で train する」(= モデル parameter を test ラベルで更新する) ではないが、**「採点される項目を agent に事前に見せている」という意味で test-disclosure / spec-disclosure** ではある。 生成側と採点側がさらに同じモデルファミリ (claude-sonnet-4) なので、表現一致による上振れリスクもある。

→ **rubric-aware の絶対スコアを baseline / improved / ara-fixes と単純比較するのは不公正**。 意味があるのは:

- ara-fixes vs baseline / improved (rubric-blind 同士の比較)
- rubric-aware vs ara-fixes (rubric を見せた効果の上限値推定)

PaperBench 公式は rubric を agent に見せない使い方を想定している可能性が高い。 厳密な leaderboard 比較は ara-fixes 以下のモードでのみ行うべき。

### Caveat 2: 論文ごとに drastically 違う効きかた

ara-fixes vs improved の per-paper delta:
- stochastic: -8.9 / semantic: +37.5 / seq-NSE: -19.5 / mechanistic: +4.4 / robust-clip: +9.7

ARA-a の H4 enforcement は「ALL tasks 強制」が裏目に出るケース (stochastic, sequential-NSE) と効くケース (semantic, mechanistic) で 2 極化。 「ARA fix は universal な改善ではない」ことが定量的に確認された。

### Caveat 3: ARA-a の +24.3pp は subset 7 ノードのみ

ARA-a 自身の Self-Evaluator がこれを flag。 全 rubric ノードに展開すると効果が変わる (実際に変わった)。 agent の出力は数字を盛らない built-in critique があっても、人間がその flag を読まずに数字を引用すれば誇張になる。

### 公正な比較に近づける次のステップ

- **Held-out rubric leaves**: 全 leaf のうち 50% だけを agent に渡し、残りは隠して評価する。 隠した leaf 上のスコアが上がれば「真の改善」、上がらなければ「単に見せた項目だけ pass している」
- **Cross-model judge**: 生成は claude-sonnet-4、採点は GPT-4o (PaperBench 公式) で表現一致リスクを切り分ける
- **Lexical overlap measurement**: 生成コード中の token と rubric leaf 文字列の overlap で「prompt をそのままコメント転写しているだけ」のケースを発見

---

## §7 次の一手

| 近い課題 | 内容 |
|---|---|
| 全 23 論文での測定 | 本日は 5 論文 (小規模)。残り 18 論文で改善の汎用性検証 |
| Stage 2 の prompt 改善 | C-007 (code dir selection) の解決、few-shot 追加 |
| NRR の Reproduce 統合 | Self-Improving Agent で実証済の NRR を Reproduce にも組込 |
| 公式 GPT-4o SimpleJudge への切替 | 生成 vs 採点モデルの分離、絶対値の公式比較 |

| もう一段先 | 内容 |
|---|---|
| Full mode 評価 | 実走 + 数値一致まで検証、GPU 必要 |
| Stage 3 env builder の本格改善 | 業界 SOTA でも < 7%、最大のフロンティア |
| Stage 1 OCR API 切替 | image-only な Table/Figure を Mistral OCR / Adobe Extract に |

| AutoRes グループとして見据える方向 | |
|---|---|
| end-to-end ループの 24/365 運用 | Literature Scout → Reproduce → PaperBench Iter → Self-Improving の循環 |
| **「人間が改善案を考えて実装する」を agent に渡してしまう** | §4 並行実験で初歩的な手応えあり、ARA + research-prime に Reproduce 改善を投げる自動橋渡しを作る |

---

## §8 議論したいこと (発表後の質疑用)

1. **rubric-aware の spec-disclosure 問題をどう厳密化するか** — held-out rubric leaves / cross-model judge / lexical overlap、どれが最も意味のある metric か
2. **ARA に Reproduce 改善ループを閉じさせる橋渡し** — 出力 patch を直接 PR にしてよいか、レビュー人が要るか
3. **Full mode (実走) にいつ移るか** — GPU + 環境構築の堅牢化が前提だが、Code-Dev でどこまで詰めるべきか
4. **PaperBench の選び方** — 23 論文全部測るより、構造の異なる 10 論文で多様性を測る方が良いのでは
5. **AutoRes グループとしての分担** — Literature Scout / Reproduce / PaperBench Iter / Self-Improving の interface 設計

---

## 定量サマリ (引用しやすい数字)

| 項目 | 値 |
|---|---|
| Reproduce Pipeline 5 論文 baseline mean hierarchical_score | **45.51** |
| improved (4 局所改善) mean | **49.08** (+3.57) |
| ara-fixes (ARA-提案 fix 取込) mean | **53.72** (+4.64 vs improved) |
| rubric-aware (Stage 2 に rubric 注入) mean | **75.15** (+21.42 vs ara-fixes、※ spec-disclosure 込み) |
| ARA-a が見つけた既存バグ件数 | **4 件** (人間が見落としていた) |
| H4 仮説 subset 検証 | stochastic-interpolants 7 ノードで 15.7% → 40.0% (+24.3 pp) |
| ARA harness × 主体 | 2 (ARA 15 skills / ARA + research-prime 123 skills) |

---

## 関連リンク

- **Reproduce Deep Dive** (本資料の数値の出所): <https://t46.github.io/autores-showcase/reproduce-deep-dive.html>
- **Reproduce Pipeline コード**: <https://github.com/t46/autores-reproduce> (default branch = main、4 mode 全部入り)
- **Showcase コード**: <https://github.com/t46/autores-showcase>
- ARA repo (autonomous-research-agent): mainline は ~/unktok/dev/autonomous-research-agent (公開状態は要確認)
- 本資料の旧版 (内部用、2026-04-26 update): `~/knowledgebase/personal/autores/autores-meeting-2026-05-01.md`

---

## 付録: 用語集

| 用語 | 意味 |
|---|---|
| Reproduce Pipeline | arXiv URL → PDF 取得 → コード生成 → 環境構築 → 実行 → 数値検証 を全自動で回すツール (5 stage) |
| PaperBench | OpenAI 公開の論文再現自動評価 benchmark、23 論文の rubric.json (採点ツリー) を持つ |
| hierarchical_score | rubric ツリーの leaf スコアを重み付きで親に伝播させて root に集約した値 (0-100)。 本資料の主要 metric |
| Code-Dev mode | 生成コードを judge に読ませて静的に採点 (GPU 不要)。 本資料の評価モード |
| Full mode | 実際にコード実行して数値が論文と一致するか確認 (GPU 必要、本資料 scope 外) |
| SimpleJudge | PaperBench 公式の評価器 (GPT-4o)。 本資料は claude-sonnet-4 で代替 |
| untested ノード | judge が「該当する数値主張を確認できなかった」と判定した rubric ノード。 partial credit 0.25 |
| ARA (Autonomous Research Agent) | Claude を Researcher / Evaluator / Reviewer / Improver の 4 役で回す自律研究 harness |
| research-prime | ARA + AI-Research-SKILLs (Orchestra) を融合したスキル集約リポ。 本資料の主体 C で skill セットのみ流用 |
| H4 仮説 | ARA-a が立てた "Stage 2 prompt から `simplify` / `standard datasets` の指示を除き、論文固有 dataset と全タスクを明示する" |
| spec-disclosure / test-disclosure | 評価される要件を agent に事前に見せること。 ML の strict な test-leakage ではないが構造的に近い |
| rubric.json | 各論文の採点ツリー (id / requirements / weight / sub_tasks の再帰)。 leaf の requirements が判定対象 |

---

*本資料は <https://github.com/t46/autores-showcase/blob/main/docs/autores-meeting-2026-05-01.md> から版管理されています。 議論で出た update もここに反映します。*
