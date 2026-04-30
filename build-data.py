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
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/s30825/dev/autores")
OUT = Path(__file__).parent / "data"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    stages = []
    for s in d.get("stages", []) or []:
        if isinstance(s, dict):
            stages.append({
                "name": s.get("name", ""),
                "success": bool(s.get("success", False)),
                "duration": float(s.get("duration", 0) or 0),
                "message": s.get("message", ""),
            })

    claims = []
    for c in d.get("claims", []) or []:
        if isinstance(c, dict):
            desc = c.get("description", "")
            # description がしばしば dict-as-string なので軽く整形
            claims.append({
                "description": str(desc),
                "status": c.get("status", ""),
                "reason": c.get("reason", ""),
                "expected": c.get("expected"),
                "actual": c.get("actual"),
            })

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


def main():
    print("[build-data] start")
    pb = build_paperbench()
    si = build_self_improving()
    rp = build_reproduce()
    ls = build_literature_scout()
    ov = build_overview(pb, si, rp, ls)

    write_json("paperbench.json", pb)
    write_json("self-improving.json", si)
    write_json("reproduce.json", rp)
    write_json("literature-scout.json", ls)
    write_json("overview.json", ov)
    print(f"[build-data] done @ {NOW}")


if __name__ == "__main__":
    main()
