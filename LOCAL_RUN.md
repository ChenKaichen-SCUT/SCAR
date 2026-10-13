# 在本地运行 SCAR

当前本地入口使用服务器的 **SCAR18 原实现**：最多 100 个环境动作，内部收尾时钟同样为 100；STM 为 5。迁移只增加启动、备份和验收工具，未修改算法或其他基线。

本机目录为 `/mnt/Space0/AINative/scar_agentodyssey`。Python 3.12 环境在 `/mnt/Space0/scar_dependencies/venv`，游戏引擎在 `/mnt/Space0/scar_dependencies/agentodyssey`；`.venv` 是本地链接。依赖与 `requirements-cpu.lock` 完全一致。无需重新下载模型或安装 CUDA。

```bash
cd /mnt/Space0/AINative/scar_agentodyssey
bash scripts/scar_local.sh doctor      # 检查环境与冻结源码，不调用模型
bash scripts/scar_local.sh list-tasks  # 列出 24 个已有任务
bash scripts/scar_local.sh smoke       # 用服务器已保存的回复做离线验收
```

`smoke` 在禁止网络的进程中回放两个游戏的既有轨迹，逐步核对完整请求签名、动作、控制器决策、反馈与物理状态。它是迁移验收，不是新实验；结果保存在 `runtime/local/smoke.json`。

开始一局新的本地实验（下面命令会调用模型 API）：

```bash
bash scripts/scar_local.sh run \
  --task s17-04-robot_kingdom-ruin_club \
  --run-dir runtime/local/my-first-run
```

模型、温度和输出上限沿用 Stage18；费用保护沿用原配置，单局上限 $0.25。模型费用仍按仓库冻结价格估计，迁移没有验证服务端余额或当前计费。密钥从环境变量 `DEEPSEEK_API_KEY` 或仓库上一级的 `miyao.txt` 读取；也可传 `--key-path /private/path/key.txt`。密钥不写入输出或 Git。

每局独立记录 `run_config.json`、`runtime/` 和 `results/`。省略 `--run-dir` 时使用带时间戳的新目录。已有目录不会被覆盖；中断后使用同一任务和目录加 `--resume`，冻结配置、请求缓存和检查点由原执行器核对。已经生成最终报告的成功或失败局直接返回原结果，不重跑；不确定计费中断仍由原执行器停止处理。

```bash
bash scripts/scar_local.sh run \
  --task s17-04-robot_kingdom-ruin_club \
  --run-dir runtime/local/my-first-run --resume
```

正式历史结果保留在 `results/stage18/`。服务器迁回的完整状态位于 `runtime/server_stage18/`，供离线检查；新启动器禁止将这两处用作输出。不同路径下的请求 ID 和账本有路径绑定，不应把服务器运行目录直接当作新的计费运行目录。

迁移时仅执行了离线检查，没有新建付费实验。完整收据见 `reports/local-migration-20261013/`，服务器备份见 `backups/server-20261013/`。如需在其他机器上使用，可设置 `SCAR_DEPENDENCIES`，或分别设置 `SCAR_PYTHON`、`AGENTODYSSEY_ROOT`；启动脚本会设置导入路径、随机哈希种子及线程数。

冻结入口用于复现当前 SCAR18。如后续开发新方法，应新建版本和输出目录；原源码哈希检查可以防止误将修改后的方法标记成旧版本。
