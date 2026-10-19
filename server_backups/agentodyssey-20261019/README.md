# AgentOdyssey 实验服务器备份 · 2026-10-19

这是 `/root/agentodyssey-benchmark-20261018` 的独立快照。它属于本次 **DeepSeek + 全历史 ReAct** 实验，版本名 `feedback_v3`、`v3r6` 等与 SCAR 主仓库既有 V1/V2/V3 实验分开解释；本次备份没有替换原有实现或结果。

**版本选择先看 [BEST_VERSIONS.md](BEST_VERSIONS.md)。** 三游戏历史主版本是 `feedback_v3`；Remnant 的最高完整运行记录为 `no_repeat` 消融（3/24）。最新 `v3r7` 是 2/24，未提分，不标为最佳。

## 备份范围

- 59,498 个原始文件，合计 3,557,601,633 字节；完整压缩包 1,413,531,488 字节。
- 包含服务器上的研究代码、第三方源码及许可证、配置、协议、测试、预算数据库、完整运行轨迹、游戏引擎配置快照、Agent 游戏状态、API 请求/响应与用量审计、旧结果归档、离线回归资料。
- API 密钥、其他凭据、虚拟环境、缓存、Git 内部目录和公共模型文件不进入快照。具体排除路径在 [manifest.json](metadata/manifest.json) 的 `excluded` 字段中。
- 公共模型文件的 SHA-256、大小及服务器环境见 [environment.json](metadata/environment.json)；Python 包版本见 [requirements-server.txt](metadata/requirements-server.txt)。环境和模型需要重新安装，不声称这是操作系统磁盘镜像。
- 服务器原件保持不变。备份没有运行新游戏或调用模型 API。

## 文件布局

| 路径 | 内容 |
|---|---|
| `archive/snapshot.tar.gz.part*` | 按顺序拼接的完整归档分块，每块至多 32 MiB；不是 Git LFS 指针 |
| `metadata/manifest.json` | 原始文件路径、字节数、SHA-256，以及排除项 |
| `metadata/chunks.json` | 每个分块和完整归档的校验值 |
| `metadata/run_index.json` | 从服务器原始轨迹重算的逐局得分、步数、死亡和增分位置 |
| `metadata/local_verification.json` | 下载、逐文件校验、递归压缩内容凭据扫描结果 |
| `code/` | 服务器顶层 Python 文件的可浏览副本；完整目录结构在归档中 |
| `records/` | 服务器顶层配置、协议、结果和核验 JSON 的可浏览副本 |
| `analysis/v3r7/` | 本次 v3r7 的补充行为分析和 API 审计 |

归档 SHA-256：`3aa6367a1a4904189754833424a2675766f5b9dc974a21a2c2a7fc821f12797f`。

## 还原与核验

使用 Git 获取分块，或下载整个仓库；不要只下载 GitHub 网页显示的文本内容。Python 3.10+，只使用标准库：

```bash
python server_backups/agentodyssey-20261019/restore.py --verify-only
python server_backups/agentodyssey-20261019/restore.py --destination /path/to/new-empty-backup-directory
```

还原结果包含 `workspace/`（原服务器项目）和 `restore/`（环境清单）。脚本检查全部分块、完整归档和每个原文件的哈希，拒绝覆盖现有目录，不反序列化 pickle，不执行实验。

原有脚本包含固定绝对路径 `/root/agentodyssey-benchmark-20261018`。要继续运行，应在新环境恢复该目录结构或明确修改路径，再重建 `.venv`、安装记录的依赖并提供自己的凭据。公共 embedding 模型可重新下载，使用环境清单中的哈希核对版本。快照是原始代码及证据备份，不代表已在另一台机器完成环境重建测试。

冻结 run ID 不能直接作为新实验输出目录；已有启动脚本有防重复运行及哈希检查。预算数据库保留原账本，不能通过重置账本绕过额度约束。只做结果核验时不需要 API 密钥，也不应重新运行随机 LLM。

## 结果解释

所有比较都是本轮已发生的单次轨迹。运行上限、提前失败和模型调用预算不完全相同；最高观察分数不等于统计显著的算法优势。失败和取消的版本也完整保留，未选择性删除。
