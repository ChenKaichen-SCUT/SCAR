# 冻结状态 d12_edea7c24b75cf3bb

目标：`craft 1 hunter_gauntlets`。来源 Stage 10 / S1 / `sequence-d0606cf4af2df919-S1-c3876e4fe87c`，零基行号 18，剩余 22 动作。

[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。

## 决策时公开证据

```json
{
  "objective": "Obtain at least 2 hunter_gauntlets in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
  "target_action": "craft 1 hunter_gauntlets",
  "current": {
    "location": "courtyard",
    "hands": {
      "hunter_gauntlets": 1.0
    },
    "ground": {
      "crucible": 1.0,
      "war_bench": 1.0,
      "iron_nugget": 2.0
    },
    "equipment": {
      "scout_satchel_0": 1.0
    },
    "neighbors": [
      "cellar"
    ]
  },
  "confirmed_recipe_relations": {
    "hunter_gauntlets": {
      "ingredients": [
        "iron_bar",
        "war_strap",
        "sinew_cord"
      ],
      "stations": [
        "war_bench"
      ]
    },
    "bandage_roll": {
      "ingredients": [
        "salvage_cloth",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "oil_bomb": {
      "ingredients": [
        "oil_flask",
        "charcoal_brick",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "scout_satchel": {
      "ingredients": [
        "salvage_cloth",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "war_parchment": {
      "ingredients": [
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "sinew_cord": {
      "ingredients": [
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "war_banner": {
      "ingredients": [
        "salvage_cloth",
        "wooden_rod"
      ],
      "stations": "UNKNOWN"
    },
    "padded_lining": {
      "ingredients": [
        "stitched_panel",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_helm": {
      "ingredients": [
        "scrap_iron",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_gauntlets": {
      "ingredients": [
        "rubble_chunk",
        "war_strap",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_lantern": {
      "ingredients": [
        "scrap_iron",
        "devil_oil",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "stitched_panel": {
      "ingredients": [
        "bandage_roll",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "timber_sword": {
      "ingredients": [
        "scorched_plank",
        "wood_strip",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "spiked_club": {
      "ingredients": [
        "charred_timber",
        "rubble_chunk",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "war_strap": {
      "ingredients": [
        "sinew_cord",
        "bandage_roll"
      ],
      "stations": "UNKNOWN"
    },
    "war_codex": {
      "ingredients": [
        "field_journal",
        "sinew_cord",
        "fiend_strip"
      ],
      "stations": "UNKNOWN"
    },
    "cog_crossbow": {
      "ingredients": [
        "gearwork_frame",
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_spear": {
      "ingredients": [
        "knapped_edge",
        "wooden_rod",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "fiend_scale_bundle": {
      "ingredients": [
        "fiend_alloy_scale",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "scale_bundle": {
      "ingredients": [
        "iron_scale",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "siege_crate": {
      "ingredients": [
        "scorched_plank",
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "fiend_gauntlets": {
      "ingredients": [
        "fiend_alloy",
        "war_strap",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "padded_tunic": {
      "ingredients": [
        "padded_lining",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_buckler": {
      "ingredients": [
        "scrap_iron",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "repair_kit": {
      "ingredients": [
        "scrap_iron",
        "sinew_cord",
        "oil_flask"
      ],
      "stations": "UNKNOWN"
    },
    "warding_charm": {
      "ingredients": [
        "demon_core_shard",
        "sinew_cord",
        "hellcoal_concentrate"
      ],
      "stations": "UNKNOWN"
    },
    "field_journal": {
      "ingredients": [
        "war_parchment",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "chain_net": {
      "ingredients": [
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "iron_nugget": {
      "ingredients": [
        "scrap_iron"
      ],
      "stations": [
        "crucible"
      ]
    },
    "gate_cipher": {
      "ingredients": [
        "cog",
        "scrap_iron"
      ],
      "stations": "UNKNOWN"
    },
    "iron_bar": {
      "ingredients": [
        "iron_nugget"
      ],
      "stations": "UNKNOWN"
    }
  },
  "containers": {
    "scout_satchel_0": {
      "counts": {
        "salvage_cloth": 3.0
      },
      "load": 3.0,
      "capacity": 20.0,
      "location": "courtyard",
      "step": 27,
      "source": "public_container_inspection"
    }
  },
  "known_locations": {
    "barracks": {
      "objects": {
        "sinew_cord": 2.0
      },
      "step": 17,
      "source": "public_ground_observation"
    },
    "cellar": {
      "objects": {
        "crown_shard": 3.0
      },
      "step": 22,
      "source": "public_ground_observation"
    },
    "courtyard": {
      "objects": {
        "crucible": 1.0,
        "war_bench": 1.0,
        "iron_nugget": 2.0
      },
      "step": 28,
      "source": "public_ground_observation"
    }
  },
  "inspected": [
    "scout_satchel_0",
    "hunter_gauntlets",
    "salvage_cloth",
    "sinew_cord",
    "scrap_iron",
    "crown_shard",
    "crucible",
    "war_bench",
    "inventory",
    "iron_nugget"
  ],
  "produced": {
    "iron_nugget": 2
  },
  "recent_attempts": [
    {
      "action": "inspect scrap_iron",
      "target": "scrap_iron",
      "context": {
        "location": "cellar",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected scrap_iron: Bent iron fragments torn from a destroyed war machine's hull.\nIt can be used to craft: repair_kit (made of scrap_iron, sinew_cord, oil_flask), scrap_buckler (made of scrap_iron, sinew_cord), iron_nugget (made of scrap_iron), gate_cipher (made of cog, scrap_iron), scrap_helm (made of scrap_iron, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 19,
      "retry_after_block": false
    },
    {
      "action": "inspect crown_shard",
      "target": "crown_shard",
      "context": {
        "location": "cellar",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected crown_shard: A broken fragment of an old kingdom's crown coin, still accepted as currency among the allied ruins.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 21,
      "retry_after_block": false
    },
    {
      "action": "craft 2 iron_nugget",
      "target": "iron_nugget",
      "context": {
        "location": "cellar",
        "stations": {
          "crucible": false
        },
        "materials": {
          "scrap_iron": 2.0
        },
        "visible": false
      },
      "feedback": "Cannot craft iron_nugget. Missing necessary crucible in the current area.",
      "state": "BLOCKED_BY_PRECONDITION",
      "meaningful_trial": false,
      "failure_type": "station",
      "retry_condition": "observed missing station present",
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": true,
      "step": 22,
      "retry_after_block": false
    },
    {
      "action": "inspect crucible",
      "target": "crucible",
      "context": {
        "location": "courtyard",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 24,
      "retry_after_block": false
    },
    {
      "action": "inspect war_bench",
      "target": "war_bench",
      "context": {
        "location": "courtyard",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 25,
      "retry_after_block": false
    },
    {
      "action": "craft 2 iron_nugget",
      "target": "iron_nugget",
      "context": {
        "location": "courtyard",
        "stations": {
          "crucible": true
        },
        "materials": {
          "scrap_iron": 2.0
        },
        "visible": false
      },
      "feedback": "I successfully crafted 2 iron_nugget. It is now on the ground.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": true,
      "step": 26,
      "retry_after_block": true
    },
    {
      "action": "inspect inventory",
      "target": "inventory",
      "context": {
        "location": "courtyard",
        "stations": {},
        "materials": {},
        "visible": false
      },
      "feedback": "I inspected my inventory.\nIt contains: 3 salvage_cloth (capacity: 3/20).",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 27,
      "retry_after_block": false
    },
    {
      "action": "inspect iron_nugget",
      "target": "iron_nugget",
      "context": {
        "location": "courtyard",
        "stations": {
          "crucible": true
        },
        "materials": {
          "scrap_iron": 0
        },
        "visible": true
      },
      "feedback": "I inspected iron_nugget: A small smelted lump of iron recovered from scrap, a step toward war-grade metal.\nIt can be used to craft: iron_bar (made of iron_nugget).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 28,
      "retry_after_block": false
    }
  ],
  "unresolved_public_nodes": [
    "salvage_cloth",
    "scrap_iron"
  ],
  "uncertainty": "Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe."
}
```

公开持有量下界与是否精确（地面数量另见 current.ground；UNKNOWN 不补成 0）：

```json
{
  "bandage_roll": {
    "lower_bound": 0,
    "exact": true
  },
  "chain_net": {
    "lower_bound": 0,
    "exact": true
  },
  "charcoal_brick": {
    "lower_bound": 0,
    "exact": true
  },
  "charred_timber": {
    "lower_bound": 0,
    "exact": true
  },
  "cog": {
    "lower_bound": 0,
    "exact": true
  },
  "cog_crossbow": {
    "lower_bound": 0,
    "exact": true
  },
  "crucible": {
    "lower_bound": 0,
    "exact": true
  },
  "demon_core_shard": {
    "lower_bound": 0,
    "exact": true
  },
  "devil_oil": {
    "lower_bound": 0,
    "exact": true
  },
  "field_journal": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_alloy": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_alloy_scale": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_scale_bundle": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_strip": {
    "lower_bound": 0,
    "exact": true
  },
  "gate_cipher": {
    "lower_bound": 0,
    "exact": true
  },
  "gearwork_frame": {
    "lower_bound": 0,
    "exact": true
  },
  "hellcoal_concentrate": {
    "lower_bound": 0,
    "exact": true
  },
  "hunter_gauntlets": {
    "lower_bound": 1.0,
    "exact": true
  },
  "iron_bar": {
    "lower_bound": 0,
    "exact": true
  },
  "iron_nugget": {
    "lower_bound": 0,
    "exact": true
  },
  "iron_scale": {
    "lower_bound": 0,
    "exact": true
  },
  "knapped_edge": {
    "lower_bound": 0,
    "exact": true
  },
  "oil_bomb": {
    "lower_bound": 0,
    "exact": true
  },
  "oil_flask": {
    "lower_bound": 0,
    "exact": true
  },
  "padded_lining": {
    "lower_bound": 0,
    "exact": true
  },
  "padded_tunic": {
    "lower_bound": 0,
    "exact": true
  },
  "repair_kit": {
    "lower_bound": 0,
    "exact": true
  },
  "rubble_chunk": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_spear": {
    "lower_bound": 0,
    "exact": true
  },
  "salvage_cloth": {
    "lower_bound": 3.0,
    "exact": true
  },
  "scale_bundle": {
    "lower_bound": 0,
    "exact": true
  },
  "scorched_plank": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel_0": {
    "lower_bound": 1.0,
    "exact": true
  },
  "scrap_buckler": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_helm": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_iron": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_lantern": {
    "lower_bound": 0,
    "exact": true
  },
  "siege_crate": {
    "lower_bound": 0,
    "exact": true
  },
  "sinew_cord": {
    "lower_bound": 0,
    "exact": true
  },
  "spiked_club": {
    "lower_bound": 0,
    "exact": true
  },
  "stitched_panel": {
    "lower_bound": 0,
    "exact": true
  },
  "timber_sword": {
    "lower_bound": 0,
    "exact": true
  },
  "war_banner": {
    "lower_bound": 0,
    "exact": true
  },
  "war_bench": {
    "lower_bound": 0,
    "exact": true
  },
  "war_codex": {
    "lower_bound": 0,
    "exact": true
  },
  "war_parchment": {
    "lower_bound": 0,
    "exact": true
  },
  "war_strap": {
    "lower_bound": 0,
    "exact": true
  },
  "warding_charm": {
    "lower_bound": 0,
    "exact": true
  },
  "wood_strip": {
    "lower_bound": 0,
    "exact": true
  },
  "wooden_rod": {
    "lower_bound": 0,
    "exact": true
  }
}
```

原始观察：

```text

Current Time: 0001-01-01 12:40:00
Current Location: Ashen Bastion, courtyard

I inspected iron_nugget: A small smelted lump of iron recovered from scrap, a step toward war-grade metal.
It can be used to craft: iron_bar (made of iron_nugget).
It has nothing written on it.

I am holding 1 hunter_gauntlets.
I have equipped 1 scout_satchel_0.
I see 1 crucible, 1 war_bench, 2 iron_nugget near me.
I see no one nearby.

My level is 1.
My attack is at 10.
My defense is at 0.
My health is at 100.
My experience is at 20.

Neighboring areas: cellar.

```

已知地点可见或历史观察到、尚未检查的对象（历史存在需重确认）：

```json
[]
```

基础提案、FIFO 和实际 S1 选择：

```json
{
  "base_proposal": "pick up iron_nugget",
  "FIFO": "enter cellar",
  "actual_S1": "pick up iron_nugget",
  "reason": "preserve_supported_base_progress",
  "mechanisms": {},
  "queue": [
    "sinew_cord",
    "hunter_gauntlets",
    "iron_nugget",
    "iron_bar",
    "bandage_roll",
    "war_strap"
  ],
  "graph": {}
}
```

公开特征、覆盖选择、分层入口账本：

```json
{
  "state_id": "d12_edea7c24b75cf3bb",
  "choices": {
    "C0": "c_9d350462bb2d",
    "C1": "c_9d350462bb2d",
    "C2": "c_9d350462bb2d",
    "C3": "c_9d350462bb2d",
    "L": "c_9d350462bb2d"
  },
  "features": {
    "incomplete_public_dependencies": false,
    "unknown_goal_recipe": false,
    "public_necessary_knowledge_drought": 0,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 0,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": true,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": true,
    "j3_estimated_actions": null,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": true,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 22
  },
  "entry_ledger": [
    {
      "candidate_id": "c_9d350462bb2d",
      "intent": [
        "primitive",
        "pick up iron_nugget"
      ],
      "target": "iron_nugget",
      "entry_states": [
        "inspected_with_public_information",
        "previous_blocked_attempt",
        "public_necessary_node"
      ],
      "last_attempt_index": 17,
      "last_feedback": "I inspected iron_nugget: A small smelted lump of iron recovered from scrap, a step toward war-grade metal.\nIt can be used to craft: iron_bar (made of iron_nugget).\nIt has nothing written on it.",
      "attempts": 3,
      "inspected": true,
      "produced": true,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "pick up iron_nugget",
      "condition": "SUPPORTED",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 0
    },
    {
      "candidate_id": "c_973aea1af0e4",
      "intent": [
        "craft_then_inspect",
        "scout_satchel"
      ],
      "target": "scout_satchel",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "enter cellar",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 1
    },
    {
      "candidate_id": "c_8ecb614a6055",
      "intent": [
        "inspect",
        "salvage_cloth"
      ],
      "target": "salvage_cloth",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 3,
      "last_feedback": "I stored 3 salvage_cloth in my inventory.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
      "attempts": 2,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect salvage_cloth",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 2
    },
    {
      "candidate_id": "c_51d20e64a67f",
      "intent": [
        "craft_then_inspect",
        "sinew_cord"
      ],
      "target": "sinew_cord",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 2,
      "last_feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "craft 2 sinew_cord",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 3
    },
    {
      "candidate_id": "c_a31e0c0dfecd",
      "intent": [
        "craft_then_inspect",
        "bandage_roll"
      ],
      "target": "bandage_roll",
      "entry_states": [
        "public_necessary_node"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "enter cellar",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 4
    },
    {
      "candidate_id": "c_a8193d99a131",
      "intent": [
        "craft_then_inspect",
        "iron_bar"
      ],
      "target": "iron_bar",
      "entry_states": [
        "public_necessary_node"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "store 2 iron_nugget inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 5
    }
  ],
  "public_input_digest": "c63ace603334e323694548c849f36a7e45c5b2655c702edb948a3b1fb7739fa0",
  "single_supplement_max_actions": 4
}
```

## 历史进展依据

仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。


|行号|执行动作|公开新配方|持有量增加/制作/新地点|进展|未关联入口检查|
|---|---|---|---|---|---|
|0|inspect hunter_gauntlets||False/False/False|False|False|
|1|inspect salvage_cloth|bandage_roll,oil_bomb,padded_lining,ruin_gauntlets,scout_satchel,scrap_helm,scrap_lantern,sinew_cord,war_banner,war_parchment|False/False/False|True|True|
|2|inspect sinew_cord|chain_net,cog_crossbow,field_journal,fiend_gauntlets,fiend_scale_bundle,hunter_gauntlets,padded_tunic,repair_kit,ruin_spear,scale_bundle,scrap_buckler,siege_crate,spiked_club,stitched_panel,timber_sword,war_codex,war_strap,warding_charm|False/False/False|True|False|
|3|store 3 salvage_cloth inventory||True/False/False|True|False|
|4|craft 2 war_parchment||False/False/False|False|False|
|5|wait||False/False/False|False|False|
|6|wait||False/False/False|False|False|
|7|enter cellar||False/False/False|False|False|
|8|inspect scrap_iron|gate_cipher,iron_nugget|False/False/False|True|True|
|9|store 2 scrap_iron inventory||True/False/False|True|False|
|10|inspect crown_shard||False/False/False|False|True|
|11|craft 2 iron_nugget||False/False/False|False|False|
|12|enter courtyard||False/False/False|False|False|
|13|inspect crucible||False/False/False|False|False|
|14|inspect war_bench||False/False/False|False|False|
|15|craft 2 iron_nugget||False/True/False|True|False|
|16|inspect inventory||False/False/False|False|True|
|17|inspect iron_nugget|iron_bar|False/False/False|True|False|

## 完整候选及公开依据

```json
[
  {
    "kind": "primitive",
    "target": "iron_nugget",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "pick up iron_nugget",
    "id": "c_9d350462bb2d",
    "confirmed_connection": true,
    "next_action": "pick up iron_nugget",
    "public_condition": "SUPPORTED"
  },
  {
    "kind": "craft",
    "target": "scout_satchel",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_973aea1af0e4",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "salvage_cloth",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_8ecb614a6055",
    "confirmed_connection": true,
    "next_action": "inspect salvage_cloth",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "sinew_cord",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_51d20e64a67f",
    "confirmed_connection": true,
    "next_action": "craft 2 sinew_cord",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "bandage_roll",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_a31e0c0dfecd",
    "confirmed_connection": true,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "iron_bar",
    "category": "known_craft",
    "ingredients": [
      "iron_nugget"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_a8193d99a131",
    "confirmed_connection": true,
    "next_action": "store 2 iron_nugget inventory",
    "public_condition": "UNKNOWN"
  }
]
```

## J0 与 J3 配对及去重排名

```json
{
  "state_id": "d12_edea7c24b75cf3bb",
  "family": "hunter_gauntlets",
  "pair_class": "both_no_necessary_information",
  "same_exploration_intent": true,
  "J0": {
    "actions": 1,
    "new_key_recipes": [],
    "useful": false,
    "one_step_useful": false,
    "rejections": 0,
    "unrelated_craft": false,
    "unrelated_key_input_consumption": false,
    "environment_key_loss": false,
    "goal": false,
    "stop": "public_plan_complete_or_blocked",
    "candidate_id": "c_9d350462bb2d",
    "intent": [
      "primitive",
      "pick up iron_nugget"
    ],
    "actions_trace": [
      "pick up iron_nugget"
    ],
    "feedback_trace": [
      "I picked up iron_nugget.\nI have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)"
    ],
    "native_new_necessary_rule_count": 0,
    "preparation_actions_until_first_necessary_recipe": null,
    "craft_actions": 0,
    "inspect_actions": 0,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [
      "pick up iron_nugget"
    ],
    "raw_entry_useful": false,
    "native_trace_digest": "8643b46f4ebaf272f3ad02a973445db36e6e08c61ddc30d1c5729a70b456d9de"
  },
  "J3": {
    "actions": 1,
    "new_key_recipes": [],
    "useful": false,
    "one_step_useful": false,
    "rejections": 0,
    "unrelated_craft": false,
    "unrelated_key_input_consumption": false,
    "environment_key_loss": false,
    "goal": false,
    "stop": "public_plan_complete_or_blocked",
    "candidate_id": "c_9d350462bb2d",
    "intent": [
      "primitive",
      "pick up iron_nugget"
    ],
    "actions_trace": [
      "pick up iron_nugget"
    ],
    "feedback_trace": [
      "I picked up iron_nugget.\nI have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)"
    ],
    "native_new_necessary_rule_count": 0,
    "preparation_actions_until_first_necessary_recipe": null,
    "craft_actions": 0,
    "inspect_actions": 0,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [
      "pick up iron_nugget"
    ],
    "raw_entry_useful": false,
    "native_trace_digest": "8643b46f4ebaf272f3ad02a973445db36e6e08c61ddc30d1c5729a70b456d9de"
  },
  "J3_raw_judgment": {
    "selected_candidate_id": "c_9d350462bb2d",
    "ranked_candidate_ids": [
      "c_9d350462bb2d",
      "c_a8193d99a131",
      "c_51d20e64a67f"
    ],
    "reason": "Iron nuggets on ground are confirmed inputs for iron_bar, needed for hunter_gauntlets. Pick them up now.",
    "hypothesized_connection": "Picking up iron_nugget enables crafting iron_bar, a hunter_gauntlets ingredient.",
    "confidence": 0.7,
    "expected_information": "Whether nuggets can be held and iron_bar craftable.",
    "alternative_if_failed": "c_a8193d99a131"
  },
  "public_features": {
    "incomplete_public_dependencies": false,
    "unknown_goal_recipe": false,
    "public_necessary_knowledge_drought": 0,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 0,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": true,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": true,
    "j3_estimated_actions": null,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": true,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 22
  },
  "J3_top3_original_ids": [
    "c_9d350462bb2d",
    "c_a8193d99a131",
    "c_51d20e64a67f"
  ],
  "J3_distinct_ranked_ids": [
    "c_9d350462bb2d",
    "c_a8193d99a131",
    "c_51d20e64a67f"
  ],
  "removed_alias_ids": [],
  "alias_groups": [],
  "distinct_top3_useful": false,
  "distinct_top2_useful": false,
  "effective_lower_rank_ids": [],
  "no_effective_direction_in_returned_distinct_ranks": false,
  "candidate_pool_has_opportunity": false,
  "new_connection_direction_relative_to_S1": false,
  "new_connection_useful_native_supported": false,
  "public_evidence_class": "disclosed_recipe_or_dependency_direction",
  "co_mentioned_public_recipe_edges": [
    {
      "product": "hunter_gauntlets",
      "ingredient": "iron_bar"
    },
    {
      "product": "iron_bar",
      "ingredient": "iron_nugget"
    }
  ],
  "co_mention_is_not_entailment_or_proof_of_reasoning": true,
  "mentioned_public_goal_station_requirements": [],
  "unconnected_recipe_names_mentioned": [],
  "name_association_causality": "not identifiable from generated explanation alone; hypothesized downstream links remain hypotheses",
  "raw_entry_selected": false,
  "raw_entry_effective_top3": [],
  "actual_native_costs_diagnostic_only": {
    "J0": 1,
    "J3": 1,
    "difference": 0
  }
}
```

## 主窗口全部原生分支

含原菜单及 Stage12 的自由提案补充分支；没有删除失败。new_key_recipes 是截至该步的累计新增集合，不能跨步相加。goal 仅为本短分支末局部持有目标，绝不表示本轮完成正式长程闭环。

### c_9d350462bb2d

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_9d350462bb2d",
  "intent": [
    "primitive",
    "pick up iron_nugget"
  ],
  "actions_trace": [
    "pick up iron_nugget"
  ],
  "feedback_trace": [
    "I picked up iron_nugget.\nI have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)"
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [
    "pick up iron_nugget"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "8643b46f4ebaf272f3ad02a973445db36e6e08c61ddc30d1c5729a70b456d9de"
}
```

第 1 步：`pick up iron_nugget`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I picked up iron_nugget.
I have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)
```
### c_973aea1af0e4

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_973aea1af0e4",
  "intent": [
    "craft_then_inspect",
    "scout_satchel"
  ],
  "actions_trace": [
    "enter cellar",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 scout_satchel"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft scout_satchel. Missing necessary war_bench in the current area."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "785da2b80ba056c89ce8c6ca114c9346a42f287b53edb1cc968359e67262c3a1"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 2 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 3 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 4 步：`craft 2 scout_satchel`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft scout_satchel. Missing necessary war_bench in the current area.
```
### c_8ecb614a6055

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_8ecb614a6055",
  "intent": [
    "inspect",
    "salvage_cloth"
  ],
  "actions_trace": [
    "inspect salvage_cloth"
  ],
  "feedback_trace": [
    "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 1,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "a8df8e80aa9d133d76987ba944d7ed064f3a6ed0d0d6a647348d219b4094c163"
}
```

第 1 步：`inspect salvage_cloth`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.
It can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).
It has nothing written on it.
```
### c_51d20e64a67f

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_51d20e64a67f",
  "intent": [
    "craft_then_inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "craft 2 sinew_cord"
  ],
  "feedback_trace": [
    "I successfully crafted 2 sinew_cord. It is now on the ground."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {
    "salvage_cloth": 1
  },
  "production": {
    "sinew_cord": 2
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [
    "craft 2 sinew_cord"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "eac7f7cfefc769f26045620c24f73a2d0ce1b8e62918d61f092924375f87e379"
}
```

第 1 步：`craft 2 sinew_cord`；拒绝=False；累计必要配方=[]；消耗={"salvage_cloth": 1}；环境损失={}。

```text
I successfully crafted 2 sinew_cord. It is now on the ground.
```
### c_a31e0c0dfecd

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_a31e0c0dfecd",
  "intent": [
    "craft_then_inspect",
    "bandage_roll"
  ],
  "actions_trace": [
    "enter cellar",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 bandage_roll"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft bandage_roll. Missing necessary war_bench in the current area."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "5002bf150a00e7b70518de839442e66fcd428bb5577f82c7fda7ab37dfb57f97"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 2 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 3 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 4 步：`craft 2 bandage_roll`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft bandage_roll. Missing necessary war_bench in the current area.
```
### c_a8193d99a131

```json
{
  "actions": 3,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": true,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_a8193d99a131",
  "intent": [
    "craft_then_inspect",
    "iron_bar"
  ],
  "actions_trace": [
    "store 2 iron_nugget inventory",
    "craft 2 iron_bar",
    "inspect iron_bar"
  ],
  "feedback_trace": [
    "I stored 2 iron_nugget in my inventory.\nI have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)",
    "Only enough ingredients to craft 1 iron_bar.\nI successfully crafted 1 iron_bar. It is now on the ground.",
    "I inspected iron_bar: A smelted bar of iron pulled from the ruins, ready for forging into weapons against devil machines.\nIt can be used to craft: forged_blade_blank (made of iron_bar, wooden_rod), hellfire_bomb (made of hellcoal_concentrate, oil_flask, iron_bar), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), fiend_halberd (made of fiend_alloy, iron_bar, wooden_rod, war_strap), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), gearwork_frame (made of cog_assembly, iron_bar), iron_mace (made of iron_bar, wooden_rod, war_strap), war_pack (made of stitched_panel, war_strap, iron_bar), gate_blank (made of iron_bar), chain_net (made of iron_bar, sinew_cord), iron_sheet (made of iron_bar), hunter_helm (made of iron_bar, padded_lining), machine_trap (made of chain_net, cog_assembly, iron_bar).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 1,
  "consumption": {
    "iron_nugget": 2
  },
  "production": {
    "iron_bar": 1
  },
  "environment_loss_quantities": {
    "sinew_cord": 1
  },
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [
    "store 2 iron_nugget inventory",
    "craft 2 iron_bar"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "036639188c69d52c27f7dd6f7c72eb6f1a3a3e9044aa949d61fb4117a0811da3"
}
```

第 1 步：`store 2 iron_nugget inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 2 iron_nugget in my inventory.
I have acquired a new item: iron_nugget. It can be used to craft: iron_bar (2 iron_nugget)
```

第 2 步：`craft 2 iron_bar`；拒绝=False；累计必要配方=[]；消耗={"iron_nugget": 2}；环境损失={}。

```text
Only enough ingredients to craft 1 iron_bar.
I successfully crafted 1 iron_bar. It is now on the ground.
```

第 3 步：`inspect iron_bar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={"sinew_cord": 1}。

```text
I inspected iron_bar: A smelted bar of iron pulled from the ruins, ready for forging into weapons against devil machines.
It can be used to craft: forged_blade_blank (made of iron_bar, wooden_rod), hellfire_bomb (made of hellcoal_concentrate, oil_flask, iron_bar), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), fiend_halberd (made of fiend_alloy, iron_bar, wooden_rod, war_strap), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), gearwork_frame (made of cog_assembly, iron_bar), iron_mace (made of iron_bar, wooden_rod, war_strap), war_pack (made of stitched_panel, war_strap, iron_bar), gate_blank (made of iron_bar), chain_net (made of iron_bar, sinew_cord), iron_sheet (made of iron_bar), hunter_helm (made of iron_bar, padded_lining), machine_trap (made of chain_net, cog_assembly, iron_bar).
It has nothing written on it.
```

## 本轮零 API 补充

[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。

### truncation_sensitivity / c_973aea1af0e4

```json
{
  "actions": 7,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": true,
  "unrelated_key_input_consumption": true,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_973aea1af0e4",
  "intent": [
    "craft_then_inspect",
    "scout_satchel"
  ],
  "actions_trace": [
    "enter cellar",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 scout_satchel",
    "enter cellar",
    "enter courtyard",
    "craft 2 scout_satchel"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft scout_satchel. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 scout_satchel.\nI successfully crafted 1 scout_satchel. It is now on the ground.\nwilliam_brooks enters the area.\n\nSide quest completed: craft a scout_satchel\nYou earned 3 coins!\nTalk to william_brooks to see your updated tasks."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 0,
  "consumption": {
    "salvage_cloth": 3,
    "sinew_cord": 1
  },
  "production": {
    "scout_satchel": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {
    "salvage_cloth": 3,
    "sinew_cord": 1
  },
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "8840837e39dc2875288cad272e72f247b6374e1c26bec2e849f74090965da8ff"
}
```
### truncation_sensitivity / c_a31e0c0dfecd

```json
{
  "actions": 7,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 2,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_a31e0c0dfecd",
  "intent": [
    "craft_then_inspect",
    "bandage_roll"
  ],
  "actions_trace": [
    "enter cellar",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 bandage_roll",
    "enter cellar",
    "enter courtyard",
    "craft 2 bandage_roll"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft bandage_roll. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Cannot craft a single bandage_roll. Do not have sufficient amount of necessary ingredients."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 2,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "85cc1db258e0666d6dbee2f2e8e134812b714fe716490de360d0ca06ee84fdee"
}
```

## 公开文本新颖性独立审计

将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。

```json
{
  "initial_public_text_necessary_recipes": [
    "bandage_roll",
    "hunter_gauntlets",
    "iron_bar",
    "iron_nugget",
    "sinew_cord",
    "war_strap"
  ],
  "selected": {
    "C0": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C1": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C2": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C3": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "L": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "J3": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    }
  }
}
```
