# Stage24 交付索引

完成独立 AGC 实现和三游戏唯一一次试验；仅两处用户授权的空白解析修复续跑，保留初次失败。最终主线 remnant/mark/metropolis = 1/11/4；两个硬拒绝提前终止。未运行新基线，未修改 Stage18。

- [科研总结报告](科研总结报告.md)：结论、RQ1–RQ3、限制。
- [AGC 算法设计与预登记](AGC算法设计.md)：冻结前协议。
- [三游戏结果表](三游戏结果表.md)：全部正负结果、诊断、费用。
- [轨迹分析](轨迹分析.md)：里程碑、长期循环、格式失败。
- [Stage18 失败模式对应](Stage18失败模式对应分析.md)。
- [授权修复与续跑](空白字符修复与续跑记录.md)：原版与混合版本来源。
- [代码](../../agents/agc/)、[运行和分析脚本](../../scar_stage24/)。
- [原始运行](../../results/stage24/runs/)、[续跑](../../results/stage24/resumed/runs/)、[日志](../../results/stage24/logs/)。
- [全部证据索引](../../results/stage24/evidence.jsonl.gz)、[逐动作指标](../../results/stage24/step_metrics/)。

离线复算：配置与 Stage22 相同的外部引擎及依赖（不上传下载包），设置 PYTHONHASHSEED=0、AGENTODYSSEY_ROOT 为引擎目录、PYTHONPATH 为项目和引擎目录。执行 `python -m scar_stage24.verify --game GAME --phase first_pass`；remnant/mark 再执行 `--phase resumed`。随后运行 `scar_stage24.analyze`、`scar_stage24.diagnose`、`scar_stage24.response_audit`、`scar_stage24.report`。这些模块禁止网络连接，不访问 API 密钥。`account` 额外依赖本机账本；公开的逐响应记录足以重算金额。`audit_quote` 与 `terminal_audit` 支持原生单动作审计。

不要将 `batch` 或 `repair --game` 当作离线复算命令，它们是付费运行入口。代码冻结与预检记录在 results/stage24；发布提交和文件增删行数见 publication.json / change_ledger.json。仅上传本项目实现、审计证据和结果，没有打包第三方引擎、模型权重、虚拟环境或密钥。
