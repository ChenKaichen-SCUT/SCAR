# Stage29 复现入口

[总报告](Stage29实验报告.md) · [生命周期](Recovery生命周期统计.md) · [分类](失败轨迹分类.md) · [纸面反事实与原生探针](GoalStack反事实分析.md) · [实现判断](HierarchicalGoalStack实现判断.md)

使用既有Python环境及冻结AgentOdyssey，设置与Stage28相同的 `AGENTODYSSEY_ROOT`、`PYTHONPATH`、`PYTHONHASHSEED=0` 和 `HF_HUB_OFFLINE=1`。所有Stage29程序使用网络禁用器，没有付费provider入口。

```bash
python -m scar_stage29.extract
python -m scar_stage29.annotations
python -m scar_stage29.stacks
python -m scar_stage29.native_probe
python -m scar_stage29.summarize
python -m scar_stage29.verify
python -m scar_stage29.report
python -m scar_stage29.audit
```

annotations.py 是透明的语义标注及证据动作号，统计代码不将其伪装成自动真值；修改标注后须重新汇总。native_probe 只在隔离副本重放保存响应及2个候选环境动作。没有Oracle Goal Stack模型续跑。

action_audit.jsonl.gz 为完整3116动作出现位置；goal_segments.json 为目标区间；lifecycle_annotations.json 为原始证据；paper_goal_stacks.json 为限定知识截止点的纸面树；public_knowledge_context_audit.json 为配方/引文的实际输入可见性；evidence_index.jsonl.gz 将绝对动作号映射到原文件行号和请求ID。不同Original后缀相互重叠，不作独立样本推断。

旧Stage28数据已做完整原生回放，Stage29验证其冻结哈希并复用收据；新增局部探针单独精确重放。audit的私钥排除扫描仅在本地私钥存在时执行，公开复算无需密钥或模型服务。下载依赖不上传。
