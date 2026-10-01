#!/usr/bin/env python3
"""Render report figures from preserved CSVs; do not rerun simulations."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--one-path-only", action="store_true", help="Update only the condition-comparison figure")
    args = parser.parse_args()
    root = args.artifacts_root.resolve()
    out = root / "report-visuals-2026-10-01"
    out.mkdir(exist_ok=True)
    font_paths = [Path("/mnt/c/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/malgun.ttf")]
    for font_path in font_paths:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
            break
    plt.rcParams.update({"font.size": 12, "axes.unicode_minus": False,
                        "svg.fonttype": "none", "svg.hashsalt": "keti-week1-report-20261001"})
    sweep_path = root / "week1-2026-10-01/w1.csv"
    analysis_path = root / "one-path-analysis-2026-10-01/all_experiments.csv"
    sweep = pd.read_csv(sweep_path)
    analysis = pd.read_csv(analysis_path)
    assert len(sweep) == 210 and len(analysis) == 39
    assert not sweep.duplicated(["scenario", "scheduler", "seed"]).any()
    assert not analysis.duplicated(["case", "seed"]).any()

    scenarios = ["dominating", "competing", "degrade"]
    schedulers = sweep[["scheduler", "name"]].drop_duplicates().set_index("scheduler").loc[[0, 1, 2, 3, 4, 6, 5]].reset_index()
    labels = [name.replace("(new)", "\n(new)") for name in schedulers["name"]]
    full = np.zeros((3, 7), dtype=int)
    done = np.zeros_like(full)
    completion_groups = []
    for i, scenario in enumerate(scenarios):
        for j, row in enumerate(schedulers.itertuples(index=False)):
            group = sweep[(sweep.scenario == scenario) & (sweep.scheduler == row.scheduler)]
            assert len(group) == 10
            full[i, j] = int((group.rx_app == group["size"]).sum())
            done[i, j] = int((group.done == 1).sum())
            assert full[i, j] <= done[i, j]
            completion_groups.append({"scenario": scenario, "scheduler": row.name,
                                      "runs": 10, "full_receive": int(full[i, j]),
                                      "done": int(done[i, j])})
    assert int(full.sum()) == 181 and int(done.sum()) == 191
    fig, ax = plt.subplots(figsize=(11.4, 4.6))
    fig.subplots_adjust(left=0.15, right=0.98, top=0.73, bottom=0.25)
    ax.imshow(full, cmap="YlGnBu", vmin=0, vmax=10, aspect="auto")
    ax.set_xticks(range(7), labels, fontsize=11)
    ax.set_yticks(range(3), scenarios, fontsize=12)
    ax.tick_params(length=0, pad=10)
    for i in range(3):
        for j in range(7):
            ax.text(j, i, f"{full[i, j]} / {done[i, j]}", ha="center", va="center",
                    fontsize=17, weight="bold", color="white" if full[i, j] >= 7 else "#143b51")
    ax.set_xticks(np.arange(-0.5, 7, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.05, 0.92, "210회 결과 · 전체 수신과 완료 처리 구분", fontsize=19, weight="bold", color="#143b51")
    fig.text(0.05, 0.82, "각 칸: 전체 수신 / 완료 처리 (각 10회)  ·  배경색: 전체 수신 횟수", fontsize=12, color="#526371")
    fig.text(0.05, 0.09, "전체 수신 181/210  |  완료 처리 191/210  |  완료 처리 후 부족 10회 + 미완료 19회", fontsize=12, color="#143b51")
    fig.text(0.05, 0.025, "완료 처리(done=1)는 목표-3,000B 기준. 바이트 미달 29회는 제공 기준 CSV에도 존재.", fontsize=10, color="#526371")
    if args.one_path_only:
        plt.close(fig)
    else:
        save(fig, out, "completion_counts")

    cases = [
        ("baseline-fixed", "고정 5Mbps · 50ms · Peekaboo", "#51768d"),
        ("scheduler-RR-only", "고정 5Mbps · 50ms · RR", "#51768d"),
        ("delay-50-55-only", "고정 5Mbps · 50~55ms · RR", "#51768d"),
        ("rate-5-6-only", "5~6Mbps · 50ms · RR", "#2b719e"),
        ("reference-full-size", "5~6Mbps · 50~55ms · RR (원본 링크 조건)", "#24826b"),
    ]
    summaries = []
    fig, ax = plt.subplots(figsize=(11.4, 5.7))
    fig.subplots_adjust(left=0.48, right=0.96, top=0.76, bottom=0.23)
    ax.axvspan(8.5, 9.0, color="#e4f3eb", zorder=0)
    ax.axvline(9.0, color="#418568", linestyle="--", linewidth=1.2)
    for i, (case, label, color) in enumerate(cases):
        group = analysis[analysis["case"] == case]
        times = group.fct_full_s.to_numpy()
        assert (group.rx_app == group["size"]).all() and (group["size"] == 5242880).all()
        passes = int(((group.fct_full_s >= 8.5) & (group.fct_full_s <= 9.0)).sum())
        n = len(group)
        mean = float(times.mean())
        ax.hlines(i, times.min(), times.max(), color=color, linewidth=4, zorder=2)
        ax.scatter(times, np.repeat(i, n), s=26, color=color, alpha=0.35, zorder=3)
        ax.scatter([mean], [i], s=85, color=color, edgecolor="white", zorder=4)
        ax.text(9.68, i, f"{mean:.4f}초\n전체 수신 {n}/{n}", va="center", color=color, fontsize=11)
        summaries.append({"case": case, "runs": n, "full_receive": n,
                          "time_range_pass": passes, "fct_full_mean_s": mean,
                          "fct_full_min_s": float(times.min()), "fct_full_max_s": float(times.max())})
    ax.set_yticks(range(len(cases)), [c[1] for c in cases], fontsize=11)
    ax.set_ylim(4.65, -0.65)
    ax.set_xlim(8.4, 10.12)
    ax.set_xticks([8.5, 9.0, 9.5])
    ax.set_xlabel("앱 전송 시작 → 목표 바이트 전체 수신 (초)", fontsize=11, labelpad=10)
    ax.grid(axis="x", color="#d8e1e6", linestyle=":")
    ax.tick_params(axis="y", length=0, pad=12)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    fig.text(0.05, 0.92, "단일 경로 · 링크 속도 조건별 전송 시간 비교", fontsize=18, weight="bold", color="#143b51")
    fig.text(0.05, 0.82, "음영: 요청서 참고 시간 8.5~9.0초  |  점: 평균 · 개별 seed  |  선: 최솟값~최댓값", fontsize=11, color="#526371")
    fig.text(0.05, 0.09, "표시한 모든 실행: 5,242,880B 전체 수신 · 손실률 0 · OLIA", fontsize=11, color="#143b51")
    fig.text(0.05, 0.025, "고정 5Mbps와 원본 링크 조건 5~6Mbps를 각각 지정해 측정", fontsize=10, color="#526371")
    save(fig, out, "one_path_comparison")

    record = {
        "date_kst": "2026-10-02", "simulation_rerun": False,
        "inputs": [{"path": str(path.relative_to(root)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in [sweep_path, analysis_path]],
        "completion": {"runs": 210, "full_receive": 181, "done": 191, "groups": completion_groups},
        "one_path_plotted_groups": summaries,
        "definitions": {"full_receive": "rx_app == size", "done": "source code completion flag",
                        "one_path_fct": "fct_full_s; not threshold FCT"},
    }
    (out / "figure_data.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"full_receive": int(full.sum()), "done": int(done.sum()),
                      "one_path": summaries, "svg_bytes": {p.name: p.stat().st_size for p in out.glob("*.svg")}}, ensure_ascii=False))


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=170, facecolor="white")
    fig.savefig(out / f"{name}.svg", facecolor="white", metadata={"Date": "2026-10-02"})
    svg_path = out / f"{name}.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)


if __name__ == "__main__":
    main()
