# Stage10 S0：hellfire_bomb

历史成功：否；动作：40；本轮未重新运行闭环。原始来源 [results/stage10/trajectories_S0.jsonl.gz](../../../results/stage10/trajectories_S0.jsonl.gz)。

终末真实未公开必要配方：hellfire_bomb；历史缺失改判：无；已知却没有成功制作过：hellcoal_concentrate、oil_flask、rubble_chunk。这些是观察事实，不单独证明因果。

真实资源损失：

```json
[
  {
    "index": 21,
    "action": "inspect war_bench",
    "items": {
      "obj_devil_oil": 1
    },
    "named_items": {
      "devil_oil": 1
    }
  }
]
```

逐动作知识与原始反馈（index从0计）：

| index | 动作 | 新公开关系 | 新数量 | 新登记关系 | 原始反馈 |
| --- | --- | --- | --- | --- | --- |
| 0 | `inspect hellfire_bomb` | 无 | 无 | 无 | I inspected hellfire_bomb: A volatile bomb packed with hellcoal concentrate that erupts in searing infernal fire.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 1 | `inspect devil_oil` | cog_assembly、hellcoal_concentrate、honed_blade、oil_flask、scrap_lantern | 无 | cog_assembly、hellcoal_concentrate、honed_blade、oil_flask、scrap_lantern | I inspected devil_oil: A dark, viscous lubricant drained from a fallen war machine's joints. Burns with infernal heat.<br>It can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil), oil_flask (made of devil_oil, rubble_chunk), cog_assembly (made of cog, devil_oil), honed_blade (made of forged_blade_blank, devil_oil), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).<br>It has nothing written on it. |
| 2 | `inspect rubble` | crucible、rubble_chunk、war_bench | 无 | crucible、rubble_chunk、war_bench | I inspected rubble: Chunks of broken stone from a kingdom's collapsed walls, useful for construction.<br>It can be used to craft: rubble_chunk (made of rubble), war_bench (made of charred_timber, rubble), crucible (made of rubble).<br>It has nothing written on it. |
| 3 | `store 1 rubble inventory` | 无 | crucible、rubble_chunk、war_bench | 无 | I stored 1 rubble in my inventory.<br>I have acquired a new item: rubble. It can be used to craft: rubble_chunk (1 rubble), war_bench (5 charred_timber, 5 rubble), crucible (10 rubble) |
| 4 | `craft 2 rubble_chunk` | 无 | 无 | 无 | Cannot craft rubble_chunk. Missing necessary war_bench in the current area. |
| 5 | `enter cellar` | 无 | 无 | 无 | I entered cellar. |
| 6 | `inspect hellcoal` | 无 | 无 | 无 | I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.<br>It can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).<br>It has nothing written on it. |
| 7 | `inspect scrap_iron` | gate_cipher、iron_nugget、repair_kit、scrap_buckler、scrap_helm | 无 | gate_cipher、iron_nugget、repair_kit、scrap_buckler、scrap_helm | I inspected scrap_iron: Bent iron fragments torn from a destroyed war machine's hull.<br>It can be used to craft: repair_kit (made of scrap_iron, sinew_cord, oil_flask), scrap_buckler (made of scrap_iron, sinew_cord), iron_nugget (made of scrap_iron), gate_cipher (made of cog, scrap_iron), scrap_helm (made of scrap_iron, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).<br>It has nothing written on it. |
| 8 | `store 2 scrap_iron inventory` | 无 | gate_cipher、iron_nugget、repair_kit、scrap_buckler、scrap_helm、scrap_lantern | 无 | I stored 2 scrap_iron in my inventory.<br>olivia_grant enters the area.<br><br>Side quest completed: collect 1 scrap_iron<br>You earned 1 coins!<br>Talk to olivia_grant to see your updated tasks.<br>I have acquired a new item: scrap_iron. It can be used to craft: repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scrap_buckler (2 scrap_iron, 1 sinew_cord), iron_nugget (1 scrap_iron), gate_cipher (2 cog, 1 scrap_iron), scrap_helm (2 scrap_iron, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth) |
| 9 | `inspect crown_shard` | 无 | 无 | 无 | I inspected crown_shard: A broken fragment of an old kingdom's crown coin, still accepted as currency among the allied ruins.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 10 | `craft 2 iron_nugget` | 无 | 无 | 无 | Cannot craft iron_nugget. Missing necessary crucible in the current area. |
| 11 | `enter courtyard` | 无 | 无 | 无 | I entered courtyard. |
| 12 | `inspect crucible` | 无 | 无 | 无 | I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 13 | `inspect war_bench` | 无 | 无 | 无 | I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 14 | `craft 2 iron_nugget` | 无 | 无 | 无 | I successfully crafted 2 iron_nugget. It is now on the ground. |
| 15 | `inspect inventory` | 无 | 无 | 无 | I inspected my inventory.<br>It contains: 1 rubble (capacity: 1/20). |
| 16 | `inspect iron_nugget` | iron_bar | 无 | iron_bar | I inspected iron_nugget: A small smelted lump of iron recovered from scrap, a step toward war-grade metal.<br>It can be used to craft: iron_bar (made of iron_nugget).<br>It has nothing written on it. |
| 17 | `store 2 iron_nugget inventory` | 无 | iron_bar | 无 | I stored 2 iron_nugget in my inventory.<br>I have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget) |
| 18 | `craft 2 iron_bar` | 无 | 无 | 无 | Only enough ingredients to craft 1 iron_bar.<br>I successfully crafted 1 iron_bar. It is now on the ground. |
| 19 | `inspect inventory` | 无 | 无 | 无 | I inspected my inventory.<br>It contains: 1 rubble (capacity: 1/20). |
| 20 | `inspect hellfire_bomb` | 无 | 无 | 无 | I inspected hellfire_bomb: A volatile bomb packed with hellcoal concentrate that erupts in searing infernal fire.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 21 | `inspect war_bench` | 无 | 无 | 无 | I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.<br>It can be used to craft: None.<br>It has nothing written on it.<br><br>Ominous mechanical grinding echoes from the nearby cellar. Dormant war machines are reclaiming the abandoned territory — a iron_ravager_15 has emerged from the wreckage. |
| 22 | `craft 1 hellfire_bomb` | 无 | 无 | 无 | Cannot craft a single hellfire_bomb. Do not have sufficient amount of necessary ingredients. |
| 23 | `enter cellar` | 无 | 无 | 无 | I entered cellar. |
| 24 | `pick up hellcoal` | 无 | hellcoal_concentrate | 无 | I picked up hellcoal.<br>I have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil) |
| 25 | `pick up hellcoal` | 无 | 无 | 无 | Cannot pick up hellcoal, not enough space in hand. |
| 26 | `enter courtyard` | 无 | 无 | 无 | I entered courtyard. |
| 27 | `inspect hellcoal` | 无 | 无 | 无 | I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.<br>It can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).<br>It has nothing written on it. |
| 28 | `store 1 hellcoal scout_satchel_0` | 无 | 无 | 无 | I stored 1 hellcoal in scout_satchel_0. |
| 29 | `enter cellar` | 无 | 无 | 无 | I entered cellar. |
| 30 | `enter courtyard` | 无 | 无 | 无 | I entered courtyard. |
| 31 | `wait` | 无 | 无 | 无 | I waited for a while. |
| 32 | `enter barracks` | 无 | 无 | 无 | Cannot enter barracks. There's no path to barracks. |
| 33 | `inspect war_bench` | 无 | 无 | 无 | I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 34 | `inspect crucible` | 无 | 无 | 无 | I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 35 | `inspect hellfire_bomb` | 无 | 无 | 无 | I inspected hellfire_bomb: A volatile bomb packed with hellcoal concentrate that erupts in searing infernal fire.<br>It can be used to craft: None.<br>It has nothing written on it. |
| 36 | `enter cellar` | 无 | 无 | 无 | I entered cellar. |
| 37 | `pick up hellcoal` | 无 | 无 | 无 | I picked up hellcoal. |
| 38 | `talk to olivia_grant` | 无 | 无 | 无 | I talked to olivia_grant.<br>olivia_grant says: I'm a helpful guide who tracks your side quest progress. Your current tasks are:<br>- [collect]: No task available<br>- craft a hellcoal_concentrate (reward: 4 coins)<br>- [talk]: No task available<br>- [trade]: No task available |
| 39 | `craft 2 hellcoal_concentrate` | 无 | 无 | 无 | Cannot craft hellcoal_concentrate. Missing necessary crucible in the current area. |
