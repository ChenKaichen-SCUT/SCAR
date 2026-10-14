# wait 行为统计

合计 wait：Origin 1311/1769（74.1%），Reset 1146/1769（64.8%），Oracle 1086/1769（61.4%）。这是重叠检查点后缀的描述性加权汇总，不是独立试验总体估计。普通 Reset 减少 165 次 wait，仍有大量停滞。

| 检查点 | 版本 | wait/动作 | 比例 | 最长连续 wait | 最长 wait 区间 |
| --- | --- | --- | --- | --- | --- |
| mark-a033 | Origin | 190/268 | 70.9% | 27 | 216–242 |
| mark-a033 | Reset | 205/268 | 76.5% | 29 | 124–152 |
| mark-a033 | Oracle | 202/268 | 75.4% | 29 | 154–182 |
| mark-a035 | Origin | 190/266 | 71.4% | 27 | 216–242 |
| mark-a035 | Reset | 123/266 | 46.2% | 15 | 136–150 |
| mark-a035 | Oracle | 66/266 | 24.8% | 21 | 70–90 |
| mark-a052 | Origin | 190/249 | 76.3% | 27 | 216–242 |
| mark-a052 | Reset | 191/249 | 76.7% | 27 | 274–300 |
| mark-a052 | Oracle | 191/249 | 76.7% | 27 | 274–300 |
| mark-a064 | Origin | 179/237 | 75.5% | 27 | 216–242 |
| mark-a064 | Reset | 154/237 | 65.0% | 22 | 71–92 |
| mark-a064 | Oracle | 154/237 | 65.0% | 22 | 71–92 |
| mark-a070 | Origin | 177/231 | 76.6% | 27 | 216–242 |
| mark-a070 | Reset | 160/231 | 69.3% | 23 | 70–92, 160–182 |
| mark-a070 | Oracle | 160/231 | 69.3% | 23 | 70–92, 160–182 |
| mark-a100 | Origin | 148/201 | 73.6% | 27 | 216–242 |
| mark-a100 | Reset | 102/201 | 50.7% | 18 | 135–152 |
| mark-a100 | Oracle | 102/201 | 50.7% | 18 | 135–152 |
| mark-a179 | Origin | 88/122 | 72.1% | 27 | 216–242 |
| mark-a179 | Reset | 92/122 | 75.4% | 27 | 274–300 |
| mark-a179 | Oracle | 92/122 | 75.4% | 27 | 274–300 |
| mark-a193 | Origin | 82/108 | 75.9% | 27 | 216–242 |
| mark-a193 | Reset | 69/108 | 63.9% | 17 | 219–235 |
| mark-a193 | Oracle | 69/108 | 63.9% | 17 | 219–235 |
| mark-a244 | Origin | 43/57 | 75.4% | 18 | 283–300 |
| mark-a244 | Reset | 36/57 | 63.2% | 18 | 255–272 |
| mark-a244 | Oracle | 36/57 | 63.2% | 18 | 255–272 |
| mark-a271 | Origin | 24/30 | 80.0% | 18 | 283–300 |
| mark-a271 | Reset | 14/30 | 46.7% | 7 | 287–293 |
| mark-a271 | Oracle | 14/30 | 46.7% | 7 | 287–293 |


| 检查点 | 版本 | 剩余 REJECT 条件计数（可重叠） |
| --- | --- | --- |
| mark-a033 | Reset | hands=15, materials=88, nominal_single_craft_material=76, route=117 |
| mark-a033 | Oracle | hands=56, materials=72, nominal_single_craft_material=35, route=87 |
| mark-a035 | Reset | ground_presence=1, hands=89, materials=49, nominal_single_craft_material=24, route=5 |
| mark-a035 | Oracle | hands=65, materials=36, nominal_single_craft_material=26, route=1 |
| mark-a052 | Reset | container_contents=1, hands=153, route=50 |
| mark-a052 | Oracle | container_contents=1, hands=153, route=50 |
| mark-a064 | Reset | hands=142, materials=8, route=17 |
| mark-a064 | Oracle | hands=142, materials=8, route=17 |
| mark-a070 | Reset | hands=158, materials=8, route=12 |
| mark-a070 | Oracle | hands=158, materials=8, route=12 |
| mark-a100 | Reset | hands=85, materials=12, route=19 |
| mark-a100 | Oracle | hands=85, materials=12, route=19 |
| mark-a179 | Reset | hands=55, materials=2, route=42 |
| mark-a179 | Oracle | hands=55, materials=2, route=42 |
| mark-a193 | Reset | hands=58, route=17 |
| mark-a193 | Oracle | hands=58, route=17 |
| mark-a244 | Reset | hands=34, route=8 |
| mark-a244 | Oracle | hands=34, route=8 |
| mark-a271 | Reset | hands=15 |
| mark-a271 | Oracle | hands=15 |


上表每一项是条件出现次数，同一动作可能既触发 materials 又触发 nominal_single_craft_material，不能相加作为“被拒动作数”。这些计数不直接说明拒绝有害：例如 a271 分支 a272 在手持 2 cloth 时提出拾取 oak_log，原有 hands 检查拒绝有当前公开证据。

原目标默认权释放后，仍可能出现“基础模型重复不可行提案→保留的条件检查拒绝→控制器 wait”。a33 Reset 最后仍提出缺少 resin_clump 的 oak_dagger 制作，a52/193 长时间重复满手拾取。它们提示容量释放、材料执行、记忆与剩余控制交互还未隔离；不能仅凭 REJECT 就称这些防护本身有害。没有离线证明它们在同状态可成功的提案，不标记为已验证局部损失。
