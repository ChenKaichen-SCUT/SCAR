# Stage25 Git 变更与发布记录

相对 Stage24 发布提交 `83fcc6942e015936f66ea695ae5ce3d99f9a95b5`，本阶段所有变更均新增在独立的 Stage25 路径，旧算法、旧结果与引擎未修改。

| 提交用途 | commit hash | 文件数 | 文本新增/删除 |
|---|---|---|---|
| 算法与协议冻结 | [c7a509c90bd87b0db520d3f56a3c209754d380b2](https://github.com/ChenKaichen-SCUT/SCAR/commit/c7a509c90bd87b0db520d3f56a3c209754d380b2) | 36 | +7192 / −0 |
| 用户范围缩减 | [99a0bcf15c7bbd26557e8657df8d3cc32a9cbed0](https://github.com/ChenKaichen-SCUT/SCAR/commit/99a0bcf15c7bbd26557e8657df8d3cc32a9cbed0) | 3 | +193 / −0 |
| 实验结果与离线分析 | [5962da117bf6055706602c95f46bdcfd8057d9af](https://github.com/ChenKaichen-SCUT/SCAR/commit/5962da117bf6055706602c95f46bdcfd8057d9af) | 127 | +115786 / −0 |

截至结果提交，共 166 个新增文件，文本 +123171 / −0 行；其中 Python 18 个文件、+1186 行，算法本体 agents/agc_v2 为 3 个文件、+185 行。二进制轨迹/图表不按文本行统计。当前发布记录自身不计入以上截至结果提交的统计；完整逐文件清单见 results/stage25/change_accounting.json。

| Python文件 | 新增 | 删除 |
|---|---|---|
| agents/agc_v2/__init__.py | 1 | 0 |
| agents/agc_v2/agent.py | 58 | 0 |
| agents/agc_v2/control.py | 126 | 0 |
| scar_stage25/__init__.py | 1 | 0 |
| scar_stage25/account.py | 84 | 0 |
| scar_stage25/analyze.py | 141 | 0 |
| scar_stage25/audit.py | 46 | 0 |
| scar_stage25/batch.py | 19 | 0 |
| scar_stage25/common.py | 15 | 0 |
| scar_stage25/diagnose.py | 111 | 0 |
| scar_stage25/freeze.py | 23 | 0 |
| scar_stage25/integration.py | 13 | 0 |
| scar_stage25/preflight.py | 107 | 0 |
| scar_stage25/prepare.py | 31 | 0 |
| scar_stage25/report.py | 214 | 0 |
| scar_stage25/run.py | 81 | 0 |
| scar_stage25/smoke.py | 53 | 0 |
| scar_stage25/verify.py | 62 | 0 |

本阶段新增模型请求 1223 次：正式三局1011，取消六局212；新增计价费用 $0.951937152，其中正式 $0.822290940、取消 $0.129646212。离线分析、回放、图表与报告新增模型调用均为0。六次账本取消拦截在API发送前终止，费用0，不算模型请求。

算法冻结后没有修复、调参或失败重跑。原九局批处理器保留；通过独立账本拦截取消多余六局，最终有效结果由范围修订与 effective_completion.json 共同界定。基础设施的原始 infrastructure_error 记录未覆盖，研究状态单独标为 user_cancelled。

发布材料包括自己的代码、生成的初态快照、轨迹、模型请求、统计、图表和报告；未上传下载引擎、依赖环境、API密钥或运行SQLite账本。900步原生精确回放及1011个请求输入核验全部通过，4889个项目冻结文件和278个引擎文件完整性通过。
