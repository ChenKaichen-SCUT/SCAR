"""Pair revised runs with archived results without rerunning any comparator."""
import argparse
from collections import defaultdict, Counter
import json
from pathlib import Path
import statistics

from scar.environment import restore, state_digest
from scar.experiments.analyze import SUCCESS, METRICS, paired_bootstrap, stage_of, write_csv
from scar.io import atomic_json, digest
from scar.providers.deepseek import BudgetLedger


def pair_key(row):
    stage = stage_of(row)
    return (stage, row["id"]) if stage == "diagnostic" else (stage, row["game"], row["seed"])


def comparisons(rows):
    grouped = defaultdict(dict)
    for row in rows:
        if row["status"] not in SUCCESS or stage_of(row) not in {"long", "cost", "diagnostic"}:
            continue
        key = pair_key(row)
        if row["algorithm"] in grouped[key]:
            raise ValueError(f"Duplicate comparator for {key}: {row['algorithm']}")
        grouped[key][row["algorithm"]] = row
    result = []
    for stage in ["diagnostic", "long", "cost"]:
        methods = sorted({r["algorithm"] for r in rows if stage_of(r) == stage} - {"SCARV2Agent"})
        for method in methods:
            for game in ["ALL", "remnant", "mark", "metropolis"]:
                matches = [(g["SCARV2Agent"], g[method]) for k, g in grouped.items()
                           if k[0] == stage and "SCARV2Agent" in g and method in g
                           and (game == "ALL" or g[method]["game"] == game)]
                for metric in METRICS:
                    measured = [(a, b) for a, b in matches if a.get(metric) is not None and b.get(metric) is not None]
                    if not measured:
                        continue
                    stats = paired_bootstrap([float(a[metric]) - float(b[metric]) for a, b in measured],
                                             [a.get("family", (a["game"], a["seed"])) for a, b in measured])
                    result.append(dict(stage=stage, game=game, comparison="SCARV2Agent - " + method,
                                       metric=metric, historical_baseline=True, **stats))
    return result


def aggregates(rows):
    groups = defaultdict(list)
    for row in rows:
        for game in ["ALL", row["game"]]:
            groups[stage_of(row), game, row["algorithm"]].append(row)
    output = []
    for (stage, game, algorithm), group in sorted(groups.items()):
        valid = [r for r in group if r["status"] in SUCCESS]
        entry = dict(stage=stage, game=game, algorithm=algorithm, n=len(group), completed=len(valid))
        for metric in METRICS:
            values = [float(r[metric]) for r in valid if r.get(metric) is not None]
            entry[metric + "_mean"] = statistics.mean(values) if values else None
            entry[metric + "_median"] = statistics.median(values) if values else None
        entry["interceptions"] = sum(r.get("interceptions", 0) for r in valid)
        entry["false_blocks"] = sum(r.get("false_blocks", 0) for r in valid)
        entry["pooled_fbr"] = entry["false_blocks"] / entry["interceptions"] if entry["interceptions"] else None
        output.append(entry)
    return output


def analyze(runtime, historical, output, report):
    runtime, historical, output = Path(runtime), Path(historical), Path(output)
    frozen = json.loads((output / "freeze.json").read_text())
    archived = json.loads((output / "archived_comparators.json").read_text())
    assert digest(archived) == frozen["archived_comparators_sha256"]
    current = [json.loads(p.read_text()) for p in sorted((runtime / "runs").glob("*/summary.json"))]
    expected = frozen["new_tasks"]
    counts = Counter(stage_of(r) for r in current)
    if dict(counts) != expected or any(r["status"] not in SUCCESS for r in current):
        raise RuntimeError("Incomplete revision; retain incomplete runs and do not generate a final performance claim")
    clean = [{k: v for k, v in r.items() if k not in {"history", "witness", "initial_snapshot", "goal"}} for r in current]
    rows = archived + clean
    atomic_json(output / "all_summaries.json", clean)
    write_csv(output / "all_runs.csv", [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in clean])
    aggregate, paired = aggregates(rows), comparisons(rows)
    for name, data in [("comparison_aggregate", aggregate), ("paired_comparisons", paired)]:
        atomic_json(output / (name + ".json"), data)
        write_csv(output / (name + ".csv"), data)
    # Cross-round pairing audit compares actual saved environments, not just seed labels.
    revised = {pair_key(r): r for r in current if stage_of(r) != "smoke"}
    new_digests, checks = {}, []
    for prior in archived:
        new = revised[pair_key(prior)]
        if new["task_id"] not in new_digests:
            new_digests[new["task_id"]] = state_digest(restore(runtime / "runs" / new["task_id"] / "initial.pkl"))
        equal = new_digests[new["task_id"]] == state_digest(restore(historical / "runs" / prior["task_id"] / "initial.pkl"))
        checks.append({"new_task": new["task_id"], "archived_task": prior["task_id"], "same_initial_state": equal})
    atomic_json(output / "cross_round_pairing.json", {"checked": len(checks), "mismatches": sum(not c["same_initial_state"] for c in checks), "checks": checks})
    if not all(c["same_initial_state"] for c in checks):
        raise RuntimeError("Cross-round initial state mismatch")
    # A harmful replacement proxy: accepted candidate replaced by a rejected action.
    interventions, examples = [], []
    for method in ["SCARAgent", "SCARV2Agent", "SimpleFailureRecovery"]:
        for stage in ["diagnostic", "long", "cost"]:
            counts = Counter()
            for row in rows:
                if row["algorithm"] != method or stage_of(row) != stage:
                    continue
                root = runtime if method == "SCARV2Agent" else historical
                for path in sorted((root / "runs" / row["task_id"]).glob("steps/*/transition.json")):
                    tr = json.loads(path.read_text())
                    if not tr.get("intercepted"):
                        continue
                    counts["interceptions"] += 1
                    accepted = not tr["proposed_truth"]["semantic_rejection"]
                    counts["accepted_candidate_intercepted"] += accepted
                    harmful = accepted and tr["semantic_rejection"]
                    counts["accepted_to_rejected"] += harmful
                    if harmful and sum(e["algorithm"] == method and e["stage"] == stage for e in examples) < 3:
                        examples.append({"algorithm": method, "stage": stage, "task": row["task_id"],
                                         "index": tr["index"], "proposed": tr["proposed_action"],
                                         "executed": tr["executed_action"], "reason": tr["reason"],
                                         "feedback": tr["action_rule_feedback"]})
            interventions.append(dict(algorithm=method, stage=stage, **counts))
    atomic_json(output / "intervention_outcomes.json", interventions)
    atomic_json(output / "intervention_examples.json", examples)
    cost = BudgetLedger(runtime / "budget.sqlite", 20).total()
    accounting = {"cost_before_revision_usd": frozen["cost_before_revision_usd"], "project_total_usd": cost,
                  "incremental_conservative_cost_usd": cost - frozen["cost_before_revision_usd"],
                  "requests": sum(r["api_calls"] for r in current), "failed_requests": sum(r["failed_requests"] for r in current),
                  "http_429": sum(r["http_429"] for r in current), "new_runs": len(current), "reused_runs": len(archived)}
    atomic_json(output / "revision_accounting.json", accounting)
    replay = json.loads((output / "replay_audit.json").read_text())
    if replay["failed"] or replay["initial_state_mismatches"]:
        raise RuntimeError("Replay audit failed")
    generate_report(report, aggregate, paired, accounting, replay, interventions)
    print(json.dumps(accounting))


def generate_report(path, aggregate, paired, accounting, replay, interventions):
    def get(stage, method, game="ALL"):
        return next(r for r in aggregate if (r["stage"], r["algorithm"], r["game"]) == (stage, method, game))
    def pct(value):
        return "—" if value is None else f"{value * 100:.2f}%"
    def num(value):
        return "—" if value is None else f"{value:.3f}"
    v2, v1, simple = [get("diagnostic", m) for m in ["SCARV2Agent", "SCARAgent", "SimpleFailureRecovery"]]
    methods = ["ShortTermMemoryAgent", "VanillaRAGAgent", "LongContextAgent", "SimpleFailureRecovery", "SCARAgent", "SCARV2Agent"]
    lines = ["# SCAR 修订版回归实验报告", "",
        "本轮仅运行修订后的 SCAR。四个基线与 SCAR 第一版均直接复用上一轮已完成的记录；"
        "长程与费用约束比较固定为每游戏种子 101、最多 200 步。所有结果均来自实际执行。", "",
        "本报告是已见案例上的回归比较：修订方向来自第一轮负面结果，不能把同一批诊断案例再称作未见测试。"
        "每游戏只有一个配对种子，远程模型没有固定输出种子，服务漂移和采样随机性无法排除；不据此作确定的因果或总体显著性结论。", "",
        "## 修订与冻结", "",
        "四个模块保持完整。公开反馈诊断、条件失败记忆及在线证据更新沿用第一版；修复触发改为检查当前候选，"
        "仅在已知规则阻止该候选或公开动作签名不合法时介入。最近一次失败本身不触发接管；"
        "条件变化和冷却只放行策略自行提出的重试，不主动替换其他候选。队列只服务于同一受阻目标，"
        "逐步重新检查位置、时效、语法与失败规则。每步最多一次额外修复生成；无有效方案时显式验证合法原候选，"
        "语法始终不合法则中止并记录错误，不静默改成 wait。", "",
        "模型、温度、768 输出 token 上限、基础 STM prompt、5 步记忆、评分及成本口径与第一轮一致。"
        "冻结记录见 `results/v2/freeze.json`，旧记录清单见 `archived_comparators.json`。"
        "第一轮核心源码哈希保持不变，修订放在独立 `scar_v2/` 包；首次新版 API 调用前冻结。", "",
        "## 诊断恢复", "",
        "复用 72 个可恢复案例、36 个 family，包含自然轨迹母案例及引擎构造的条件释放变体；"
        "A/D 标签重叠，C 类型缺失，样本覆盖限制与第一轮相同。基线未运行 LongContext 诊断，因此此处也不补跑。", "",
        "| 方法 | n | Recovery@10 | Recovery@20 | 重复语义失败率 | FBR（合并计数） | 每例费用 | 每例请求 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for method in methods:
        if method == "LongContextAgent":
            continue
        r = get("diagnostic", method)
        lines.append(f"| {method} | {r['completed']} | {pct(r['recovery_at_10_mean'])} | {pct(r['recovery_at_20_mean'])} | {pct(r['semantic_riar_mean'])} | {r['false_blocks']}/{r['interceptions']} ({pct(r['pooled_fbr'])}) | ${r['cost_usd_mean']:.6f} | {r['api_calls_mean']:.2f} |")
    lines += ["", "Recovery@20 配对差值按 family 聚类 Bootstrap（10,000 次）；区间只描述这批已见案例。", "",
              "| 历史比较方法 | 新版差值（百分点） | 95% 区间（百分点） |", "|---|---:|---:|"]
    for p in paired:
        if p["stage"] == "diagnostic" and p["game"] == "ALL" and p["metric"] == "recovery_at_20":
            lines.append(f"| {p['comparison'].split(' - ')[1]} | {p['mean_difference']*100:+.2f} | [{p['ci95_low']*100:.2f}, {p['ci95_high']*100:.2f}] |")
    lines += ["", "FBR 分母是被干预的候选数；没有干预时为未定义，不记作 0。其真值来自独立环境副本的拒绝反馈标签，"
              "不能保证检测到所有无进展行为。分类恢复、严格目标验证重试、恢复成本与在线模块事件另见同目录 CSV/JSON。", ""]
    for stage, title in [("long", "200 步长程"), ("cost", "每局 $0.15 实际费用上限")]:
        lines += [f"## {title}", "", "每游戏一个种子 101；费用实验另行实际执行，请求前预留费用，最多仍为 200 步。", "",
                  "| 方法 | remnant 主线奖励 | mark 主线奖励 | metropolis 主线奖励 | 均值 / 中位数 | 平均步数 | 平均费用 |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for method in methods:
            r = get(stage, method)
            game_rewards = [get(stage, method, g)["main_quest_reward_mean"] for g in ["remnant", "mark", "metropolis"]]
            lines.append(f"| {method} | {game_rewards[0]:g} | {game_rewards[1]:g} | {game_rewards[2]:g} | {r['main_quest_reward_mean']:.2f} / {r['main_quest_reward_median']:.2f} | {r['steps_mean']:.1f} | ${r['cost_usd_mean']:.6f} |")
        lines += ["", "| 新版相对方法 | 主线奖励均值配对差 | 3 个游戏配对 Bootstrap 95% 区间 |", "|---|---:|---:|"]
        for p in paired:
            if p["stage"] == stage and p["game"] == "ALL" and p["metric"] == "main_quest_reward":
                lines.append(f"| {p['comparison'].split(' - ')[1]} | {p['mean_difference']:+.3f} | [{p['ci95_low']:.3f}, {p['ci95_high']:.3f}] |")
        r = get(stage, "SCARV2Agent")
        lines += ["", f"新版通关率 {pct(r['completion_mean'])}；引擎 IAR {pct(r['iar_mean'])}，语义失败率 {pct(r['semantic_failure_rate_mean'])}，"
                  f"重复语义失败率 {pct(r['semantic_riar_mean'])}。平均输入 / 输出 token：{num(r['input_tokens_mean'])} / {num(r['output_tokens_mean'])}；"
                  f"平均请求 {num(r['api_calls_mean'])}，决策累计耗时 {num(r['decision_wall_seconds_mean'])} 秒。"
                  "单游戏单种子无可估计的种子间不确定性；三个游戏上的区间极粗，不能解释为更多种子上的置信保证。", ""]
    lines += ["## 干预风险与规则验证", "", "合法候选被替换为拒绝动作是有害替换的代理指标，不等同于全部由记忆导致的因果错误。", "",
              "| 方法 | 阶段 | 合法候选 → 拒绝动作次数 |", "|---|---|---:|"]
    for r in interventions:
        lines.append(f"| {r['algorithm']} | {r['stage']} | {r.get('accepted_to_rejected',0)} |")
    lines += ["", "独立冻结 CRA 沿用第一轮对未改动记忆判定模块的审计（14.23%）；它不能代表新版轨迹新学规则的独立验证。"
              "新版在线 CRA 仅为探索性检查，详见汇总表，不与独立 CRA 混用。", "",
              "## 完整性、费用与数据位置", "",
              f"新增 {accounting['new_runs']} 组全部有效结束（含 3 组开发 smoke）；复用 {accounting['reused_runs']} 条历史比较记录。"
              f"跨轮 318 对实际初始状态全部匹配。抽查 {replay['checked']} 个动作全部精确重放，"
              f"{replay['initial_states_checked']} 个初始状态均与冻结源一致。", "",
              f"本轮请求 {accounting['requests']} 次，其中失败请求 {accounting['failed_requests']} 次、HTTP 429 共 {accounting['http_429']} 次。"
              f"新增保守费用 ${accounting['incremental_conservative_cost_usd']:.6f}，项目累计 ${accounting['project_total_usd']:.6f}，共享原 $20 上限。"
              "统一采用第一轮冻结定价，用于比较与预算管理，不等于账户账单。", "",
              "原始新版轨迹、请求审计及完整快照位于服务器 `/root/scar_workspace/runtime_v2`；历史数据位于 `runtime`。"
              "GitHub 只发布我们的代码、配置、测试及结果分析文件，不发布下载依赖、模型或原始 pickle。", "",
              "## 研究判断", "",
              f"新版 Recovery@20 {pct(v2['recovery_at_20_mean'])}，第一版 {pct(v1['recovery_at_20_mean'])}，简单恢复 {pct(simple['recovery_at_20_mean'])}；"
              f"新版合并 FBR {pct(v2['pooled_fbr'])}。这次结果应首先用于检验修复是否减少有害干预。"
              "最终 GO / PARTIAL / NO-GO 判断需要结合逐游戏结果和上述区间人工审阅；本自动生成稿不预设有效结论。", ""]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--historical-runtime", required=True)
    parser.add_argument("--output", default="results/v2")
    parser.add_argument("--report", default="reports/修订版实验报告.md")
    args = parser.parse_args()
    analyze(args.runtime, args.historical_runtime, args.output, args.report)
