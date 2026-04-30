#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Build UI-ready JSON for AutoRes 5/1 showcase from raw component outputs.

Run:  python build-data.py     (or: uv run build-data.py)
Outputs to ./data/{overview,paperbench,self-improving,reproduce,literature-scout}.json
Never crashes — missing inputs produce a stub with `_warning`.
"""
from __future__ import annotations
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/s30825/dev/autores")
OUT = Path(__file__).parent / "data"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
BATCH_ROOT = REPO / "reproduce" / "results" / "paperbench-batch"


def safe_load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_warning": f"failed to load {path}: {e}"}


def write_json(name: str, data: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    data["_generated_at"] = NOW
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  wrote data/{name}")


# -------------------------------------------------------------- §1 PaperBench
def build_paperbench() -> dict:
    base = REPO / "results" / "stochastic-interpolants"
    iters = []
    for label, path in [
        ("v0 baseline", "evaluation-full.json"),
        ("v1 +1 iter", "evaluation-improved-v1.json"),
        ("v2 +2 iter", "evaluation-improved-v2.json"),
    ]:
        d = safe_load(base / path)
        if "_warning" in d:
            iters.append({"label": label, **d})
            continue
        iters.append({
            "label": label,
            "hierarchical_score": float(d.get("hierarchical_score", 0)),
            "simple_average_score": float(d.get("simple_average_score", 0)),
            "score_distribution": d.get("score_distribution", {}),
            "num_nodes": int(d.get("num_nodes_total", 0)),
        })

    # "改善した点" / "失敗した点" notes — score-log.md の英語原文を 5/1 発表向けに日本語へ翻訳・整形
    notes = {
        "v0": {
            "improved": [
                "論文の解析（Stage 1）：主張・アーキテクチャ詳細・ハイパーパラメータ・コード参照をすべて正しく抽出",
                "ハイパーパラメータの一致（rubric Stage 4-5）：Adam optimizer、lr=2e-4、StepLR gamma=0.99/1000 steps、grad clip 10000、U-Net 構造（dim_mults、attention heads 等）すべて 100 点",
                "コアフレームワーク：Stochastic interpolant + torchdiffeq Dopri5 ソルバを使った ODE サンプリングを実装",
                "訓練ループの構造：損失計算のフレームワーク、時間サンプリング U(0,1) を実装",
            ],
            "failed": [
                "データソース：ImageNet ではなく CIFAR-10 を使ってしまった（dataset 関連ノードが 0/100）",
                "外部依存：lucidrains の denoising-diffusion-pytorch repo を取り込んでいない（0/100）",
                "タスク固有実装：Inpainting のマスク戦略が完全に間違い（64-tile ではなくピクセル単位、超解像のマスクも誤り）",
                "Dependent coupling：論文の核心となる貢献の実装が不完全（適切な data-conditioning ではなく汎用ノイズ相関になっていた）",
                "サンプリング手順：Algorithm 2 の明示的 Euler ステップではなく ODE solve を使ってしまった",
                "訓練ステップ：エポックベース（要件は 200,000 勾配ステップのステップベース）",
                "クラス条件付け：未実装（クラス値で uniform channel を埋める処理がない）",
            ],
        },
        "v1": {
            "improved": [
                "ImageNet データセットアクセス：HuggingFace datasets を使うように修正（スコア 0 → 100）",
                "マスク戦略：64-tile マスク（p=0.3）を実装（ほぼ修正完了）",
                "結合公式：x_0 = mask * x_1 + (1-mask) * noise を正しく実装",
                "ステップベース訓練：200,000 勾配ステップで訓練するように変更",
                "クラス条件付け：クラス値の uniform channel を追加",
                "バッチサイズ：要件通り 32 に固定",
                "両モデル：Dependent Coupling と Uncoupled Interpolant の両方を実装",
            ],
            "failed": [
                "lucidrains の U-Net：外部 repo からまだ import できていない（スコア 0 のまま）",
                "Dopri ソルバ：前回は使えていたが、書き直しの過程で Forward Euler に戻ってしまった",
                "勾配クリップ値：10,000 ではなく 1.0 に設定されている",
                "サンプリング細部：実装上の細かいズレが残る",
            ],
        },
        "v2": {
            "improved": [
                "Dopri ソルバ：torchdiffeq の odeint(method='dopri5') を復元",
                "FID 評価：fid_score.py を追加して正しい評価を実装",
                "超解像：適切なダウンサンプリング／アップサンプリングのパイプラインを構築",
                "Uncoupled モデル：dependent / uncoupled バリアントを明確に分離",
                "ODE 用モデルラッパー：torchdiffeq に対応する ODE 関数の正しいラッピング",
            ],
            "failed": [],
        },
    }

    sota = [
        {"agent": "DeepCode", "score": 75.9, "note": "20論文の平均", "ours": False},
        {"agent": "ML 博士号取得者（人間）", "score": 72.4, "note": "20論文の平均", "ours": False},
        {"agent": "IterativeAgent o1-high", "score": 43.4, "note": "20論文の平均 (Code-Dev)", "ours": False},
        {"agent": "autores v0.1（ベースライン）", "score": 43.2, "note": "1論文、改善なし", "ours": True},
        {"agent": "autores v0.1 + 1 反復", "score": 67.5, "note": "1論文", "ours": True},
        {"agent": "autores v0.1 + 2 反復", "score": 94.5, "note": "1論文（最易）", "ours": True, "highlight": True},
    ]

    return {
        "title": "PaperBench Code-Dev — Stochastic Interpolants 1論文での実証",
        "summary": "「生成 → 反復改善」のループで 43.2% → 67.5% → 94.5%。単一論文ではあるが SOTA を超える結果を達成。",
        "iterations": iters,
        "notes": notes,
        "sota_table": sota,
        "caveat": "94.5% は最も易しい論文1本（94 ノード）での結果。SOTA の数字は20論文平均なので、公平な比較ではない点に注意。",
    }


def parse_score_log_notes(path: Path) -> dict:
    """Extract 'What Improved' / 'What Failed' bullets per iteration from score-log.md."""
    if not path.exists():
        return {"_warning": f"{path} not found"}
    md = path.read_text()
    notes = {"v0": {"improved": [], "failed": []},
             "v1": {"improved": [], "failed": []},
             "v2": {"improved": [], "failed": []}}

    # Iteration 1 section: "Improvement Iteration 1" — improved=v1
    # Iteration 2 section: "Improvement Iteration 2" — improved=v2
    # Initial section (2026-04-20 | Stochastic Interpolants ...): improved/failed=v0

    sections = re.split(r"^## ", md, flags=re.MULTILINE)
    for sec in sections:
        title = sec.split("\n", 1)[0].strip()
        if "Improvement Iteration 1" in title:
            key = "v1"
        elif "Improvement Iteration 2" in title:
            key = "v2"
        elif "Stochastic Interpolants (PaperBench Code-Dev)" in title:
            key = "v0"
        else:
            continue
        for sub_label, dest in [("What Improved", "improved"),
                                ("What Worked", "improved"),
                                ("What Failed", "failed"),
                                ("What Still Failed", "failed")]:
            m = re.search(rf"### {sub_label}\s*\n(.*?)(?=\n### |\n## |\Z)", sec, re.DOTALL)
            if m:
                bullets = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*:?\s*(.*)$", m.group(1), re.MULTILINE)
                if not bullets:
                    bullets = re.findall(r"^\d+\.\s+(.+?)$", m.group(1), re.MULTILINE)
                    bullets = [(b.strip(), "") for b in bullets]
                for head, rest in bullets:
                    text = (head + ("：" + rest if rest else "")).strip()
                    if text and text not in notes[key][dest]:
                        notes[key][dest].append(text)
    return notes


# ---------------------------------------------------- §2 self-improving-agent
def build_self_improving() -> dict:
    base = REPO / "self-improving-agent" / "logs"
    cycles = []
    for i in range(1, 6):
        d = safe_load(base / f"cycle-{i:04d}.json")
        if "_warning" in d:
            cycles.append({"cycle": i, **d})
            continue
        s = d.get("score", {}) or {}
        imp = d.get("improvement", {}) or {}
        diff = (d.get("diff") or "").splitlines()
        delta = float(s.get("improvement_delta", 0) or 0)
        cycles.append({
            "cycle": int(d.get("cycle", i)),
            "accuracy": float(s.get("accuracy", 0) or 0),
            "loss": float(s.get("loss", 0) or 0),
            "improvement_delta": delta,
            "is_best": bool(s.get("is_best", False)),
            "regressed": delta < 0,
            "epochs": int(s.get("epochs", 0) or 0),
            "training_time_sec": float(s.get("training_time_sec", 0) or 0),
            "improvement": {
                "description": imp.get("description", ""),
                "category": imp.get("category", ""),
                "confidence": float(imp.get("confidence", 0) or 0),
                "reasoning": imp.get("reasoning", ""),
            },
            "diff_excerpt": "\n".join(diff[:30]),
        })

    accs = [c.get("accuracy", 0) for c in cycles if "accuracy" in c]
    best_cycle = max((c for c in cycles if c.get("is_best")), key=lambda c: c.get("accuracy", 0), default=None)
    return {
        "title": "Self-Improving Agent — CIFAR-10 CNN の自動改善ループ",
        "summary": "Claude が train.py を書き換える → 訓練 → 評価 → 失敗から学習する 24/365 ループ。5 サイクルで最高精度 0.6957 を達成。",
        "cycles": cycles,
        "best_cycle": best_cycle.get("cycle") if best_cycle else None,
        "best_accuracy": max(accs) if accs else None,
        "total_cycles": len(cycles),
        "regressed_count": sum(1 for c in cycles if c.get("regressed")),
        "note": "毎サイクル改善するわけではない。退行（サイクル3、5）は、ロールバックと失敗履歴管理（NRR）の必要性を体現している。",
    }


# ------------------------------------------------------------- §3 reproduce
def build_reproduce() -> dict:
    p = REPO / "reproduce" / "results" / "stochastic-interpolants-e2e-test" / "report.json"
    d = safe_load(p)
    if "_warning" in d:
        return d

    pi = d.get("paper_info", {}) or {}

    # 各ステージの英語 message を補完する日本語キャプション
    stage_jp = {
        "Paper Fetching": "arXiv API で PDF を取得し、Claude が論文から方法論・主張する数値・ハイパラを構造化抽出した。",
        "Code Finding": "公式 GitHub が見つからなかったため、Claude が論文記述を読んでゼロから実装を生成した（生成 fallback）。これが時間の 56% を占める理由。",
        "Environment Building": "Python venv を作成し、pytorch などの依存関係を解決した。Docker は使っていない（軽量 venv で進める方針）。",
        "Experiment Execution": "生成された訓練/推論スクリプトを実行し、stdout/stderr を構造化キャプチャ。56 秒で完走。",
        "Result Verification": "Claude が論文の Table から数値主張を抽出し、実行結果の metrics と ±5% 許容で比較した。",
    }

    stages = []
    for s in d.get("stages", []) or []:
        if isinstance(s, dict):
            name = s.get("name", "")
            stages.append({
                "name": name,
                "success": bool(s.get("success", False)),
                "duration": float(s.get("duration", 0) or 0),
                "message": s.get("message", ""),
                "jp_caption": stage_jp.get(name, ""),
            })

    # claim status を日本語に翻訳
    status_jp = {
        "passed": "✓ 一致 — 論文の数値と ±5% 以内で一致",
        "failed": "✗ 不一致 — 論文の数値と乖離",
        "untested": "未検証 — 実行出力に該当 metric が見つからず照合できなかった",
    }

    claims = []
    for c in d.get("claims", []) or []:
        if not isinstance(c, dict):
            continue
        desc_raw = c.get("description", "")
        # description は Python の dict を str() 化したもの。ast で安全に構造化
        parsed = {}
        if isinstance(desc_raw, str) and desc_raw.startswith("{"):
            try:
                parsed = ast.literal_eval(desc_raw)
            except Exception:
                parsed = {}
        status = c.get("status", "")
        reason_en = c.get("reason", "") or ""

        # reason の英語を簡単な日本語に翻訳
        reason_jp = ""
        m = re.match(r"Metric '([^']+)' not found in execution output", reason_en)
        if m:
            reason_jp = f"実行出力の中に '{m.group(1)}' という metric が見つからなかった（FID 評価コードが Stage 4 で起動されていないか、出力フォーマットが違う）"
        elif reason_en:
            reason_jp = reason_en  # fallback

        claims.append({
            "description_raw": desc_raw,
            "metric": parsed.get("metric", ""),
            "value": parsed.get("value", ""),
            "dataset": parsed.get("dataset", ""),
            "model_variant": parsed.get("model_variant", ""),
            "table": parsed.get("table", ""),
            "comparison": parsed.get("comparison", ""),
            "status": status,
            "status_jp": status_jp.get(status, status),
            "reason": reason_en,
            "reason_jp": reason_jp,
            "expected": c.get("expected"),
            "actual": c.get("actual"),
        })

    # 再現スコアの内訳を集計
    n_passed = sum(1 for c in claims if c["status"] == "passed")
    n_failed = sum(1 for c in claims if c["status"] == "failed")
    n_untested = sum(1 for c in claims if c["status"] == "untested")

    return {
        "title": "Reproduce Pipeline — arXiv URL から再現レポートまで",
        "summary": "5 ステージで論文を end-to-end に再現するパイプライン。Stochastic Interpolants で再現スコア 0.5、合計 161 秒。",
        "paper": {
            "title": pi.get("title", ""),
            "arxiv_id": pi.get("arxiv_id", ""),
            "arxiv_url": d.get("arxiv_url", ""),
            "authors": pi.get("authors", []),
        },
        "reproduction_score": float(d.get("reproduction_score", 0) or 0),
        "total_duration": float(d.get("total_duration", 0) or 0),
        "status": d.get("status", ""),
        "stages": stages,
        "claims": claims,
        "claim_breakdown": {
            "passed": n_passed,
            "failed": n_failed,
            "untested": n_untested,
            "total": len(claims),
            "explanation": (
                f"3 つの数値主張のうち、一致確認できたのは {n_passed} 件、不一致が {n_failed} 件、"
                f"未検証（実行出力に metric が無かった）が {n_untested} 件。"
                "再現スコア 0.5 は '実行は完走したが数値の半分は確認できていない' 状態を表す。"
            ),
        },
        "data_flow": [
            {"step": "入力", "value": "arXiv URL（例: 2310.03725）"},
            {"step": "Stage 1 出力", "value": "論文の主張する数値 + ハイパラ + 構造化メタデータ"},
            {"step": "Stage 2 出力", "value": "Python 実装コード（生成 fallback の場合は Claude が一から書いたもの）"},
            {"step": "Stage 3 出力", "value": "動く venv 環境（pytorch + torchdiffeq 等の依存解決済み）"},
            {"step": "Stage 4 出力", "value": "訓練/推論実行ログ + 出力 metrics（あれば）"},
            {"step": "Stage 5 出力", "value": "claim 検証結果（passed/failed/untested）+ 再現スコア"},
        ],
    }


# ----------------------------------------------------- §4 literature-scout (stub)
def build_literature_scout() -> dict:
    """擬似サンプル — ライブ取得は arXiv 429 / Semantic Scholar 0件のため、代表出力を表示。"""
    return {
        "title": "Literature Scout — 関連論文の自動発見",
        "summary": "arXiv と Semantic Scholar を同時検索し、Claude が研究文脈に対する関連度を判定する CLI ツール。",
        "concept": [
            {"step": 1, "label": "クエリ入力", "detail": '「self-improving ML agents」などの自然言語'},
            {"step": 2, "label": "並列検索", "detail": "arXiv API と Semantic Scholar API を同時に呼び出し"},
            {"step": 3, "label": "Claude による分析", "detail": "進行中の研究コンテキストを渡し、関連度を判定"},
            {"step": 4, "label": "ランク済み出力", "detail": "関連度 0.0〜1.0 と判断理由が付いた論文カード"},
        ],
        "cli_sample": (
            '$ uv run literature-scout "self-improving ML agents" \\\n'
            '    -n 5 -s arxiv -c cs.AI -c cs.LG \\\n'
            '    --context "Building a system that autonomously runs ML experiments..."\n'
            'Searching for: self-improving ML agents\n'
            'Sources: arxiv\n'
            'AI analysis: enabled\n'
            '...'
        ),
        "sample_papers": [
            {
                "title": "Self-Improving LLM Agents at Test-Time",
                "arxiv_id": "2510.07956",
                "relevance": 0.92,
                "reasoning": "メタ最適化と自己改善ループの直接的な競合研究。テスト時の振る舞いに焦点が異なる点が特徴。",
                "abstract_snippet": "テスト時の自己改善を、反復的な精緻化と検証で実現する手法...",
            },
            {
                "title": "Bilevel Optimization for Autoresearch",
                "arxiv_id": "2603.23420",
                "relevance": 0.85,
                "reasoning": "autoresearch エコシステムにおけるメタ最適化の代表例。引用候補。",
                "abstract_snippet": "二段階の autoresearch フレームワークを提案し、5倍の改善を達成...",
            },
            {
                "title": "Negative Result Repository for ML Experiments",
                "arxiv_id": "—",
                "relevance": 0.78,
                "reasoning": "我々の NRR と直接対応する概念。失敗実験の構造化。",
                "abstract_snippet": "構造化された失敗ログにより、複数実行間の重複実験を防止する...",
            },
        ],
        "note": "本日のデモはライブ取得せず代表出力のスタブを表示（arXiv 429 / Semantic Scholar 0件のため）。",
    }


# ---------------------------------------------------------------- Hero overview
def build_overview(pb, si, rp, ls) -> dict:
    def metric(d, key, fallback="—"):
        return d.get(key, fallback) if isinstance(d, dict) else fallback

    def pb_metric():
        its = pb.get("iterations", [])
        if its and isinstance(its[-1], dict):
            return f"{its[-1].get('hierarchical_score', '?'):.1f}%"
        return "—"

    def si_metric():
        return f"best {si.get('best_accuracy', 0):.4f} ({si.get('total_cycles', 0)} cycles)" if si.get("best_accuracy") else "—"

    def rp_metric():
        return f"score {rp.get('reproduction_score', '?')} / {rp.get('total_duration', '?')}s" if "reproduction_score" in rp else "—"

    return {
        "title": "AutoRes — 4 コンポーネント ショーケース",
        "subtitle": "論文を自律的に再現し、改善し、評価する研究エージェント（5/1 ミーティング向け）",
        "components": [
            {
                "id": "paperbench",
                "name": "PaperBench Iter",
                "tagline": "「生成 → 反復改善」で 43.2% → 94.5%",
                "metric": pb_metric(),
                "status": "完成",
            },
            {
                "id": "self-improving",
                "name": "Self-Improving Agent",
                "tagline": "CIFAR-10 CNN を自動で書き換える 24/365 ループ",
                "metric": si_metric(),
                "status": "完成",
            },
            {
                "id": "reproduce",
                "name": "Reproduce Pipeline",
                "tagline": "arXiv URL から再現レポートまで（5 ステージ）",
                "metric": rp_metric(),
                "status": "α版",
            },
            {
                "id": "literature-scout",
                "name": "Literature Scout",
                "tagline": "arXiv + Semantic Scholar + Claude による関連度判定",
                "metric": "CLI ツール",
                "status": "完成",
            },
        ],
        "matrix": [
            {
                "name": "PaperBench Iter",
                "input": "rubric.json + 生成コード",
                "output": "階層スコア / ノード単位の評価",
                "key_finding": "反復改善で +51.3 ポイント",
            },
            {
                "name": "Self-Improving Agent",
                "input": "train.py + データセット",
                "output": "改善された train.py + 精度履歴",
                "key_finding": "毎サイクル改善せず → ロールバックと失敗履歴管理が必要",
            },
            {
                "name": "Reproduce Pipeline",
                "input": "arXiv URL",
                "output": "再現コード + 実行結果 + 主張の検証",
                "key_finding": "5 ステージ中、Code Finding が 56% の時間を占める（90秒 / 161秒）",
            },
            {
                "name": "Literature Scout",
                "input": "自然言語クエリ + 研究コンテキスト",
                "output": "関連度でランクされた論文リスト",
                "key_finding": "Intel（push）と Scout（pull）を使い分ける",
            },
        ],
    }


# --------------------------- §Deep Dive — PaperBench batch ---------------------------
def build_paperbench_batch() -> dict:
    """5 論文 × {baseline, improved} の評価結果を集計。

    BATCH_ROOT/<paper_id>/<variant>/{summary.json, evaluation.json} を読む。
    結果が無い論文は status='not_run' で記録（"進行中" として表示できる）。
    """
    paper_order = [
        ("stochastic-interpolants", "Stochastic Interpolants", 94),
        ("semantic-self-consistency", "Semantic Self-Consistency", 100),
        ("sequential-neural-score-estimation", "Sequential Neural Score Estimation", 123),
        ("mechanistic-understanding", "Mechanistic Understanding (DPO toxicity)", 128),
        ("robust-clip", "Robust CLIP", 146),
    ]
    variants = ["baseline", "improved"]

    papers = []
    for pid, label, nodes in paper_order:
        entry = {"id": pid, "label": label, "nodes_expected": nodes, "variants": {}}
        for v in variants:
            vdir = BATCH_ROOT / pid / v
            slot = {
                "status": "not_run",
                "hierarchical_score": None,
                "simple_average_score": None,
                "num_nodes": None,
                "error": None,
            }
            summary_p = vdir / "summary.json"
            eval_p = vdir / "evaluation.json"
            if summary_p.exists():
                try:
                    s = json.loads(summary_p.read_text())
                    slot["status"] = s.get("status", "unknown")
                    if s.get("evaluation"):
                        e = s["evaluation"]
                        slot["hierarchical_score"] = e.get("hierarchical_score")
                        slot["simple_average_score"] = e.get("simple_average_score")
                        slot["num_nodes"] = e.get("num_nodes")
                        if not e.get("success"):
                            slot["error"] = e.get("error")
                except Exception as ex:
                    slot["error"] = f"summary parse error: {ex}"
            if eval_p.exists() and slot["hierarchical_score"] is None:
                # Fallback: read evaluation.json directly
                try:
                    e = json.loads(eval_p.read_text())
                    slot["hierarchical_score"] = float(e.get("hierarchical_score", 0))
                    slot["simple_average_score"] = float(e.get("simple_average_score", 0))
                    slot["num_nodes"] = e.get("num_nodes_evaluated") or len(e.get("scored_nodes", []))
                    slot["status"] = "completed"
                except Exception as ex:
                    slot["error"] = f"evaluation parse error: {ex}"
            entry["variants"][v] = slot
        # delta 計算
        b = entry["variants"]["baseline"].get("hierarchical_score")
        i = entry["variants"]["improved"].get("hierarchical_score")
        if b is not None and i is not None:
            entry["delta"] = round(i - b, 2)
        else:
            entry["delta"] = None
        papers.append(entry)

    # Summary
    completed = sum(
        1 for p in papers
        if p["variants"]["baseline"]["status"] == "completed"
        and p["variants"]["improved"]["status"] == "completed"
    )
    improved_count = sum(1 for p in papers if (p.get("delta") or 0) > 0)

    return {
        "title": "Reproduce Pipeline Deep Dive — 5 論文での再測定",
        "summary": (
            f"Stochastic Interpolants 1 本で 0.5 だった再現スコアを、4 つのコード改善"
            f"（metric alias / success 判定 / pdfplumber / max_tokens）と 5 論文での再測定で検証する。"
        ),
        "improvements": [
            {
                "id": "metric_alias",
                "name": "metric alias 拡張 (12 → 40+)",
                "description": (
                    "verifier.py / executor.py の metric alias を 12 個から 40+ に拡張。"
                    "FID / FID-50k / LPIPS / SSIM / PSNR / BERTScore / METEOR / CIDEr / pass@k 等を追加。"
                    "substring + regex matching、テーブル形式（| FID | 1.13 |）対応。"
                    "untested の重みも 0.5 → 0.25 に下げて「拾えてない」事実を正直に表す。"
                ),
                "files": [
                    "src/autores_reproduce/verifier.py",
                    "src/autores_reproduce/executor.py",
                ],
            },
            {
                "id": "success_strict",
                "name": "success 判定の厳密化",
                "description": (
                    "executor.py で success_strict フィールド新設。returncode==0 だけでなく "
                    "metric が 1 個以上抽出された AND silent failure pattern (mat1 and mat2 / "
                    "shape mismatch / Traceback 等) が出ていない、を AND 条件に。"
                    "「returncode=0 だが実は失敗」を炙り出す。"
                ),
                "files": ["src/autores_reproduce/executor.py"],
            },
            {
                "id": "pdfplumber",
                "name": "PDF extractor を pdfplumber に切替",
                "description": (
                    "paper_fetcher.py の PyPDF2 を pdfplumber 優先に。page.extract_tables() を "
                    "markdown 化して text に追記、論文 Table 1 / Table 2 の数値（FID 1.13 等）を直接拾える。"
                    "paper_text の truncation を 50000 → 200000 に拡張。PyPDF2 を fallback で残す。"
                ),
                "files": ["src/autores_reproduce/paper_fetcher.py", "pyproject.toml"],
            },
            {
                "id": "max_tokens",
                "name": "code generation max_tokens 緩和",
                "description": (
                    "code_finder.py の Claude API max_tokens を 8192 → 16384 に。"
                    "本格的な prompt 改善は後日、まず cut-off による途切れを緩和。"
                ),
                "files": ["src/autores_reproduce/code_finder.py"],
            },
        ],
        "papers": papers,
        "stats": {
            "total_papers": len(papers),
            "fully_completed": completed,
            "improved_count": improved_count,
        },
        "evaluation_mode": "PaperBench Code-Dev (claude-sonnet-4-20250514 as judge)",
        "note": (
            "本評価は PaperBench Code-Dev mode（生成コードを judge にかける、実行不要、GPU 不要）。"
            "公式 SimpleJudge は GPT-4o だが、我々は claude-sonnet-4 を使用しているため絶対値は公式と直接比較不可。"
            "差分（baseline → improved）が我々の改善効果の指標。"
        ),
    }


def build_pipeline_rethink() -> dict:
    """4 mode (baseline / improved / ara-fixes / rubric-aware) × 5 論文の hierarchical_score を集計。

    BATCH_ROOT/<paper_id>/<variant>/{summary.json,evaluation.json} を読む。
    Pipeline-level rethink experiment (2026-04-30): ARA-提案 fix の検証 + rubric-aware Stage 2。
    """
    paper_order = [
        ("stochastic-interpolants", "Stochastic Interpolants", 94),
        ("semantic-self-consistency", "Semantic Self-Consistency", 100),
        ("sequential-neural-score-estimation", "Sequential Neural Score Estimation", 123),
        ("mechanistic-understanding", "Mechanistic Understanding (DPO toxicity)", 128),
        ("robust-clip", "Robust CLIP", 146),
    ]
    variants = ["baseline", "improved", "ara-fixes", "rubric-aware"]

    def _read_score(vdir: Path):
        slot = {"status": "not_run", "hierarchical_score": None, "simple_average_score": None, "num_nodes": None, "error": None}
        sp = vdir / "summary.json"
        ep = vdir / "evaluation.json"
        if sp.exists():
            try:
                s = json.loads(sp.read_text())
                slot["status"] = s.get("status", "unknown")
                if s.get("evaluation"):
                    e = s["evaluation"]
                    slot["hierarchical_score"] = e.get("hierarchical_score")
                    slot["simple_average_score"] = e.get("simple_average_score")
                    slot["num_nodes"] = e.get("num_nodes")
                    if not e.get("success"):
                        slot["error"] = e.get("error")
            except Exception as ex:
                slot["error"] = f"summary parse error: {ex}"
        if ep.exists() and slot["hierarchical_score"] is None:
            try:
                e = json.loads(ep.read_text())
                slot["hierarchical_score"] = float(e.get("hierarchical_score", 0))
                slot["simple_average_score"] = float(e.get("simple_average_score", 0))
                slot["num_nodes"] = e.get("num_nodes_evaluated") or len(e.get("scored_nodes", []))
                slot["status"] = "completed"
            except Exception as ex:
                slot["error"] = f"evaluation parse error: {ex}"
        return slot

    papers = []
    mode_means = {v: [] for v in variants}
    for pid, label, nodes in paper_order:
        entry = {"id": pid, "label": label, "nodes_expected": nodes, "variants": {}}
        scores = {}
        for v in variants:
            slot = _read_score(BATCH_ROOT / pid / v)
            entry["variants"][v] = slot
            if slot["hierarchical_score"] is not None:
                mode_means[v].append(slot["hierarchical_score"])
                scores[v] = slot["hierarchical_score"]
        # 各論文の最良 mode
        if scores:
            best_v = max(scores, key=scores.get)
            entry["best_variant"] = best_v
            entry["best_score"] = scores[best_v]
        # delta
        if scores.get("baseline") is not None and scores.get("rubric-aware") is not None:
            entry["delta_rubric_vs_baseline"] = round(scores["rubric-aware"] - scores["baseline"], 2)
        if scores.get("improved") is not None and scores.get("ara-fixes") is not None:
            entry["delta_ara_vs_improved"] = round(scores["ara-fixes"] - scores["improved"], 2)
        if scores.get("improved") is not None and scores.get("rubric-aware") is not None:
            entry["delta_rubric_vs_improved"] = round(scores["rubric-aware"] - scores["improved"], 2)
        papers.append(entry)

    means = {v: (round(sum(xs) / len(xs), 2) if xs else None) for v, xs in mode_means.items()}

    # 「再現に求められる 4 つの ought-to」
    ought_to = [
        {
            "key": "rubric-ground",
            "title": "rubric-ground",
            "ja": "再現は要件ツリー (rubric) に直接根拠を持つべき",
            "explain": "judge が見る要件を agent が事前に知らずにコードを書くのは「答えを見ずにテストを通す」のに近い。Stage 2 prompt に rubric の leaf 要件を直接渡すべき。",
            "addressed_by": "rubric-aware mode",
        },
        {
            "key": "decompose",
            "title": "decompose",
            "ja": "再現はタスク単位に分解されるべき",
            "explain": "論文が複数実験を含むなら、生成コードも実験ごとに分かれているべき。1 ファイルに圧縮されると scope failure が起きる。",
            "addressed_by": "ara-fixes / rubric-aware mode (H4 enforcement)",
        },
        {
            "key": "verify",
            "title": "verify",
            "ja": "再現はコード生成だけでは終わらず、要件単位で検証されるべき",
            "explain": "現状 Code-Dev mode は静的 judge のみ。本来は実行 + 数値一致まで検証されるべき (Full mode)。今回 scope 外。",
            "addressed_by": "(out of scope) Full mode 評価で実走が必要",
        },
        {
            "key": "iterate",
            "title": "iterate",
            "ja": "再現は 1 発生成ではなく反復であるべき",
            "explain": "v1 評価 → 失敗 leaf 抽出 → v2 再生成、というループが本来必要。今回 1-pass のみで実装、2-pass は次の一手として明示。",
            "addressed_by": "(partial) 2-pass loop は設計済、本実験では 1-pass のみ評価",
        },
    ]

    # ARA → pipeline mapping (どの ARA-fix がどの mode に組み込まれたか)
    ara_pipeline_map = [
        {"ara_claim": "C-008", "title": "Non-recursive glob in evaluator", "incorporated_in": "ara-fixes / rubric-aware (両 mode に同じ evaluator 修正が効く)", "file": "scripts/evaluate_paperbench.py", "fix": "submission_path.glob → rglob + skip-dir filter"},
        {"ara_claim": "C-010", "title": "Hardcoded paper_id in evaluation.json", "incorporated_in": "ara-fixes / rubric-aware (両 mode)", "file": "scripts/evaluate_paperbench.py", "fix": "--paper-id 引数化、rubric path から auto-derive"},
        {"ara_claim": "H4 + C-011", "title": "Stage 2 prompt scope failure", "incorporated_in": "ara-fixes / rubric-aware", "file": "src/autores_reproduce/code_finder.py", "fix": "「simplify 許可」削除、「ALL tasks / EXACT datasets」を mandatory に"},
        {"ara_claim": "C-007", "title": "Code dir selection bottleneck", "incorporated_in": "(skipped, out of scope)", "file": "—", "fix": "次の一手で対応"},
    ]

    return {
        "papers": papers,
        "variants": variants,
        "mode_means": means,
        "ought_to": ought_to,
        "ara_pipeline_map": ara_pipeline_map,
        "interpretation": {
            "headline": "「細かい修正」(improved) と「パイプラインレベル介入」(ara-fixes / rubric-aware) のどちらがどれだけ動いたか",
            "rubric_aware_design": "Stage 2 prompt に rubric.json の leaf 要件 (重み付き checklist) を直接渡し、Claude に「judge が何を見るか」を事前に教えてからコードを書かせる。これは「答えを見せてからテストを書かせる」test-driven な再現アプローチに対応する。",
            "limit": "今回は 1-pass 評価のみ。2-pass loop (失敗 leaf 抽出 → v2 再生成) は実装済みだがスコープ外で本実験では未起動。",
            "honest_caveat": "Code-Dev mode は静的 judge であり、実行可能性 / 数値一致は検証していない。Full mode (GPU 必要) は次の一手。",
        },
    }


def build_agent_comparison() -> dict:
    """3 主体並列実験 (人間+Claude / ARA 15 skills / ARA + research-prime 123 skills) の比較データを生成。"""
    ARA_RUNS = Path.home() / "unktok/dev/autonomous-research-agent/runs"
    ara_a = ARA_RUNS / "2026-04-30-reproduce-automation-ara"
    ara_p = ARA_RUNS / "2026-04-30-reproduce-automation-prime"

    # H4 per-node breakdown (ARA-a の実機検証結果)
    h4_path = ara_a / "experiments/h4-prompt-fix/eval_h4_results.json"
    h4_nodes = []
    if h4_path.exists():
        h4_data = safe_load(h4_path)
        if h4_data:
            base = h4_data.get("baseline_results", [])
            impr = h4_data.get("h4_results", [])
            for b, i in zip(base, impr):
                req_short = b.get("requirements", "")[:80]
                # 短縮表現のためのラベル
                if "U-Net" in req_short:
                    label = "U-Net architecture"
                elif "ImageNet" in req_short and "validation" in req_short:
                    label = "ImageNet train/val access"
                elif "tiles" in req_short and "0.3" in req_short:
                    label = "Mask: 64 tiles × p=0.3"
                elif "same value for all channels" in req_short:
                    label = "Mask: same value across channels"
                elif "Hadamard" in req_short or "noise" in req_short.lower():
                    label = "Mask: noise injection $x_0=\\xi\\circ x_1+(1-\\xi)\\circ\\zeta$"
                elif "class value" in req_short:
                    label = "Class label channel"
                elif "uniformly sampled" in req_short:
                    label = "Time t ∼ U(0,1)"
                else:
                    label = req_short[:60]
                h4_nodes.append({
                    "label": label,
                    "baseline": b.get("score", 0),
                    "improved": i.get("score", 0),
                })

    # ARA-a が発見したバグ (4 件)
    ara_a_bugs = [
        {
            "id": "C-008",
            "title": "Non-recursive glob in evaluate_paperbench.py",
            "summary": "submission/<subdir>/ にあるコードが評価対象から漏れる。official repo で 0% スコアの主因。",
            "impact": "stochastic-interpolants の \"untested\" 比率が高かった一因と整合 (submission/training/inpainting_512.py が glob で拾われていなかった)。",
        },
        {
            "id": "C-007",
            "title": "Code dir selection bottleneck",
            "summary": "official repo に複数候補ディレクトリがあるとき、誤って空 / wrap dir を選んで 0% に落ちる。",
            "impact": "Stage 2 以前 (= Stage 1 のディレクトリ抽出) のバグ。修正すれば baseline が底上げされる。",
        },
        {
            "id": "C-010",
            "title": "paper_id metadata bug",
            "summary": "全 evaluation.json で paper_id=\"stochastic-interpolants\" が hardcoded、どの論文を評価しても同じ値が入る。",
            "impact": "現状の集計で「どの論文の数値か」を別 path から復元する必要があり、追跡コストが上がる。",
        },
        {
            "id": "C-011",
            "title": "Stage 2 prompt が \"simplify\" 指示で scope failure 誘発",
            "summary": "現行 prompt の \"simplify\" / \"standard datasets\" 指示が、論文固有のタスクや dataset を捨てる方向に効く。Stage 1 が正しく抽出していても Stage 2 で scope が縮む。",
            "impact": "H4 仮説 (targeted prompt fix) の根拠。+24.3pp の改善はこの指示文の修正によるもの。",
        },
    ]

    # ARA-p の failure taxonomy (4 クラスタ)
    ara_p_taxonomy = [
        {"cluster": "GeneratedCodeSyntaxError", "pct": 40, "papers": "semantic-self-consistency, mechanistic-understanding", "cause": "Claude 生成コードに未終端 string literal 等"},
        {"cluster": "CLIArgumentMismatch", "pct": 20, "papers": "robust-clip", "cause": "executor が --device cpu を subcommand 前に注入する構造的 mismatch"},
        {"cluster": "NumpyVersionIncompatibility", "pct": 20, "papers": "sequential-neural-score-estimation", "cause": "numpy 2.0 で StringDType 削除"},
        {"cluster": "EvaluationMetadataBug", "pct": 20, "papers": "sequential-neural-score-estimation", "cause": "evaluation.json の paper_id 誤記 (= ARA-a の C-010 と同件)"},
    ]

    # 3 主体サマリ
    subjects = [
        {
            "id": "human",
            "label": "主体 A: 人間 + Claude",
            "harness": "Claude Code 標準",
            "skills": "—",
            "scope": "5 論文 × 2 variants 全 evaluation",
            "improvement_metric": "5 論文 mean +3.6 pt",
            "improvement_value": 3.6,
            "improvement_unit": "pt",
            "bugs_found": 0,
            "claims": 0,
            "char": "測定インフラの整備が中心、生成コード本体は動かず",
        },
        {
            "id": "ara-a",
            "label": "主体 B: ARA (15 skills)",
            "harness": "ARA sustainer (2 cycle × 4 phase)",
            "skills": "ARA 同梱 15 skills",
            "scope": "1 論文 × rubric subset 7 ノード",
            "improvement_metric": "subset で 15.7% → 40.0% (+24.3 pp)",
            "improvement_value": 24.3,
            "improvement_unit": "pp",
            "bugs_found": 4,
            "claims": 12,
            "char": "★ 既存 reproduce repo のバグ 4 件発見 + H4 仮説実機検証",
        },
        {
            "id": "ara-p",
            "label": "主体 C: ARA + research-prime (123 skills)",
            "harness": "ARA sustainer (cycle 1 半、harness 早期 exit)",
            "skills": "research-prime: ARA 16 + Orchestra 95 + new/ 12 = 123 skills",
            "scope": "Researcher + Evaluator のみ、cycle 2 未到達",
            "improvement_metric": "数値結果なし (定性のみ)",
            "improvement_value": 0,
            "improvement_unit": "—",
            "bugs_found": 0,
            "claims": 6,
            "char": "failure 4 クラスタ分類 + Layer 0 validator 2 件 (CLIIntrospector が F2 実証)",
        },
    ]

    # Self-Evaluator が flag した誇張 (信頼性の自己校正)
    self_critique = [
        {"subject": "ara-a", "flagged": "claim-003 confidence 0.75 過大 — fix フェーズの F2 Evidence なし"},
        {"subject": "ara-a", "flagged": "H4 fix を 5 論文に展開していない、+24.3pp は subset のみ"},
        {"subject": "ara-a", "flagged": "eval_h4.py の inpainting detection regex バグで breakdown が意味なし"},
        {"subject": "ara-p", "flagged": "実験ログファイル未保存、再現性に欠ける (timestamp + path のみ)"},
        {"subject": "ara-p", "flagged": "skill_validation Ledger エントリ 0 件 — research-question.md の必須要件未充足"},
    ]

    return {
        "subjects": subjects,
        "ara_a_bugs": ara_a_bugs,
        "h4_nodes": h4_nodes,
        "h4_summary": {
            "baseline_avg": round(sum(n["baseline"] for n in h4_nodes) / max(len(h4_nodes), 1), 1),
            "improved_avg": round(sum(n["improved"] for n in h4_nodes) / max(len(h4_nodes), 1), 1),
            "delta_pp": 24.3,
            "judge": "claude-sonnet-4-6",
            "n_nodes": len(h4_nodes),
            "paper": "stochastic-interpolants",
        },
        "ara_p_taxonomy": ara_p_taxonomy,
        "ara_p_cli_introspector_example": {
            "before": "python cli.py --device cpu eval --weights ./weights",
            "after": "python cli.py eval --device cpu --weights ./weights",
            "explain": "robust-clip の cli は subcommand (eval/build) の後に flag を取る構造。executor が --device cpu を subcommand 前に注入していたため argparse error。CLIIntrospector が --help を parse して構造を学習し、正しい順序で組み立てる。",
        },
        "self_critique": self_critique,
        "meta_conclusion": "+3.6 pt / バグ 0 件 (主体 A) と +24.3 pp / バグ 4 件 (主体 B) の比較は、「人間が改善案を考えるより agent にループを閉じさせる方が深い改善が出る」という仮説の部分実証。ただし主体 B の +24.3pp は 1 論文 × 7 ノード subset の結果。",
    }


def main():
    print("[build-data] start")
    pb = build_paperbench()
    si = build_self_improving()
    rp = build_reproduce()
    ls = build_literature_scout()
    ov = build_overview(pb, si, rp, ls)
    pbb = build_paperbench_batch()
    ac = build_agent_comparison()
    pr = build_pipeline_rethink()

    write_json("paperbench.json", pb)
    write_json("self-improving.json", si)
    write_json("reproduce.json", rp)
    write_json("literature-scout.json", ls)
    write_json("overview.json", ov)
    write_json("paperbench-batch.json", pbb)
    write_json("agent-comparison.json", ac)
    write_json("pipeline-rethink.json", pr)
    print(f"[build-data] done @ {NOW}")


if __name__ == "__main__":
    main()
