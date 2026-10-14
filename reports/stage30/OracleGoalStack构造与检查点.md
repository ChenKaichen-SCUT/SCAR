# Oracle Goal Stack 构造与检查点

level 0 是检查点原目标；level 1 与 Stage28 临时恢复目标完全相同；level 2 是公开拒绝已经暗含的可用性/条件确认。兄弟节点没有动作顺序。子条件有些在初始 observation 中已经满足，必须标为已有而不能算新增知识。

禁止提供配方、材料清单/数量、位置或资源路径。本轮不直接使用 Stage29 纸面树，因为其中含当前短期上下文未必可见的旧配方。完整 JSON、公开来源原文、截止动作号与检查点文件哈希见 results/stage30/checkpoints/*/meta.json。未知依赖保持未知，因此不是全知层级上界。

|检查点|失败动作号|原动作|level 0|level 1|level 2|剩余预算|
|---|---|---|---|---|---|---|
|parent_a031|31|lockpick library|Find the one who knows where cinder-smoke gathers|Have a lockpick tool held in hand before continuing the original objective.|The availability of a lockpick tool is known from public evidence.|269|
|parent_a054|54|pick up iron_bar|Arm myself with a weapon before following the ash|Have sufficient free hand space for iron_bar before continuing the original objective.|The available hand space and held objects are established from public evidence.|246|
|parent_a060|60|craft 1 wood_plank|Gather materials to craft a weapon|Have access to a workbench for crafting wood_plank before continuing the original objective.|The accessibility of a workbench is known from public evidence.|240|
|parent_a113|113|take out wooden_rod small_bag_0|Gather crafting materials from defeated goblin to improve equipment|Have sufficient free hand space for wooden_rod before continuing the original objective.|The available hand space and held objects are established from public evidence.|187|
|parent_a136|136|write quiet paper_7|Improve equipment and carrying capacity to safely gather crafting materials|Have a writing tool held in hand before continuing the original objective.|The availability of a writing tool is known from public evidence.|164|
|parent_a235|235|craft 1 torch|Prepare a light source to explore the dark armory|Have sufficient necessary ingredients for crafting torch before continuing the original objective.|The required ingredients and quantities are known from public evidence.; The availability of those publicly known ingredients is established.|65|
|parent_a270|270|store 1 cloth small_satchel_0|Find or craft a weapon or armor to improve combat readiness|Have sufficient free space in small_satchel_0 for cloth before continuing the original objective.|The available space and contents of the affected container are established from public evidence.|30|
|oracle032_a256|256|craft 1 glass_shard|Craft a usable item from available materials at the workbench|Have access to a furnace for crafting glass_shard before continuing the original objective.|The accessibility of a furnace is known from public evidence.|44|
|oracle037_a122|122|craft 1 lockpick|Equip gear and gather resources for survival|Have access to a workbench for crafting lockpick before continuing the original objective.|The accessibility of a workbench is known from public evidence.|178|
|oracle079_a165|165|craft 1 star_metal_sword|Escape goblin_warrior_15 and find a weapon|Have sufficient necessary ingredients for crafting star_metal_sword before continuing the original objective.|The required ingredients and quantities are known from public evidence.; The availability of those publicly known ingredients is established.|135|
