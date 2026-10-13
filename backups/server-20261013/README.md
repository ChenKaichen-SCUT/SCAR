# 服务器项目备份（2026-10-13）

源目录 `/root/scar_workspace/project`。对照提交 `c5fa743e7fc71460c1bcd73ed7b82c9ef3e5e975`：3,169 个文件内容完全一致；24 个服务器独有文件保存在 `project-supplement.tar.gz`。`project-manifest.json` 逐文件记录全部 3,193 个源码、配置、报告和实验产物的 SHA-256。补充包包含历史开发产物及服务器侧离线反事实结果，不替换任何正式结果。

`scar18-terminal-memory.tar.gz` 额外保存 174 个 SCAR18 文件：控制器和短期记忆、检查点元信息、进度、日志及 SQLite 账本的 SQL 导出。24 局的 876 条动作记录和 885 条模型请求已逐条核对，与 `results/stage18/runs/` 的公开归档完全一致，因此不重复上传。`scar18-runtime-manifest.json` 覆盖服务器 SCAR18 运行目录的全部 1,176 个文件。

完整 SCAR18 运行目录已复制到本地 `runtime/server_stage18/`，包括 24 个物理检查点；均已验证 SHA-256 和跨机器恢复。原始路径仍写在历史审计文件中，不作改写；这份目录用于恢复和审计，新运行另存 `runtime/local/`。

上传范围遵守“只上传我们实现的代码和结果”的约定：不上传密钥、虚拟环境、下载的引擎、重复世界副本或物理 pickle。旧阶段的可重建运行缓存仍留在服务器；其已发表源码、轨迹、统计和报告保留在 Git 历史及当前项目中。本备份是研究项目备份，不是服务器整盘镜像。服务器原文件与其他基线均未删除或修改。

`backup-index.json` 给出归档哈希、数量和去重核对结果。备份生成程序为 `scripts/backup_server_workspace.py`；本地完整性与检查点恢复检查为 `scar_local/verify_migration.py`。恢复补充包时先解到空目录检查，避免覆盖正式结果。
