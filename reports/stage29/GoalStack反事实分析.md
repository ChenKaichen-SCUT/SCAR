# Goal Stack 反事实分析

以下为纸面分析树，不是新增控制器，也没有提供给模型。节点只使用各检查点之前的公开信息，具体引文/截止动作/来源保存于 `paper_goal_stacks.json`。L0是Agent当时目标，不保证等于游戏主线；原尝试只是候选手段，不强行当必要路径。

## parent_a031（知识截止动作 31）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Find the one who knows where cinder-smoke gathers|
|attempt|parent|1|使原先尝试的动作可行：lockpick library|
|recovery|attempt|2|Have a lockpick tool held in hand before continuing the original objective.|
|source|recovery|3|确认所需工具或设施的公开可获得性/可访问性|

公开依据：

- 动作 31：`Cannot lockpick library. No lockpick tool in hand.`

仍未知或不能由层级本身决定：这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。

## parent_a054（知识截止动作 54）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Arm myself with a weapon before following the ash|
|attempt|parent|1|使原先尝试的动作可行：pick up iron_bar|
|recovery|attempt|2|Have sufficient free hand space for iron_bar before continuing the original objective.|
|space|recovery|3|使已被拒绝的容量约束得到满足，同时重新核验待保留资源|

公开依据：

- 动作 54：`Cannot pick up iron_bar, not enough space in hand.`

仍未知或不能由层级本身决定：目标关系本身不决定丢弃/存储哪个物品、能否访问容器或是否牺牲照明。

## parent_a060（知识截止动作 60）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Gather materials to craft a weapon|
|attempt|parent|1|使原先尝试的动作可行：craft 1 wood_plank|
|recovery|attempt|2|Have access to a workbench for crafting wood_plank before continuing the original objective.|
|source|recovery|3|确认所需工具或设施的公开可获得性/可访问性|
|component_0|attempt|2|核验公开材料条件：1 wood_log|

公开依据：

- 动作 60：`Cannot craft wood_plank. Missing necessary workbench in the current area.`
- 动作 59：`wood_plank (1 wood_log)`

仍未知或不能由层级本身决定：这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。；列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。

## parent_a113（知识截止动作 113）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Gather crafting materials from defeated goblin to improve equipment|
|attempt|parent|1|使原先尝试的动作可行：take out wooden_rod small_bag_0|
|recovery|attempt|2|Have sufficient free hand space for wooden_rod before continuing the original objective.|
|space|recovery|3|使已被拒绝的容量约束得到满足，同时重新核验待保留资源|

公开依据：

- 动作 113：`Cannot take out wooden_rod, not enough space in hand.`

仍未知或不能由层级本身决定：目标关系本身不决定丢弃/存储哪个物品、能否访问容器或是否牺牲照明。

## parent_a136（知识截止动作 136）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Improve equipment and carrying capacity to safely gather crafting materials|
|attempt|parent|1|使原先尝试的动作可行：write quiet paper_7|
|recovery|attempt|2|Have a writing tool held in hand before continuing the original objective.|
|source|recovery|3|确认所需工具或设施的公开可获得性/可访问性|

公开依据：

- 动作 136：`Cannot write on paper_7. No writing tools held in hand.`

仍未知或不能由层级本身决定：这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。

## parent_a235（知识截止动作 235）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Prepare a light source to explore the dark armory|
|attempt|parent|1|使原先尝试的动作可行：craft 1 torch|
|recovery|attempt|2|Have sufficient necessary ingredients for crafting torch before continuing the original objective.|
|component_0|attempt|2|核验公开材料条件：1 wooden_rod|
|component_1|attempt|2|核验公开材料条件：1 mountain_sulfur|

公开依据：

- 动作 235：`Cannot craft a single torch. Do not have sufficient amount of necessary ingredients.`
- 动作 132：`torch (1 wooden_rod, 1 mountain_sulfur)`

仍未知或不能由层级本身决定：列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。

## parent_a270（知识截止动作 270）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Find or craft a weapon or armor to improve combat readiness|
|attempt|parent|1|使原先尝试的动作可行：store 1 cloth small_satchel_0|
|recovery|attempt|2|Have sufficient free space in small_satchel_0 for cloth before continuing the original objective.|
|space|recovery|3|使已被拒绝的容量约束得到满足，同时重新核验待保留资源|

公开依据：

- 动作 270：`Cannot store any number of cloth, not enough space in small_satchel_0.`

仍未知或不能由层级本身决定：目标关系本身不决定丢弃/存储哪个物品、能否访问容器或是否牺牲照明。

## oracle032_a256（知识截止动作 256）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Craft a usable item from available materials at the workbench|
|attempt|parent|1|使原先尝试的动作可行：craft 1 glass_shard|
|recovery|attempt|2|Have access to a furnace for crafting glass_shard before continuing the original objective.|
|source|recovery|3|确认所需工具或设施的公开可获得性/可访问性|
|component_0|attempt|2|核验公开材料条件：1 quartz_chunk|

公开依据：

- 动作 256：`Cannot craft glass_shard. Missing necessary furnace in the current area.`
- 动作 233：`glass_shard (1 quartz_chunk)`

仍未知或不能由层级本身决定：这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。；列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。

## oracle037_a122（知识截止动作 122）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Equip gear and gather resources for survival|
|attempt|parent|1|使原先尝试的动作可行：craft 1 lockpick|
|recovery|attempt|2|Have access to a workbench for crafting lockpick before continuing the original objective.|
|source|recovery|3|确认所需工具或设施的公开可获得性/可访问性|
|component_0|attempt|2|核验公开材料条件：1 rust_scrap|
|component_1|attempt|2|核验公开材料条件：1 iron_bar|
|component_2|attempt|2|核验公开材料条件：1 thread|

公开依据：

- 动作 122：`Cannot craft lockpick. Missing necessary workbench in the current area.`
- 动作 121：`lockpick (1 rust_scrap, 1 iron_bar, 1 thread)`

仍未知或不能由层级本身决定：这个条件本身不提供工具/设施获取方法，也不证明需要新建；未知路径保持未知。；列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。

## oracle079_a165（知识截止动作 165）

|节点|父节点|层级|条件/目标|
|---|---|---|---|
|parent|None|0|Escape goblin_warrior_15 and find a weapon|
|attempt|parent|1|使原先尝试的动作可行：craft 1 star_metal_sword|
|recovery|attempt|2|Have sufficient necessary ingredients for crafting star_metal_sword before continuing the original objective.|
|component_0|attempt|2|核验公开材料条件：1 star_metal_blade|
|component_1|attempt|2|核验公开材料条件：1 wooden_rod|
|component_2|attempt|2|核验公开材料条件：1 cloth_strap|
|component_3|attempt|2|核验公开材料条件：1 goblin_eye|

公开依据：

- 动作 165：`Cannot craft a single star_metal_sword. Do not have sufficient amount of necessary ingredients.`
- 动作 164：`star_metal_sword (1 star_metal_blade, 1 wooden_rod, 1 cloth_strap, 1 goblin_eye)`

仍未知或不能由层级本身决定：列出成品组件不等于知道各组件的递归制作方法、设施或资源位置。

## 与信息补充的混杂

parent_a235 的旧 torch 配方公开于103/132，但236实际模型上下文未包含完整配方；若“理想Stack”补入 wooden_rod 和 mountain_sulfur，干预同时补回了旧知识。oracle079_a165 的完整剑配方在166上下文可见，173已不在；当时目标仍ACTIVE，模型却说 goblin_eye 不需要。相反，oracle032_a256 在274的上下文仍有 verified=true 的黑暗引文，却说没有直接黑暗证据。前者涉及信息保留/利用，后者涉及已在上下文证据的判断，不能都称为父目标丢失。

这些检查是特定完整字串/关系的证据，不等同测量模型内部记忆。全文和请求ID保存在 public_knowledge_context_audit.json。

## 已执行的原生局部反事实

在 oracle037_a122 的147步前复原相同物理状态/环境RNG；24步保存响应前缀精确回放，未调用模型。公开状态显示手持1个torch、地上可见iron_bar。原理由本身考虑了pick up iron_bar，却先错误认为手满并执行drop torch。

|同状态动作|实际原生结果|可支持的判断|
|---|---|---|
|drop torch（保存原动作）|状态哈希与旧轨迹一致；变暗|原分支精确重现|
|pick up iron_bar（公开可见候选）|成功；手中同时保留torch与iron_bar|存在不牺牲照明的局部可行行动|

这个对照是局部动作可行性证据，不能证明该动作长期更优、不会死亡、能够完成lockpick或第一章，更不能证明Goal Stack会选择它。它说明至少这一局部错误发生在目标与材料计划仍明确的情况下，单纯保留目标名称没有解决状态判断。

## 未执行的可选 Oracle Goal Stack Replay

本轮没有调用模型进行Stack提示续跑，也没有生成该实验的成功率。优先完成离线机制筛查，是因为当前存在多个竞争解释；“理想Stack”若补入旧配方、当前库存推断或替模型决定材料优先级，会混合信息、规划与层级三个干预。未执行不等于Stack无提升，也不构成关闭该研究方向的证据。

若后续另行安排，需信息等量对照，并保留合法替代、条件失效和死亡后的重新评估；这些均未在Stage29实现。
