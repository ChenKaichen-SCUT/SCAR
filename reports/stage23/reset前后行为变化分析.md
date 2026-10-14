# reset 前后行为变化分析

| 检查点 | 版本 | 首次 stale（母轨迹） | reset | reset 前连续 wait | reset 当步动作 | 首次仲裁释放 | 首次新事实 | 再次告知 oak 任务 | 首次主线奖励 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mark-a033 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a033 | Reset | 32 | 34 | 0 | enter library | 35 | 35 | 35 | 42 |
| mark-a033 | Oracle | 32 | 33 | 0 | talk to remy | 33 | 33 | 33 | 40 |
| mark-a035 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a035 | Reset | 32 | 36 | 0 | enter library | 36 | 37 | 37 | 42 |
| mark-a035 | Oracle | 32 | 35 | 0 | talk to remy | 35 | 35 | 35 | 40 |
| mark-a052 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a052 | Reset | 32 | 52 | 0 | wait | 68 | 63 | 63 | — |
| mark-a052 | Oracle | 32 | 52 | 0 | wait | 68 | 63 | 63 | — |
| mark-a064 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a064 | Reset | 32 | 64 | 0 | enter library | 68 | — | 93 | — |
| mark-a064 | Oracle | 32 | 64 | 0 | enter library | 68 | — | 93 | — |
| mark-a070 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a070 | Reset | 32 | 70 | 2 | wait | 94 | — | 93 | — |
| mark-a070 | Oracle | 32 | 70 | 2 | wait | 94 | — | 93 | — |
| mark-a100 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a100 | Reset | 32 | 100 | 6 | enter library | 100 | 290 | 123 | 294 |
| mark-a100 | Oracle | 32 | 100 | 6 | enter library | 100 | 290 | 123 | 294 |
| mark-a179 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a179 | Reset | 32 | 179 | 0 | attack fen_cutthroat_8 | 179 | — | 183 | — |
| mark-a179 | Oracle | 32 | 179 | 0 | attack fen_cutthroat_8 | 179 | — | 183 | — |
| mark-a193 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a193 | Reset | 32 | 193 | 0 | wait | 216 | — | 211 | — |
| mark-a193 | Oracle | 32 | 193 | 0 | wait | 216 | — | 211 | — |
| mark-a244 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a244 | Reset | 32 | 244 | 0 | enter library | 244 | — | 273 | — |
| mark-a244 | Oracle | 32 | 244 | 0 | enter library | 244 | — | 273 | — |
| mark-a271 | Origin | 32 | — | — | — | — | — | — | — |
| mark-a271 | Reset | 32 | 271 | 0 | enter library | 275 | — | — | — |
| mark-a271 | Oracle | 32 | 271 | 0 | enter library | 275 | — | — | — |


reset 为动作仲裁前激活时刻；“首次仲裁释放”是第一次命中新增释放分支，可能晚于 reset。“首次新事实”只统计 Stage22-B 的 13 类固定公开知识标记，相对整个共享前缀已见知识去重，不是所有自然语言信息。空值不代表没有任何新信息。已知任务被再次告知单列，不能算成新发现。原文本与更一般状态变化均保留在逐步指标里。

| 检查点 | 版本 | 新状态签名 | 新区域 | 接受非 wait | 进展代理动作 | wait 比例 |
| --- | --- | --- | --- | --- | --- | --- |
| mark-a033 | Origin | 23 | 0 | 76/268 | 6 | 70.9% |
| mark-a033 | Reset | 20 | 0 | 58/268 | 9 | 76.5% |
| mark-a033 | Oracle | 22 | 0 | 62/268 | 9 | 75.4% |
| mark-a035 | Origin | 22 | 0 | 74/266 | 6 | 71.4% |
| mark-a035 | Reset | 77 | 2 | 136/266 | 26 | 46.2% |
| mark-a035 | Oracle | 95 | 8 | 192/266 | 42 | 24.8% |
| mark-a052 | Origin | 19 | 0 | 58/249 | 3 | 76.3% |
| mark-a052 | Reset | 11 | 0 | 58/249 | 2 | 76.7% |
| mark-a052 | Oracle | 11 | 0 | 58/249 | 2 | 76.7% |
| mark-a064 | Origin | 18 | 0 | 57/237 | 2 | 75.5% |
| mark-a064 | Reset | 17 | 0 | 82/237 | 3 | 65.0% |
| mark-a064 | Oracle | 17 | 0 | 82/237 | 3 | 65.0% |
| mark-a070 | Origin | 17 | 0 | 53/231 | 2 | 76.6% |
| mark-a070 | Reset | 14 | 0 | 70/231 | 3 | 69.3% |
| mark-a070 | Oracle | 14 | 0 | 70/231 | 3 | 69.3% |
| mark-a100 | Origin | 16 | 0 | 52/201 | 2 | 73.6% |
| mark-a100 | Reset | 33 | 1 | 94/201 | 14 | 50.7% |
| mark-a100 | Oracle | 33 | 1 | 94/201 | 14 | 50.7% |
| mark-a179 | Origin | 12 | 0 | 33/122 | 2 | 72.1% |
| mark-a179 | Reset | 8 | 0 | 27/122 | 2 | 75.4% |
| mark-a179 | Oracle | 8 | 0 | 27/122 | 2 | 75.4% |
| mark-a193 | Origin | 8 | 0 | 26/108 | 1 | 75.9% |
| mark-a193 | Reset | 11 | 0 | 37/108 | 1 | 63.9% |
| mark-a193 | Oracle | 11 | 0 | 37/108 | 1 | 63.9% |
| mark-a244 | Origin | 4 | 0 | 14/57 | 0 | 75.4% |
| mark-a244 | Reset | 4 | 0 | 20/57 | 0 | 63.2% |
| mark-a244 | Oracle | 4 | 0 | 20/57 | 0 | 63.2% |
| mark-a271 | Origin | 1 | 0 | 6/30 | 0 | 80.0% |
| mark-a271 | Reset | 2 | 0 | 16/30 | 0 | 46.7% |
| mark-a271 | Oracle | 2 | 0 | 16/30 | 0 | 46.7% |


新状态签名只含位置、手持、装备、地面物品名称及 NPC 名称，排除时间、HP、stamina 和地面数量；地面刷新或 NPC 自行活动也能改变签名。新区域由动作后的公开位置计算，若同一步进入后死亡复活，该区域不会计入公开最终位置口径（例如 Oracle-a35 的 a166）。因此它不是隐藏地图遍历总数。

“接受非 wait”排除 invalid_action 及公开 Cannot/Invalid/教程拒绝反馈；这是可复算的文本判据，不等于任务相关。“进展代理”还要求主线增量、制作奖励、新知识标记、新区域、新持有物名称或首次击杀之一。它仍可能包括支线或无关物品，严格任务推进看原生 quest 奖励。

a35 Oracle：a35 对话获得任务，a40 收取 oak_rod，a50 收取 copper_sword，a94 写 kindness，a166 到达 stalls，a194 收取 torch，a271 到 backstreets，a276 完成第一章。这个序列支持“解除阻塞→获得信息→连续任务推进”。a33 两干预版只得到 1 奖励后再次停滞；a271 虽减少 10 个 wait，却没有奖励或进展代理动作，不能称为恢复。

a100 的两干预版到 a294 才取得首奖励，a297/a299 再推进两阶段。首奖励延迟 194 个绝对步差，表明可推进并不等于高效。该分支不是“仅早期机会点有效”的例外排除项，已纳入全部结果。
