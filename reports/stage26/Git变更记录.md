# Stage26 Git变更与费用记录

基于Stage25发布提交 `ef687bdd0966205464ab6f9622981b0116153e02`。全部新增文件均位于scar_stage26、reports/stage26、results/stage26；AGC-v2和其他既有算法/结果未修改。

| 用途 | commit hash | 文件数 | 文本增删 |
|---|---|---|---|
| 诊断代码与预登记 | [ec7ef262a059cd9c00cb39846a725094c0776212](https://github.com/ChenKaichen-SCUT/SCAR/commit/ec7ef262a059cd9c00cb39846a725094c0776212) | 16 | +1736 / −0 |
| 原生断点与冻结清单 | [800096d5f3ba2426870540d66de7f8d8550b41ae](https://github.com/ChenKaichen-SCUT/SCAR/commit/800096d5f3ba2426870540d66de7f8d8550b41ae) | 61 | +24001 / −0 |
| 完整结果与诊断分析 | [70343cc02153a6f2f4657a1e0471d1378aeaee0e](https://github.com/ChenKaichen-SCUT/SCAR/commit/70343cc02153a6f2f4657a1e0471d1378aeaee0e) | 181 | +104929 / −0 |

截至实验结果提交，新增258个文件，文本+130666 / −0行；其中16个Python文件、+1010行，Agent算法文件修改0个。二进制快照、轨迹、图表不计文本行。本发布记录自身不计入截至结果提交的统计；完整逐文件清单见results/stage26/change_accounting.json。

| Python文件 | 新增行 | 删除行 |
|---|---|---|
| scar_stage26/__init__.py | 1 | 0 |
| scar_stage26/account.py | 63 | 0 |
| scar_stage26/analyze.py | 132 | 0 |
| scar_stage26/audit.py | 56 | 0 |
| scar_stage26/batch.py | 24 | 0 |
| scar_stage26/common.py | 31 | 0 |
| scar_stage26/diagnose.py | 79 | 0 |
| scar_stage26/freeze.py | 21 | 0 |
| scar_stage26/prepare.py | 59 | 0 |
| scar_stage26/provider.py | 23 | 0 |
| scar_stage26/replay.py | 13 | 0 |
| scar_stage26/report.py | 227 | 0 |
| scar_stage26/run.py | 95 | 0 |
| scar_stage26/smoke.py | 49 | 0 |
| scar_stage26/source_audit.py | 78 | 0 |
| scar_stage26/verify.py | 59 | 0 |

新增模型调用2117次，计价$1.724797284。首次干预决策共复用11个已有响应（部分决策原本包含目标重评估），新增费用0；Original后缀和全部离线分析/验证调用0次。费用来自保存usage及价格，并与原始本地账本逐条核对；未取得供应商发票。

300个母轨迹动作和1918个Oracle动作已精确原生回放；2128个Oracle续跑模型上下文（含复用响应）全部核验。5099个冻结项目文件和278个引擎文件通过完整性检查。没有失败重跑、模型/提示/算法修复、阈值调整或500步实验。

a28分支第225次决策四次重复非法pick up 10 coin后按冻结规则结束，剩余76步未执行，原始响应、费用和终止全部保留。其余九个分支执行至绝对a300。10个分支最终主线均1，首章0/10；它们共享一条母轨迹，不是10个独立样本。

仅发布本阶段自有实验/分析代码和生成材料；下载引擎、依赖环境、API密钥和运行SQLite账本不入Git。秘密扫描覆盖文本与解压后归档，通过。
