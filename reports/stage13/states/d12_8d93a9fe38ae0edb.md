# 冻结状态 d12_8d93a9fe38ae0edb

目标：`craft 1 fiend_helm`。来源 Stage 11 / E1 / `sequence-303b2d8fdefd2859-E1-d560807b7e4b`，零基行号 8，剩余 32 动作。

[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。

## 遗漏解释

检查 hellcoal 没有新增必要配方。有效路线先进入 courtyard，再制作和检查 brimite_ingot，共三步。移动本身是合法准备，不能仅凭第一步没有知识就称该方向无用。

```json
{
  "A": {
    "supported": false,
    "level": "native_counterfactual",
    "meaning": "unconnected public entry yields necessary new knowledge; actual raw/intermediate identity not inferred by policy",
    "candidates": []
  },
  "B": {
    "supported": true,
    "level": "native_counterfactual",
    "meaning": "multi-action useful alternatives exist; unavoidable only when minimum preparation >0",
    "unavoidable_within_observed_menu": true,
    "minimum_preparation_actions": 2
  },
  "C": {
    "supported": true,
    "level": "public_observation_and_native_counterfactual",
    "meaning": "some useful alternatives require transport/acquisition or encounter a rejection; this alone does not prove S1 could not choose another immediate candidate",
    "evidence": [
      {
        "candidate_id": "c_fe960f3c0293",
        "initial_public_condition": {
          "action": "enter courtyard",
          "status": "UNKNOWN",
          "conditions": [
            {
              "kind": "route",
              "status": "UNKNOWN",
              "evidence": {
                "neighbors": [
                  "barracks",
                  "courtyard"
                ],
                "guard": "UNLOCKED"
              },
              "observed_step": 18,
              "valid_until": "relevant public condition changes"
            }
          ]
        },
        "preparatory_first_action": "enter courtyard",
        "native_rejections": 0
      }
    ]
  },
  "D": {
    "supported": false,
    "level": "unproven",
    "meaning": "only count when exact frozen base proposal branch is useful and S1 override is not",
    "override_observed": true,
    "base_proposal_useful": false
  },
  "E": {
    "supported": false,
    "level": "public_observation_proxy",
    "meaning": "sustained same public recipe component without new publicly connected recipe; causal overexploitation is not established",
    "weaker_known_branch_action_observed": true
  },
  "F": {
    "supported": true,
    "level": "native_counterfactual_cost",
    "meaning": "actual useful branch uses >=3 actions or consumes resources/exposes loss; scarcity and net full-task harm remain untested",
    "candidates": [
      "c_fe960f3c0293"
    ]
  }
}
```
## 决策时公开证据

```json
{
  "objective": "Obtain at least 2 fiend_helm in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
  "target_action": "craft 1 fiend_helm",
  "current": {
    "location": "cellar",
    "hands": {
      "fiend_helm": 1.0
    },
    "ground": {
      "bandage_roll": 1.0,
      "hellcoal": 3.0,
      "sinew_cord": 1.0
    },
    "equipment": {
      "scout_satchel_0": 1.0
    },
    "neighbors": [
      "barracks",
      "courtyard"
    ]
  },
  "confirmed_recipe_relations": {
    "fiend_helm": {
      "ingredients": "UNKNOWN",
      "stations": [
        "war_bench",
        "crucible"
      ]
    },
    "brimite_ingot": {
      "ingredients": [
        "brimite_nugget"
      ],
      "stations": [
        "crucible"
      ]
    },
    "hellcoal_concentrate": {
      "ingredients": [
        "hellcoal",
        "devil_oil"
      ],
      "stations": "UNKNOWN"
    },
    "oil_flask": {
      "ingredients": [
        "devil_oil",
        "rubble_chunk"
      ],
      "stations": "UNKNOWN"
    },
    "cog_assembly": {
      "ingredients": [
        "cog",
        "devil_oil"
      ],
      "stations": "UNKNOWN"
    },
    "honed_blade": {
      "ingredients": [
        "forged_blade_blank",
        "devil_oil"
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
    "stitched_panel": {
      "ingredients": [
        "bandage_roll",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_maul": {
      "ingredients": [
        "ruin_blade",
        "wooden_rod",
        "bandage_roll"
      ],
      "stations": "UNKNOWN"
    },
    "war_strap": {
      "ingredients": [
        "sinew_cord",
        "bandage_roll"
      ],
      "stations": "UNKNOWN"
    }
  },
  "containers": {
    "scout_satchel_0": {
      "counts": {
        "brimite_nugget": 2.0
      },
      "load": null,
      "capacity": 20.0,
      "location": "cellar",
      "step": 2,
      "source": "public_container_inspection"
    }
  },
  "known_locations": {
    "barracks": {
      "objects": {
        "devil_oil": 1.0,
        "salvage_cloth": 1.0
      },
      "step": 16,
      "source": "public_ground_observation"
    },
    "cellar": {
      "objects": {
        "bandage_roll": 1.0,
        "hellcoal": 3.0,
        "sinew_cord": 1.0
      },
      "step": 18,
      "source": "public_ground_observation"
    },
    "courtyard": {
      "objects": {
        "crucible": 1.0,
        "war_bench": 1.0
      },
      "step": 7,
      "source": "public_ground_observation"
    }
  },
  "inspected": [
    "scout_satchel_0",
    "fiend_helm",
    "brimite_nugget",
    "devil_oil",
    "salvage_cloth",
    "bandage_roll"
  ],
  "produced": {},
  "recent_attempts": [
    {
      "action": "inspect fiend_helm",
      "target": "fiend_helm",
      "context": {
        "location": "barracks",
        "stations": {
          "war_bench": false,
          "crucible": false
        },
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 11,
      "retry_after_block": false
    },
    {
      "action": "inspect brimite_nugget",
      "target": "brimite_nugget",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected brimite_nugget: A dense nugget smelted from brimite ore, hot to the touch and faintly glowing.\nIt can be used to craft: brimite_ingot (made of brimite_nugget).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 12,
      "retry_after_block": false
    },
    {
      "action": "inspect devil_oil",
      "target": "devil_oil",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected devil_oil: A dark, viscous lubricant drained from a fallen war machine's joints. Burns with infernal heat.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil), oil_flask (made of devil_oil, rubble_chunk), cog_assembly (made of cog, devil_oil), honed_blade (made of forged_blade_blank, devil_oil), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 13,
      "retry_after_block": false
    },
    {
      "action": "inspect salvage_cloth",
      "target": "salvage_cloth",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 14,
      "retry_after_block": false
    },
    {
      "action": "craft 2 brimite_ingot",
      "target": "brimite_ingot",
      "context": {
        "location": "barracks",
        "stations": {
          "crucible": false
        },
        "materials": {
          "brimite_nugget": 2.0
        },
        "visible": false
      },
      "feedback": "Cannot craft brimite_ingot. Missing necessary crucible in the current area.",
      "state": "BLOCKED_BY_PRECONDITION",
      "meaningful_trial": false,
      "failure_type": "station",
      "retry_condition": "observed missing station present",
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": true,
      "step": 16,
      "retry_after_block": false
    },
    {
      "action": "inspect bandage_roll",
      "target": "bandage_roll",
      "context": {
        "location": "cellar",
        "stations": {},
        "materials": {
          "salvage_cloth": 0,
          "sinew_cord": 0
        },
        "visible": true
      },
      "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 18,
      "retry_after_block": false
    }
  ],
  "unresolved_public_nodes": [
    "fiend_helm"
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
  "brimite_ingot": {
    "lower_bound": 0,
    "exact": true
  },
  "brimite_nugget": {
    "lower_bound": 2.0,
    "exact": true
  },
  "charcoal_brick": {
    "lower_bound": 0,
    "exact": true
  },
  "cog": {
    "lower_bound": 0,
    "exact": true
  },
  "cog_assembly": {
    "lower_bound": 0,
    "exact": true
  },
  "devil_oil": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_helm": {
    "lower_bound": 1.0,
    "exact": true
  },
  "forged_blade_blank": {
    "lower_bound": 0,
    "exact": true
  },
  "hellcoal": {
    "lower_bound": 0,
    "exact": true
  },
  "hellcoal_concentrate": {
    "lower_bound": 0,
    "exact": true
  },
  "honed_blade": {
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
  "rubble_chunk": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_blade": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_maul": {
    "lower_bound": 0,
    "exact": true
  },
  "salvage_cloth": {
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
  "sinew_cord": {
    "lower_bound": 0,
    "exact": true
  },
  "stitched_panel": {
    "lower_bound": 0,
    "exact": true
  },
  "war_banner": {
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
  "wooden_rod": {
    "lower_bound": 0,
    "exact": true
  }
}
```

原始观察：

```text

Current Time: 0001-01-01 11:00:00
Current Location: Ashen Bastion, cellar

I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.
It can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).
It has nothing written on it.

I am holding 1 fiend_helm.
I have equipped 1 scout_satchel_0.
I see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.
I see no one nearby.

My level is 1.
My attack is at 10.
My defense is at 0.
My health is at 100.
My experience is at 10.

Neighboring areas: barracks, courtyard.

```

已知地点可见或历史观察到、尚未检查的对象（历史存在需重确认）：

```json
[
  "crucible",
  "hellcoal",
  "sinew_cord",
  "war_bench"
]
```

基础提案、FIFO 和实际 S1 选择：

```json
{
  "base_proposal": "enter courtyard",
  "FIFO": "inspect hellcoal",
  "actual_S1": "inspect hellcoal",
  "reason": "retain_F0",
  "mechanisms": {
    "exploration": {
      "reason": "unknown recipe/material link",
      "source": {
        "public_entity": "hellcoal",
        "missing_nodes": [
          "fiend_helm"
        ]
      },
      "spent": 9,
      "limit": 18
    }
  },
  "queue": [
    "fiend_helm"
  ],
  "graph": {}
}
```

公开特征、覆盖选择、分层入口账本：

```json
{
  "state_id": "d12_8d93a9fe38ae0edb",
  "choices": {
    "C0": "c_7b57c2d1e762",
    "C1": "c_7b57c2d1e762",
    "C2": "c_7b57c2d1e762",
    "C3": "c_7b57c2d1e762",
    "L": "c_7b57c2d1e762"
  },
  "features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 8,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": false,
    "uninspected_independent_entry_intents": 1,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": false,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": null,
    "s1_estimated_actions": 1,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 32
  },
  "entry_ledger": [
    {
      "candidate_id": "c_7b57c2d1e762",
      "intent": [
        "inspect",
        "hellcoal"
      ],
      "target": "hellcoal",
      "entry_states": [
        "unconnected_uninspected_entry"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": true,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect hellcoal",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 0
    },
    {
      "candidate_id": "c_f95fd9e12df4",
      "intent": [
        "craft_then_inspect",
        "hellcoal_concentrate"
      ],
      "target": "hellcoal_concentrate",
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
      "first_action": "store 3 hellcoal inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 1
    },
    {
      "candidate_id": "c_c53ac1f74f40",
      "intent": [
        "primitive",
        "enter courtyard"
      ],
      "target": "courtyard",
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
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "enter courtyard",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 2
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
      "first_action": "enter barracks",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 3
    },
    {
      "candidate_id": "c_334ffca58064",
      "intent": [
        "craft_then_inspect",
        "war_parchment"
      ],
      "target": "war_parchment",
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
      "first_action": "enter barracks",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 4
    },
    {
      "candidate_id": "c_64d1c15df952",
      "intent": [
        "inspect",
        "hellcoal"
      ],
      "target": "hellcoal",
      "entry_states": [
        "unconnected_uninspected_entry"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": true,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect hellcoal",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 5
    },
    {
      "candidate_id": "c_9a5fdfafa653",
      "intent": [
        "inspect",
        "crucible"
      ],
      "target": "crucible",
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
      "public_recipe_support": false,
      "station": true,
      "container": false,
      "first_action": "enter courtyard",
      "condition": "UNKNOWN",
      "estimated_actions": 2,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 6
    },
    {
      "candidate_id": "c_3005d7648aa4",
      "intent": [
        "craft_then_inspect",
        "war_strap"
      ],
      "target": "war_strap",
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
      "first_action": "store 1 sinew_cord inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 7
    },
    {
      "candidate_id": "c_fe960f3c0293",
      "intent": [
        "craft_then_inspect",
        "brimite_ingot"
      ],
      "target": "brimite_ingot",
      "entry_states": [
        "previous_blocked_attempt"
      ],
      "last_attempt_index": 5,
      "last_feedback": "Cannot craft brimite_ingot. Missing necessary crucible in the current area.",
      "attempts": 1,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "enter courtyard",
      "condition": "UNKNOWN",
      "estimated_actions": 3,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 8
    },
    {
      "candidate_id": "c_d6a4a748f3ca",
      "intent": [
        "craft_then_inspect",
        "stitched_panel"
      ],
      "target": "stitched_panel",
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
      "first_action": "store 1 bandage_roll inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 9
    },
    {
      "candidate_id": "c_c9ee531b4a5f",
      "intent": [
        "inspect",
        "fiend_helm"
      ],
      "target": "fiend_helm",
      "entry_states": [
        "inspected_no_new_public_recipe",
        "public_necessary_node"
      ],
      "last_attempt_index": 0,
      "last_feedback": "I inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect fiend_helm",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 10
    },
    {
      "candidate_id": "c_3f33cf002d85",
      "intent": [
        "inspect",
        "war_bench"
      ],
      "target": "war_bench",
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
      "public_recipe_support": false,
      "station": true,
      "container": false,
      "first_action": "enter courtyard",
      "condition": "UNKNOWN",
      "estimated_actions": 2,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 11
    },
    {
      "candidate_id": "c_ff3dc4ae7a9a",
      "intent": [
        "inspect",
        "sinew_cord"
      ],
      "target": "sinew_cord",
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
      "first_action": "inspect sinew_cord",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 12
    }
  ],
  "public_input_digest": "dd2a781c9571384caf5b4294e952d01b800850f7f0f244f0939180f0028bfa57",
  "single_supplement_max_actions": 4
}
```

## 历史进展依据

仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。


|行号|执行动作|公开新配方|持有量增加/制作/新地点|进展|未关联入口检查|
|---|---|---|---|---|---|
|0|inspect fiend_helm||False/False/False|False|False|
|1|inspect brimite_nugget|brimite_ingot|False/False/False|True|True|
|2|inspect devil_oil|cog_assembly,hellcoal_concentrate,honed_blade,oil_flask,scrap_lantern|False/False/False|True|True|
|3|inspect salvage_cloth|bandage_roll,oil_bomb,padded_lining,ruin_gauntlets,scout_satchel,scrap_helm,sinew_cord,war_banner,war_parchment|False/False/False|True|True|
|4|store 2 brimite_nugget inventory||True/False/False|True|False|
|5|craft 2 brimite_ingot||False/False/False|False|False|
|6|enter cellar||False/False/False|False|False|
|7|inspect bandage_roll|ruin_maul,stitched_panel,war_strap|False/False/False|True|False|

## 完整候选及公开依据

```json
[
  {
    "kind": "inspect",
    "target": "hellcoal",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "inspect hellcoal",
    "id": "c_7b57c2d1e762",
    "confirmed_connection": false,
    "next_action": "inspect hellcoal",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "hellcoal_concentrate",
    "category": "known_craft",
    "ingredients": [
      "hellcoal",
      "devil_oil"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_f95fd9e12df4",
    "confirmed_connection": false,
    "next_action": "store 3 hellcoal inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "primitive",
    "target": "courtyard",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "enter courtyard",
    "id": "c_c53ac1f74f40",
    "confirmed_connection": false,
    "next_action": "enter courtyard",
    "public_condition": "UNKNOWN"
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
    "next_action": "enter barracks",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "war_parchment",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_334ffca58064",
    "confirmed_connection": false,
    "next_action": "enter barracks",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "hellcoal",
    "category": "unconnected_visible",
    "evidence": "currently observed, not previously inspected",
    "id": "c_64d1c15df952",
    "confirmed_connection": false,
    "next_action": "inspect hellcoal",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "crucible",
    "category": "known_location",
    "location": "courtyard",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_9a5fdfafa653",
    "confirmed_connection": false,
    "next_action": "enter courtyard",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "war_strap",
    "category": "known_craft",
    "ingredients": [
      "sinew_cord",
      "bandage_roll"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_3005d7648aa4",
    "confirmed_connection": false,
    "next_action": "store 1 sinew_cord inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "brimite_ingot",
    "category": "known_craft",
    "ingredients": [
      "brimite_nugget"
    ],
    "stations": [
      "crucible"
    ],
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_fe960f3c0293",
    "confirmed_connection": false,
    "next_action": "enter courtyard",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "stitched_panel",
    "category": "known_craft",
    "ingredients": [
      "bandage_roll",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_d6a4a748f3ca",
    "confirmed_connection": false,
    "next_action": "store 1 bandage_roll inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "fiend_helm",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_c9ee531b4a5f",
    "confirmed_connection": true,
    "next_action": "inspect fiend_helm",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "war_bench",
    "category": "known_location",
    "location": "courtyard",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_3f33cf002d85",
    "confirmed_connection": false,
    "next_action": "enter courtyard",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "sinew_cord",
    "category": "unconnected_visible",
    "evidence": "currently observed, not previously inspected",
    "id": "c_ff3dc4ae7a9a",
    "confirmed_connection": false,
    "next_action": "inspect sinew_cord",
    "public_condition": "UNKNOWN"
  }
]
```

## J0 与 J3 配对及去重排名

```json
{
  "state_id": "d12_8d93a9fe38ae0edb",
  "family": "fiend_helm",
  "pair_class": "both_no_necessary_information",
  "same_exploration_intent": false,
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
    "stop": "inspection_attempt_completed",
    "candidate_id": "c_7b57c2d1e762",
    "intent": [
      "inspect",
      "hellcoal"
    ],
    "actions_trace": [
      "inspect hellcoal"
    ],
    "feedback_trace": [
      "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it."
    ],
    "native_new_necessary_rule_count": 0,
    "preparation_actions_until_first_necessary_recipe": null,
    "craft_actions": 0,
    "inspect_actions": 1,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [],
    "raw_entry_useful": false,
    "native_trace_digest": "3957e053daa4d3560b19f01f1d84a99e15d0b9c9dbb8a79e00dab3ae7360bceb"
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
    "candidate_id": "c_c53ac1f74f40",
    "intent": [
      "primitive",
      "enter courtyard"
    ],
    "actions_trace": [
      "enter courtyard"
    ],
    "feedback_trace": [
      "I entered courtyard."
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
    "public_known_necessary_executions": [],
    "raw_entry_useful": false,
    "native_trace_digest": "18b5977f97d1b614a23eb2ef7fc1b77ee39af3b78b380e75fa796525af6067bc"
  },
  "J3_raw_judgment": {
    "selected_candidate_id": "c_c53ac1f74f40",
    "ranked_candidate_ids": [
      "c_c53ac1f74f40",
      "c_3f33cf002d85",
      "c_9a5fdfafa653"
    ],
    "reason": "fiend_helm needs war_bench and crucible, both historically in courtyard; go there to confirm stations and attempt craft.",
    "hypothesized_connection": "Courtyard contains war_bench and crucible required to craft fiend_helm.",
    "confidence": 0.6,
    "expected_information": "Confirm presence of war_bench/crucible and enable craft attempt.",
    "alternative_if_failed": "c_7b57c2d1e762"
  },
  "public_features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 8,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": false,
    "uninspected_independent_entry_intents": 1,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": false,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": null,
    "s1_estimated_actions": 1,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 32
  },
  "J3_top3_original_ids": [
    "c_c53ac1f74f40",
    "c_3f33cf002d85",
    "c_9a5fdfafa653"
  ],
  "J3_distinct_ranked_ids": [
    "c_c53ac1f74f40",
    "c_3f33cf002d85",
    "c_9a5fdfafa653"
  ],
  "removed_alias_ids": [],
  "alias_groups": [
    {
      "intent": [
        "inspect",
        "hellcoal"
      ],
      "ids": [
        "c_7b57c2d1e762",
        "c_64d1c15df952"
      ],
      "different_information_outcomes": false
    }
  ],
  "distinct_top3_useful": false,
  "distinct_top2_useful": false,
  "effective_lower_rank_ids": [],
  "no_effective_direction_in_returned_distinct_ranks": true,
  "candidate_pool_has_opportunity": true,
  "new_connection_direction_relative_to_S1": true,
  "new_connection_useful_native_supported": false,
  "public_evidence_class": "known_station_prerequisite_only",
  "co_mentioned_public_recipe_edges": [],
  "co_mention_is_not_entailment_or_proof_of_reasoning": true,
  "mentioned_public_goal_station_requirements": [
    "war_bench",
    "crucible"
  ],
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

### c_7b57c2d1e762

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
  "candidate_id": "c_7b57c2d1e762",
  "intent": [
    "inspect",
    "hellcoal"
  ],
  "actions_trace": [
    "inspect hellcoal"
  ],
  "feedback_trace": [
    "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "3957e053daa4d3560b19f01f1d84a99e15d0b9c9dbb8a79e00dab3ae7360bceb"
}
```

第 1 步：`inspect hellcoal`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.
It can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).
It has nothing written on it.
```
### c_f95fd9e12df4

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
  "candidate_id": "c_f95fd9e12df4",
  "intent": [
    "craft_then_inspect",
    "hellcoal_concentrate"
  ],
  "actions_trace": [
    "store 3 hellcoal inventory",
    "enter barracks",
    "store 1 devil_oil inventory",
    "craft 2 hellcoal_concentrate"
  ],
  "feedback_trace": [
    "I stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)",
    "I entered barracks.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)",
    "I stored 1 devil_oil in my inventory.\nI have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)",
    "Cannot craft hellcoal_concentrate. Missing necessary crucible in the current area.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)"
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "d8c8bb06e84607b0f7be4d4e721007366949e5521ba4490a64f5e974074884c2"
}
```

第 1 步：`store 3 hellcoal inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 3 hellcoal in my inventory.
I have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)
The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)
```

第 2 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.

The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)
```

第 3 步：`store 1 devil_oil inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 devil_oil in my inventory.
I have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
The malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)
```

第 4 步：`craft 2 hellcoal_concentrate`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft hellcoal_concentrate. Missing necessary crucible in the current area.

The malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)
```
### c_c53ac1f74f40

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
  "candidate_id": "c_c53ac1f74f40",
  "intent": [
    "primitive",
    "enter courtyard"
  ],
  "actions_trace": [
    "enter courtyard"
  ],
  "feedback_trace": [
    "I entered courtyard."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "18b5977f97d1b614a23eb2ef7fc1b77ee39af3b78b380e75fa796525af6067bc"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```
### c_973aea1af0e4

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
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
    "enter barracks",
    "store 1 salvage_cloth inventory",
    "enter cellar",
    "store 1 sinew_cord inventory"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "I entered cellar.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)"
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "9e41edc4cd8f7b8db8cc917c64839932983194fa09af5eef40b760cd57f9f4fc"
}
```

第 1 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 2 步：`store 1 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 salvage_cloth in my inventory.
olivia_grant enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 3 coins!
Talk to olivia_grant to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 3 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 4 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```
### c_334ffca58064

```json
{
  "actions": 3,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_334ffca58064",
  "intent": [
    "craft_then_inspect",
    "war_parchment"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 salvage_cloth inventory",
    "craft 2 war_parchment"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "c5d6bb36669afb1d2d030b2cdf823ed142368e9642d1aaae13822d943610e1d0"
}
```

第 1 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 2 步：`store 1 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 salvage_cloth in my inventory.
olivia_grant enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 3 coins!
Talk to olivia_grant to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 3 步：`craft 2 war_parchment`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.
```
### c_64d1c15df952

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
  "candidate_id": "c_64d1c15df952",
  "intent": [
    "inspect",
    "hellcoal"
  ],
  "actions_trace": [
    "inspect hellcoal"
  ],
  "feedback_trace": [
    "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "3957e053daa4d3560b19f01f1d84a99e15d0b9c9dbb8a79e00dab3ae7360bceb"
}
```

第 1 步：`inspect hellcoal`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.
It can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).
It has nothing written on it.
```
### c_9a5fdfafa653

```json
{
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_9a5fdfafa653",
  "intent": [
    "inspect",
    "crucible"
  ],
  "actions_trace": [
    "enter courtyard",
    "inspect crucible"
  ],
  "feedback_trace": [
    "I entered courtyard.",
    "I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "21b1838c4aebf600970002d0a260acc52c49df636f9d952f16f655a36c56269b"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 2 步：`inspect crucible`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.
It can be used to craft: None.
It has nothing written on it.
```
### c_3005d7648aa4

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
  "candidate_id": "c_3005d7648aa4",
  "intent": [
    "craft_then_inspect",
    "war_strap"
  ],
  "actions_trace": [
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap",
    "enter courtyard"
  ],
  "feedback_trace": [
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "Cannot craft war_strap. Missing necessary war_bench in the current area.",
    "I entered courtyard."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "fe2a2ca18144711e00f857cabb3fc95802a73f97e13e27fd9ce0bb0ae9a82bd8"
}
```

第 1 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 2 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 3 步：`craft 2 war_strap`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft war_strap. Missing necessary war_bench in the current area.
```

第 4 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```
### c_fe960f3c0293

```json
{
  "actions": 3,
  "new_key_recipes": [
    "fiend_alloy"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_fe960f3c0293",
  "intent": [
    "craft_then_inspect",
    "brimite_ingot"
  ],
  "actions_trace": [
    "enter courtyard",
    "craft 2 brimite_ingot",
    "inspect brimite_ingot"
  ],
  "feedback_trace": [
    "I entered courtyard.",
    "Only enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.",
    "I inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.\nIt can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 2,
  "craft_actions": 1,
  "inspect_actions": 1,
  "consumption": {
    "brimite_nugget": 2
  },
  "production": {
    "brimite_ingot": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "a77013eb706f8a3c1b8e662ca19c9d586fde2977627ca289693859dfb7a09e5b"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 2 步：`craft 2 brimite_ingot`；拒绝=False；累计必要配方=[]；消耗={"brimite_nugget": 2}；环境损失={}。

```text
Only enough ingredients to craft 1 brimite_ingot.
I successfully crafted 1 brimite_ingot. It is now on the ground.
```

第 3 步：`inspect brimite_ingot`；拒绝=False；累计必要配方=["fiend_alloy"]；消耗={}；环境损失={}。

```text
I inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.
It can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).
It has nothing written on it.
```
### c_d6a4a748f3ca

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
  "candidate_id": "c_d6a4a748f3ca",
  "intent": [
    "craft_then_inspect",
    "stitched_panel"
  ],
  "actions_trace": [
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel",
    "enter courtyard"
  ],
  "feedback_trace": [
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
    "I entered courtyard."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "d0e6de71a6e2eec05cf422bcd8ef54b9edf5828756e47cfa99969e8e5e0c8bca"
}
```

第 1 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 2 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 3 步：`craft 2 stitched_panel`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft stitched_panel. Missing necessary war_bench in the current area.
```

第 4 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```
### c_c9ee531b4a5f

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
  "candidate_id": "c_c9ee531b4a5f",
  "intent": [
    "inspect",
    "fiend_helm"
  ],
  "actions_trace": [
    "inspect fiend_helm"
  ],
  "feedback_trace": [
    "I inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it."
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
  "native_trace_digest": "8958c5e066ff68678e4cb773f824a7b0c22e7a6999c3f03bee82598952cfafa7"
}
```

第 1 步：`inspect fiend_helm`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.
It can be used to craft: None.
It has nothing written on it.
```
### c_3f33cf002d85

```json
{
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_3f33cf002d85",
  "intent": [
    "inspect",
    "war_bench"
  ],
  "actions_trace": [
    "enter courtyard",
    "inspect war_bench"
  ],
  "feedback_trace": [
    "I entered courtyard.",
    "I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "251649f7162ecb470f49799aaf920c6c02932956ade482a1fcc6670a00225ec3"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 2 步：`inspect war_bench`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.
It can be used to craft: None.
It has nothing written on it.
```
### c_ff3dc4ae7a9a

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
  "candidate_id": "c_ff3dc4ae7a9a",
  "intent": [
    "inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "inspect sinew_cord"
  ],
  "feedback_trace": [
    "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "16cb6cd37190ac1778212ef4d9895be6d069f4f5b4451b064def5526db38ed4d"
}
```

第 1 步：`inspect sinew_cord`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.
It can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).
It has nothing written on it.
```

## 本轮零 API 补充

[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。

### truncation_sensitivity / c_f95fd9e12df4

```json
{
  "actions": 8,
  "new_key_recipes": [
    "fiend_alloy"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_f95fd9e12df4",
  "intent": [
    "craft_then_inspect",
    "hellcoal_concentrate"
  ],
  "actions_trace": [
    "store 3 hellcoal inventory",
    "enter barracks",
    "store 1 devil_oil inventory",
    "craft 2 hellcoal_concentrate",
    "enter cellar",
    "enter courtyard",
    "craft 2 hellcoal_concentrate",
    "inspect hellcoal_concentrate"
  ],
  "feedback_trace": [
    "I stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)",
    "I entered barracks.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)",
    "I stored 1 devil_oil in my inventory.\nI have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)",
    "Cannot craft hellcoal_concentrate. Missing necessary crucible in the current area.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)",
    "I entered cellar.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (74 HP remaining)",
    "I entered courtyard.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (68 HP remaining)",
    "Only enough ingredients to craft 1 hellcoal_concentrate.\nI successfully crafted 1 hellcoal_concentrate. It is now on the ground.\n\nSide quest completed: craft a hellcoal_concentrate\nYou earned 4 coins!\nTalk to olivia_grant to see your updated tasks.",
    "I inspected hellcoal_concentrate: Compressed hellcoal reduced to a volatile paste, used to temper devil-forged alloys.\nIt can be used to craft: hellfire_bomb (made of hellcoal_concentrate, oil_flask, iron_bar), suppression_charge (made of hellcoal_concentrate, cog_assembly, oil_flask), fiend_alloy (made of brimite_ingot, hellcoal_concentrate), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 7,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "devil_oil": 1,
    "hellcoal": 3
  },
  "production": {
    "hellcoal_concentrate": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "5584ec1e49411daa0de901b68b8a5b6cbe607eaf6f7b6797ce46a09212bb72a9"
}
```
### truncation_sensitivity / c_973aea1af0e4

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
  "candidate_id": "c_973aea1af0e4",
  "intent": [
    "craft_then_inspect",
    "scout_satchel"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 salvage_cloth inventory",
    "enter cellar",
    "store 1 sinew_cord inventory",
    "craft 2 scout_satchel",
    "enter courtyard",
    "craft 2 scout_satchel"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "I entered cellar.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft scout_satchel. Missing necessary war_bench in the current area.",
    "I entered courtyard.",
    "Cannot craft a single scout_satchel. Do not have sufficient amount of necessary ingredients."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "94a401f871e9000bc3282d0acbfd78b82293d5fb305aaed957e42e9f479a5410"
}
```
### truncation_sensitivity / c_3005d7648aa4

```json
{
  "actions": 6,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": true,
  "unrelated_key_input_consumption": true,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_3005d7648aa4",
  "intent": [
    "craft_then_inspect",
    "war_strap"
  ],
  "actions_trace": [
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap",
    "enter courtyard",
    "craft 2 war_strap",
    "inspect war_strap"
  ],
  "feedback_trace": [
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "Cannot craft war_strap. Missing necessary war_bench in the current area.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 war_strap.\nI successfully crafted 1 war_strap. It is now on the ground.",
    "I inspected war_strap: A tough strap for securing armor plates and weapon grips.\nIt can be used to craft: timber_vest (made of timber_plate, wood_rivet, padded_lining, war_strap), fiend_cuirass (made of fiend_plate, fiend_rivet, padded_lining, war_strap), ruin_cuirass (made of ruin_plate, war_strap, padded_lining), demonhide_armor (made of fiend_scale_bundle, padded_lining, war_strap, war_engine_heart), timber_shield (made of timber_plate, wood_rivet, war_strap), fiend_halberd (made of fiend_alloy, iron_bar, wooden_rod, war_strap), fiend_shield (made of fiend_alloy_sheet, timber_plate, war_strap, fiend_rivet), hunter_shield (made of iron_sheet, timber_plate, war_strap), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), demonslayer (made of fiend_alloy, brimite_blade, war_engine_heart, war_strap), brimite_sword (made of brimite_blade, wooden_rod, war_strap), hunter_sword (made of honed_blade, wooden_rod, war_strap), iron_mace (made of iron_bar, wooden_rod, war_strap), war_pack (made of stitched_panel, war_strap, iron_bar), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), hunter_scale (made of scale_bundle, padded_lining, war_strap), ruin_plate (made of ruin_slab, war_strap).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "production": {
    "war_strap": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "7ac0eca6dc6068294e295ab2dc0868f7b0fc6c4fda241593b72f54f9de7a1d12"
}
```
### truncation_sensitivity / c_d6a4a748f3ca

```json
{
  "actions": 6,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_d6a4a748f3ca",
  "intent": [
    "craft_then_inspect",
    "stitched_panel"
  ],
  "actions_trace": [
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel",
    "enter courtyard",
    "craft 2 stitched_panel",
    "inspect stitched_panel"
  ],
  "feedback_trace": [
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 stitched_panel.\nI successfully crafted 1 stitched_panel. It is now on the ground.",
    "I inspected stitched_panel: A reinforced cloth panel stitched for field armor assembly.\nIt can be used to craft: war_pack (made of stitched_panel, war_strap, iron_bar), padded_lining (made of stitched_panel, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "production": {
    "stitched_panel": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "b7e827afef4d1313010268efaee1c07c723ab128468510b638a5032c88d5cae5"
}
```

## 公开文本新颖性独立审计

将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。

```json
{
  "initial_public_text_necessary_recipes": [
    "brimite_ingot",
    "hellcoal_concentrate",
    "padded_lining",
    "stitched_panel"
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
