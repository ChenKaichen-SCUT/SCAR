# Stage11 E1：hellfire_bomb

历史成功：否；动作：40；本轮未重新运行闭环。原始来源 [results/stage11/trajectories_E1.jsonl.gz](../../../results/stage11/trajectories_E1.jsonl.gz)。

终末真实未公开必要配方：无；历史缺失改判：无；已知却没有成功制作过：hellcoal_concentrate、hellfire_bomb、oil_flask。这些是观察事实，不单独证明因果。

真实资源损失：

```json
[
  {
    "index": 21,
    "action": "enter cellar",
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
| 20 | `pick up iron_bar` | chain_net、cog_crossbow、fiend_halberd、forged_blade_blank、gate_blank、gearwork_frame、hellfire_bomb、hunter_gauntlets、hunter_helm、iron_mace、iron_sheet、machine_trap、siege_crate、war_pack | chain_net、cog_crossbow、fiend_halberd、forged_blade_blank、gate_blank、gearwork_frame、hellfire_bomb、hunter_gauntlets、hunter_helm、iron_mace、iron_sheet、machine_trap、siege_crate、war_pack | 无 | I picked up iron_bar.<br>I have acquired a new item: iron_bar. It can be used to craft: forged_blade_blank (2 iron_bar, 1 wooden_rod), hellfire_bomb (1 hellcoal_concentrate, 1 oil_flask, 0.5 iron_bar), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), fiend_halberd (1 fiend_alloy, 2 iron_bar, 2 wooden_rod, 2 war_strap), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), gearwork_frame (1 cog_assembly, 2 iron_bar), iron_mace (2 iron_bar, 1 wooden_rod, 1 war_strap), war_pack (2 stitched_panel, 2 war_strap, 1 iron_bar), gate_blank (0.5 iron_bar), chain_net (3 iron_bar, 2 sinew_cord), iron_sheet (2 iron_bar), hunter_helm (2 iron_bar, 1 padded_lining), machine_trap (1 chain_net, 1 cog_assembly, 1 iron_bar) |
| 21 | `enter cellar` | 无 | 无 | 无 | I entered cellar.<br><br>Ominous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a iron_ravager_14 has emerged from the wreckage. |
| 22 | `store 1 hellcoal inventory` | 无 | hellcoal_concentrate | 无 | I stored 1 hellcoal in my inventory.<br>I have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil) |
| 23 | `store 1 hellcoal inventory` | 无 | 无 | 无 | I stored 1 hellcoal in my inventory. |
| 24 | `store 1 hellcoal inventory` | 无 | 无 | 无 | I stored 1 hellcoal in my inventory.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (98 HP remaining) |
| 25 | `enter barracks` | 无 | 无 | 无 | I entered barracks.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining) |
| 26 | `inspect iron_bar` | 无 | 无 | chain_net、cog_crossbow、fiend_halberd、forged_blade_blank、gate_blank、gearwork_frame、hellfire_bomb、hunter_gauntlets、hunter_helm、iron_mace、iron_sheet、machine_trap、siege_crate、war_pack | I inspected iron_bar: A smelted bar of iron pulled from the ruins, ready for forging into weapons against devil machines.<br>It can be used to craft: forged_blade_blank (made of iron_bar, wooden_rod), hellfire_bomb (made of hellcoal_concentrate, oil_flask, iron_bar), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), fiend_halberd (made of fiend_alloy, iron_bar, wooden_rod, war_strap), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), gearwork_frame (made of cog_assembly, iron_bar), iron_mace (made of iron_bar, wooden_rod, war_strap), war_pack (made of stitched_panel, war_strap, iron_bar), gate_blank (made of iron_bar), chain_net (made of iron_bar, sinew_cord), iron_sheet (made of iron_bar), hunter_helm (made of iron_bar, padded_lining), machine_trap (made of chain_net, cog_assembly, iron_bar).<br>It has nothing written on it.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (94 HP remaining) |
| 27 | `enter cellar` | 无 | 无 | 无 | I entered cellar.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining) |
| 28 | `store 1 hellfire_bomb inventory` | 无 | 无 | 无 | I stored 1 hellfire_bomb in my inventory.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (90 HP remaining) |
| 29 | `take out hellcoal scout_satchel_0` | 无 | 无 | 无 | I took out hellcoal from scout_satchel_0.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (88 HP remaining) |
| 30 | `inspect inventory` | 无 | 无 | 无 | I inspected my inventory.<br>It contains: 1 rubble, 2 hellcoal, 1 hellfire_bomb (capacity: 5/20).<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining) |
| 31 | `enter courtyard` | 无 | 无 | 无 | I entered courtyard.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (84 HP remaining) |
| 32 | `inspect crucible` | 无 | 无 | 无 | I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.<br>It can be used to craft: None.<br>It has nothing written on it.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (82 HP remaining) |
| 33 | `inspect war_bench` | 无 | 无 | 无 | I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.<br>It can be used to craft: None.<br>It has nothing written on it.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining) |
| 34 | `enter cellar` | 无 | 无 | 无 | I entered cellar.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (78 HP remaining) |
| 35 | `talk to olivia_grant` | 无 | 无 | 无 | I talked to olivia_grant.<br>olivia_grant says: I'm a helpful guide who tracks your side quest progress. Your current tasks are:<br>- [collect]: No task available<br>- craft a hellcoal_concentrate (reward: 4 coins)<br>- [talk]: No task available<br>- [trade]: No task available<br><br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (76 HP remaining) |
| 36 | `inspect crown_shard` | 无 | 无 | 无 | I inspected crown_shard: A broken fragment of an old kingdom's crown coin, still accepted as currency among the allied ruins.<br>It can be used to craft: None.<br>It has nothing written on it.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (74 HP remaining) |
| 37 | `enter courtyard` | 无 | 无 | 无 | I entered courtyard.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (72 HP remaining) |
| 38 | `inspect scout_satchel_0` | 无 | 无 | 无 | I inspected scout_satchel_0: A worn leather satchel issued to every hunter of devil-forged machines.<br>It contains: 1 rubble, 2 hellcoal, 1 hellfire_bomb (capacity: 5/20).<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (70 HP remaining) |
| 39 | `craft 2 rubble_chunk` | 无 | 无 | 无 | Only enough ingredients to craft 1 rubble_chunk.<br>I successfully crafted 1 rubble_chunk. It is now on the ground.<br><br>The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (68 HP remaining) |
