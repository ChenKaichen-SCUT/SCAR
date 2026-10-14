# Stage31

结论：**NO_CLEAR_SUPPORT**。三组 remnant 配对；本轮新增 1251 请求，usage 计价 $0.537804042。包含全部早停和反例。

- [实验报告](Stage31实验报告.md)
- [REC设计](REC设计文档.md)
- [失败模式覆盖](失败模式覆盖分析.md)
- [离线检测统计](离线误动作拦截统计.md)
- [Stage25案例对应](与Stage25失败案例对应分析.md)
- [控制器与早停审计](控制器逐提案与早停审计.md)
- [三游戏判断](三游戏测试与研究判断.md)
- [冻结前协议](预登记实验协议.md)

复算只使用归档响应：配置原冻结环境、PYTHONHASHSEED=0 和 AGENTODYSSEY_ROOT 后，运行 `python -m scar_stage31.verify --archive-only`、`python -m scar_stage31.terminal_review`、`python -m scar_stage31.analyze`、`python -m scar_stage31.offline_review`、`python -m scar_stage31.cases`、`python -m scar_stage31.report`、`python -m scar_stage31.validate_analysis`。全部零 API；不要运行 batch 来复算。精确包版本、原环境哈希在 freeze 和既有环境配置内，下载依赖不上传。

results/stage31 包含统计 CSV/JSON、完整新请求/轨迹、逐动作证据索引、REC 每个提案、原生探针、最终记忆及成本核验。AGC-v2 seed42 完整数据通过原 Stage25 路径引用，其余基线的原 47 步归档保留并与续跑合并；new_requests 单独保存新增调用。
