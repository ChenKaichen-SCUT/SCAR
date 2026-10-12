# d12_8d93a9fe38ae0edb：craft 1 fiend_helm

来源：Stage11 / sequence-303b2d8fdefd2859-E1-d560807b7e4b / index 8。

## 当时的公开观察、知识和 STM5

```json
{
  "observation": {
    "step": 18,
    "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
  },
  "public_knowledge": {
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
  },
  "memory": [
    "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected devil_oil: A dark, viscous lubricant drained from a fallen war machine's joints. Burns with infernal heat.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil), oil_flask (made of devil_oil, rubble_chunk), cog_assembly (made of cog, devil_oil), honed_blade (made of forged_blade_blank, devil_oil), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 2 brimite_nugget, 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter courtyard\nExecuted action: inspect salvage_cloth",
    "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 2 brimite_nugget, 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter cellar\nExecuted action: store 2 brimite_nugget inventory",
    "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 2 brimite_nugget in my inventory.\nI have acquired a new item: brimite_nugget. It can be used to craft: brimite_ingot (2 brimite_nugget)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter courtyard\nExecuted action: craft 2 brimite_ingot",
    "\nCurrent Time: 0001-01-01 10:40:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft brimite_ingot. Missing necessary crucible in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter courtyard\nExecuted action: enter cellar",
    "\nCurrent Time: 0001-01-01 10:50:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n\nProposed: enter courtyard\nExecuted action: inspect bandage_roll"
  ]
}
```

## 原模型提案与两个规则参考

```json
{
  "historical_model_proposal": "enter courtyard",
  "rule_actions": {
    "J0": "inspect hellcoal",
    "J1": "enter courtyard"
  },
  "rule_decisions": {
    "J0": {
      "node": "fiend_helm",
      "action": "inspect hellcoal",
      "structured_action": "inspect hellcoal",
      "graph": {},
      "queue": [
        "fiend_helm"
      ],
      "resource_table": {
        "state": {
          "location": "cellar",
          "location_full": "Ashen Bastion, cellar",
          "hands": {
            "fiend_helm": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "bandage_roll": 1.0,
            "hellcoal": 3.0,
            "sinew_cord": 1.0
          },
          "neighbors": [
            "barracks",
            "courtyard"
          ],
          "step": 18,
          "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
          "public_goal": null
        },
        "places": {
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
        "links": {
          "barracks": [
            "cellar"
          ],
          "cellar": [
            "barracks",
            "courtyard"
          ],
          "courtyard": [
            "cellar"
          ]
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
        "inventory": "scout_satchel_0",
        "recipes": {
          "fiend_helm": {
            "ingredients": [],
            "quantities": null,
            "stations": [
              "war_bench",
              "crucible"
            ]
          },
          "brimite_ingot": {
            "quantities": null,
            "ingredients": [
              "brimite_nugget"
            ],
            "step": 12,
            "source": "public_inspection",
            "stations": [
              "crucible"
            ]
          },
          "hellcoal_concentrate": {
            "quantities": null,
            "ingredients": [
              "hellcoal",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "oil_flask": {
            "quantities": null,
            "ingredients": [
              "devil_oil",
              "rubble_chunk"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "cog_assembly": {
            "quantities": null,
            "ingredients": [
              "cog",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "honed_blade": {
            "quantities": null,
            "ingredients": [
              "forged_blade_blank",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "scrap_lantern": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "devil_oil",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "bandage_roll": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "sinew_cord"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "oil_bomb": {
            "quantities": null,
            "ingredients": [
              "oil_flask",
              "charcoal_brick",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "scout_satchel": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "sinew_cord"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "war_parchment": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "sinew_cord": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "war_banner": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "wooden_rod"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "padded_lining": {
            "quantities": null,
            "ingredients": [
              "stitched_panel",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "scrap_helm": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "ruin_gauntlets": {
            "quantities": null,
            "ingredients": [
              "rubble_chunk",
              "war_strap",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "stitched_panel": {
            "quantities": null,
            "ingredients": [
              "bandage_roll",
              "sinew_cord"
            ],
            "step": 18,
            "source": "public_inspection"
          },
          "ruin_maul": {
            "quantities": null,
            "ingredients": [
              "ruin_blade",
              "wooden_rod",
              "bandage_roll"
            ],
            "step": 18,
            "source": "public_inspection"
          },
          "war_strap": {
            "quantities": null,
            "ingredients": [
              "sinew_cord",
              "bandage_roll"
            ],
            "step": 18,
            "source": "public_inspection"
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
        "guards": {
          "barracks->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 17
          },
          "cellar->courtyard": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered courtyard.\nolivia_grant enters the area.\n\n=== SIDE QUESTS UNLOCKED ===\nSide quests are now available! Completing them will grant you coins.\nTalk to olivia_grant to see your current tasks.\n============================",
            "step": 7
          },
          "courtyard->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 8
          },
          "cellar->barracks": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered barracks.",
            "step": 9
          }
        },
        "observations": 60,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 fiend_helm",
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
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "inspect hellcoal",
        "base_action": "enter courtyard",
        "selected_action": "inspect hellcoal",
        "reason": "retain_F0",
        "override": true,
        "overlay_changed_F0": false,
        "conditions": [
          {
            "action": "inspect hellcoal",
            "status": "UNKNOWN",
            "conditions": [
              {
                "kind": "public_trial",
                "status": "UNKNOWN",
                "evidence": "no known negative condition",
                "observed_step": 18,
                "valid_until": "relevant public condition changes"
              }
            ]
          }
        ],
        "selected_meta": null,
        "stash_memory": {},
        "batch_rule": "inherited_F0_unchanged",
        "candidate_limit": 32
      }
    },
    "J1": {
      "node": "fiend_helm",
      "action": "enter courtyard",
      "structured_action": "enter courtyard",
      "graph": {},
      "queue": [
        "fiend_helm"
      ],
      "resource_table": {
        "state": {
          "location": "cellar",
          "location_full": "Ashen Bastion, cellar",
          "hands": {
            "fiend_helm": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "bandage_roll": 1.0,
            "hellcoal": 3.0,
            "sinew_cord": 1.0
          },
          "neighbors": [
            "barracks",
            "courtyard"
          ],
          "step": 18,
          "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
          "public_goal": null
        },
        "places": {
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
        "links": {
          "barracks": [
            "cellar"
          ],
          "cellar": [
            "barracks",
            "courtyard"
          ],
          "courtyard": [
            "cellar"
          ]
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
        "inventory": "scout_satchel_0",
        "recipes": {
          "fiend_helm": {
            "ingredients": [],
            "quantities": null,
            "stations": [
              "war_bench",
              "crucible"
            ]
          },
          "brimite_ingot": {
            "quantities": null,
            "ingredients": [
              "brimite_nugget"
            ],
            "step": 12,
            "source": "public_inspection",
            "stations": [
              "crucible"
            ]
          },
          "hellcoal_concentrate": {
            "quantities": null,
            "ingredients": [
              "hellcoal",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "oil_flask": {
            "quantities": null,
            "ingredients": [
              "devil_oil",
              "rubble_chunk"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "cog_assembly": {
            "quantities": null,
            "ingredients": [
              "cog",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "honed_blade": {
            "quantities": null,
            "ingredients": [
              "forged_blade_blank",
              "devil_oil"
            ],
            "step": 13,
            "source": "public_inspection"
          },
          "scrap_lantern": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "devil_oil",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "bandage_roll": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "sinew_cord"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "oil_bomb": {
            "quantities": null,
            "ingredients": [
              "oil_flask",
              "charcoal_brick",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "scout_satchel": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "sinew_cord"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "war_parchment": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "sinew_cord": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "war_banner": {
            "quantities": null,
            "ingredients": [
              "salvage_cloth",
              "wooden_rod"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "padded_lining": {
            "quantities": null,
            "ingredients": [
              "stitched_panel",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "scrap_helm": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "ruin_gauntlets": {
            "quantities": null,
            "ingredients": [
              "rubble_chunk",
              "war_strap",
              "salvage_cloth"
            ],
            "step": 14,
            "source": "public_inspection"
          },
          "stitched_panel": {
            "quantities": null,
            "ingredients": [
              "bandage_roll",
              "sinew_cord"
            ],
            "step": 18,
            "source": "public_inspection"
          },
          "ruin_maul": {
            "quantities": null,
            "ingredients": [
              "ruin_blade",
              "wooden_rod",
              "bandage_roll"
            ],
            "step": 18,
            "source": "public_inspection"
          },
          "war_strap": {
            "quantities": null,
            "ingredients": [
              "sinew_cord",
              "bandage_roll"
            ],
            "step": 18,
            "source": "public_inspection"
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
        "guards": {
          "barracks->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 17
          },
          "cellar->courtyard": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered courtyard.\nolivia_grant enters the area.\n\n=== SIDE QUESTS UNLOCKED ===\nSide quests are now available! Completing them will grant you coins.\nTalk to olivia_grant to see your current tasks.\n============================",
            "step": 7
          },
          "courtyard->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 8
          },
          "cellar->barracks": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered barracks.",
            "step": 9
          }
        },
        "observations": 61,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 fiend_helm",
      "reason": "stage11_known_forward_bridge",
      "mechanisms": {
        "exploration": {
          "reason": "stage11_known_forward_bridge",
          "source": {
            "public_recipe": {
              "quantities": null,
              "ingredients": [
                "brimite_nugget"
              ],
              "step": 12,
              "source": "public_inspection",
              "stations": [
                "crucible"
              ]
            },
            "unresolved_nodes": [
              "fiend_helm"
            ],
            "confirmed_goal_connection": false,
            "unknown_downstream_connection": true,
            "claim": "possible source of further rules, not a known hidden dependency"
          },
          "spent": 9,
          "limit": 18
        }
      },
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "enter courtyard",
        "base_action": "enter courtyard",
        "selected_action": "enter courtyard",
        "reason": "retain_F0",
        "override": false,
        "overlay_changed_F0": false,
        "conditions": [
          {
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
          }
        ],
        "selected_meta": null,
        "stash_memory": {},
        "batch_rule": "inherited_F0_unchanged",
        "candidate_limit": 32
      },
      "stage11": {
        "switches": {
          "goal_ranking": true,
          "timely_execution": false
        },
        "base_action": "enter courtyard",
        "S1_with_rank_candidate": "enter courtyard",
        "selected_action": "enter courtyard",
        "exploration_candidates": [
          {
            "action": "enter courtyard",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "brimite_ingot",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "brimite_nugget"
                ],
                "step": 12,
                "source": "public_inspection",
                "stations": [
                  "crucible"
                ]
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
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
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "store 3 hellcoal inventory",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "hellcoal_concentrate",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "hellcoal",
                  "devil_oil"
                ],
                "step": 13,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
              "action": "store 3 hellcoal inventory",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "container_access",
                  "status": "SUPPORTED",
                  "evidence": {
                    "container": "scout_satchel_0",
                    "current_access": true
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                },
                {
                  "kind": "transfer_source",
                  "status": "SUPPORTED",
                  "evidence": {
                    "current_held_and_ground": 3.0
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes"
                },
                {
                  "kind": "container_capacity",
                  "status": "UNKNOWN",
                  "evidence": {
                    "load": null,
                    "capacity": 20.0,
                    "item_volume": "UNKNOWN"
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter barracks",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "scout_satchel",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "salvage_cloth",
                  "sinew_cord"
                ],
                "step": 14,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
              "action": "enter barracks",
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
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "store 1 bandage_roll inventory",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "stitched_panel",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "bandage_roll",
                  "sinew_cord"
                ],
                "step": 18,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
              "action": "store 1 bandage_roll inventory",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "container_access",
                  "status": "SUPPORTED",
                  "evidence": {
                    "container": "scout_satchel_0",
                    "current_access": true
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                },
                {
                  "kind": "transfer_source",
                  "status": "SUPPORTED",
                  "evidence": {
                    "current_held_and_ground": 1.0
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes"
                },
                {
                  "kind": "container_capacity",
                  "status": "UNKNOWN",
                  "evidence": {
                    "load": null,
                    "capacity": 20.0,
                    "item_volume": "UNKNOWN"
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter barracks",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "war_parchment",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "salvage_cloth"
                ],
                "step": 14,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
              "action": "enter barracks",
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
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "store 1 sinew_cord inventory",
            "priority": 2,
            "kind": "known_forward_bridge",
            "target": "war_strap",
            "basis": {
              "public_recipe": {
                "quantities": null,
                "ingredients": [
                  "sinew_cord",
                  "bandage_roll"
                ],
                "step": 18,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "fiend_helm"
              ],
              "confirmed_goal_connection": false,
              "unknown_downstream_connection": true,
              "claim": "possible source of further rules, not a known hidden dependency"
            },
            "assessment": {
              "action": "store 1 sinew_cord inventory",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "container_access",
                  "status": "SUPPORTED",
                  "evidence": {
                    "container": "scout_satchel_0",
                    "current_access": true
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                },
                {
                  "kind": "transfer_source",
                  "status": "SUPPORTED",
                  "evidence": {
                    "current_held_and_ground": 1.0
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes"
                },
                {
                  "kind": "container_capacity",
                  "status": "UNKNOWN",
                  "evidence": {
                    "load": null,
                    "capacity": 20.0,
                    "item_volume": "UNKNOWN"
                  },
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "inspect hellcoal",
            "priority": 3,
            "kind": "inspect_public_object",
            "target": "hellcoal",
            "basis": {
              "confirmed_goal_connection": false,
              "unresolved_node": false,
              "actually_produced": false,
              "observed_material_source": true,
              "unknown_downstream_connection": true
            },
            "assessment": {
              "action": "inspect hellcoal",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "public_trial",
                  "status": "UNKNOWN",
                  "evidence": "no known negative condition",
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 0
          },
          {
            "action": "inspect sinew_cord",
            "priority": 3,
            "kind": "inspect_public_object",
            "target": "sinew_cord",
            "basis": {
              "confirmed_goal_connection": false,
              "unresolved_node": false,
              "actually_produced": false,
              "observed_material_source": true,
              "unknown_downstream_connection": true
            },
            "assessment": {
              "action": "inspect sinew_cord",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "public_trial",
                  "status": "UNKNOWN",
                  "evidence": "no known negative condition",
                  "observed_step": 18,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 0
          }
        ],
        "execution_candidates": [],
        "selected": {
          "action": "enter courtyard",
          "priority": 2,
          "kind": "known_forward_bridge",
          "target": "brimite_ingot",
          "basis": {
            "public_recipe": {
              "quantities": null,
              "ingredients": [
                "brimite_nugget"
              ],
              "step": 12,
              "source": "public_inspection",
              "stations": [
                "crucible"
              ]
            },
            "unresolved_nodes": [
              "fiend_helm"
            ],
            "confirmed_goal_connection": false,
            "unknown_downstream_connection": true,
            "claim": "possible source of further rules, not a known hidden dependency"
          },
          "assessment": {
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
          "eligible": true,
          "preparation_steps": 1
        },
        "public_goal_view": {
          "goal": "fiend_helm",
          "known_dependency_nodes": [
            "fiend_helm"
          ],
          "active_nodes": [
            "fiend_helm"
          ],
          "unresolved_recipe_nodes": [
            "fiend_helm"
          ],
          "nodes": {
            "fiend_helm": {
              "status": "BLOCKED",
              "required_floor": 2,
              "owned": {
                "lower_bound": 1.0,
                "exact": true
              },
              "known_recipe": false,
              "missing_inputs": [],
              "input_floors": {},
              "recipe": {
                "ingredients": [],
                "quantities": null,
                "stations": [
                  "war_bench",
                  "crucible"
                ]
              },
              "assessment": {
                "action": "craft 1 fiend_helm",
                "status": "REJECT",
                "conditions": [
                  {
                    "kind": "unchanged_failure",
                    "status": "REJECT",
                    "evidence": {
                      "action": "craft 1 fiend_helm",
                      "context": {
                        "ingredients": [],
                        "materials": {},
                        "stations": {
                          "war_bench": 0,
                          "crucible": 0
                        },
                        "unknown_recipe_carried": {
                          "hands": {
                            "fiend_helm": 1.0
                          },
                          "equipment": {
                            "scout_satchel_0": 1.0
                          },
                          "containers": {
                            "scout_satchel_0": {
                              "brimite_nugget": 2.0
                            }
                          }
                        }
                      },
                      "feedback": "Cannot craft fiend_helm. Missing necessary war_bench, crucible in the current area.",
                      "step": 10
                    },
                    "observed_step": 18,
                    "valid_until": "relevant public condition changes"
                  },
                  {
                    "kind": "station",
                    "status": "REJECT",
                    "evidence": {
                      "required": [
                        "war_bench",
                        "crucible"
                      ],
                      "current_ground": {
                        "bandage_roll": 1.0,
                        "hellcoal": 3.0,
                        "sinew_cord": 1.0
                      }
                    },
                    "observed_step": 18,
                    "valid_until": "relevant public condition changes"
                  },
                  {
                    "kind": "recipe",
                    "status": "UNKNOWN",
                    "evidence": "ingredient names not publicly disclosed",
                    "observed_step": 18,
                    "valid_until": "relevant public condition changes"
                  }
                ]
              },
              "quantity_certainty": "UNKNOWN",
              "readiness_scope": "observed conditions and inherited FIFO floor; never native legality guarantee"
            }
          },
          "edges": {
            "fiend_helm": []
          },
          "unknown_scope": "missing recipe may be a raw material; possible bridges are not graph edges"
        },
        "queue": [
          "fiend_helm"
        ],
        "extra_model_calls": 0,
        "inherited_batch_rule": true,
        "candidate_limit": 32,
        "node_limit": 64
      }
    }
  }
}
```

## 同一公开候选池

```json
{
  "retained": [
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
  ],
  "cropped": []
}
```

## 新模型判断（主判断与预先指定的重复分开）

```json
[
  {
    "state_id": "d12_8d93a9fe38ae0edb",
    "method": "J3",
    "replicate": 0,
    "status": "completed",
    "parsed": {
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
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.0016642200000000001,
    "charged_or_reserved_usd": 0.0016642200000000001
  },
  {
    "state_id": "d12_8d93a9fe38ae0edb",
    "method": "J2",
    "replicate": 0,
    "status": "completed",
    "parsed": {
      "reasoning": "The fiend_helm recipe is unknown, and crafting it requires a war_bench and crucible, which were last seen in the courtyard. I should go to the courtyard to attempt crafting there, since those stations are the known prerequisite. I'll first visit the courtyard to confirm the stations are present before crafting.",
      "action": "enter courtyard"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.00017282400000000002,
    "charged_or_reserved_usd": 0.00017282400000000002
  }
]
```

## 四方法的主选择与真实结果

| 方法 | 候选/提案 | 实际短分支 | 新增必要配方 | 原生拒绝数 | 停止原因 |
| --- | --- | --- | --- | --- | --- |
| J0 | c_7b57c2d1e762 | ["inspect hellcoal"] | [] | 0 | inspection_attempt_completed |
| J1 | c_c53ac1f74f40 | ["enter courtyard"] | [] | 0 | public_plan_complete_or_blocked |
| J2 | c_c53ac1f74f40 | ["enter courtyard"] | [] | 0 | public_plan_complete_or_blocked |
| J3 | c_c53ac1f74f40 | ["enter courtyard"] | [] | 0 | public_plan_complete_or_blocked |

## 所有候选的真实分支（包括未选择候选）

<details><summary>c_7b57c2d1e762 / inspect / hellcoal</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "inspect hellcoal",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "6c85001af2e676006bccd593c41f7cad24bf417cb10d1568010211dba804be2d",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "6c85001af2e676006bccd593c41f7cad24bf417cb10d1568010211dba804be2d",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_f95fd9e12df4 / craft / hellcoal_concentrate</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "store 3 hellcoal inventory",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 96.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "13dd93c0c51937913d6c3c5a78589d1691d9ca0e87120039aafafa4aa1347bec",
      "goal": false
    },
    {
      "index": 1,
      "action": "enter barracks",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 96.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 92.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered barracks.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "c06cc22be4f168f583016865030fc3ffec1f5913379bdd69c90a03e540fb470b",
      "goal": false
    },
    {
      "index": 2,
      "action": "store 1 devil_oil inventory",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 92.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 devil_oil in my inventory.\nI have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 86.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I stored 1 devil_oil in my inventory.\nI have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "674b332af18de581a79d242001abe36b5f56f4727dd80729aa8d0f0cf2d205a4",
      "goal": false
    },
    {
      "index": 3,
      "action": "craft 2 hellcoal_concentrate",
      "before": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 devil_oil in my inventory.\nI have acquired a new item: devil_oil. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil), oil_flask (2 devil_oil, 1 rubble_chunk), cog_assembly (3 cog, 1 devil_oil), honed_blade (1 forged_blade_blank, 1 devil_oil), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 86.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 22,
        "text": "\nCurrent Time: 0001-01-01 11:40:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft hellcoal_concentrate. Missing necessary crucible in the current area.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 80.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "Cannot craft hellcoal_concentrate. Missing necessary crucible in the current area.\n\nThe malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)",
      "rejected": true,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "baa19ba2460fa6c83e7b97fc07a0d11945ade773af46c793553a4fbcafccb65e",
      "goal": false
    }
  ],
  "stop": "action_limit",
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "baa19ba2460fa6c83e7b97fc07a0d11945ade773af46c793553a4fbcafccb65e",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_c53ac1f74f40 / primitive / courtyard</summary>

```json
{
  "candidate": {
    "kind": "primitive",
    "target": "courtyard",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "enter courtyard",
    "id": "c_c53ac1f74f40"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter courtyard",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "616580509716cfdb97032b67b2393fc7f2406dcba650524c1ea7a070a282224b",
      "goal": false
    }
  ],
  "stop": "public_plan_complete_or_blocked",
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "616580509716cfdb97032b67b2393fc7f2406dcba650524c1ea7a070a282224b",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_973aea1af0e4 / craft / scout_satchel</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "enter barracks",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered barracks.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "1d9e60e412e85fb030fc0e71343a26be1a672ea6611f64a0e3a2f3a0b421e561",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 salvage_cloth inventory",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "afadad1083bc499bf286d4a975e504a293866c4aa14ba019aff0ce5fe6e30484",
      "goal": false
    },
    {
      "index": 2,
      "action": "enter cellar",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I entered cellar.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "2e8a68bcf663dab19f20e8c8018bb7f91b1a5a5627bd259ebf261ffdb4cd61df",
      "goal": false
    },
    {
      "index": 3,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 22,
        "text": "\nCurrent Time: 0001-01-01 11:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "f8a37fe0faa7b8e3465c74dda30b2ab6ad318fb390817196836a261b2eed6023",
      "goal": false
    }
  ],
  "stop": "action_limit",
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "f8a37fe0faa7b8e3465c74dda30b2ab6ad318fb390817196836a261b2eed6023",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_334ffca58064 / craft / war_parchment</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "enter barracks",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered barracks.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "1d9e60e412e85fb030fc0e71343a26be1a672ea6611f64a0e3a2f3a0b421e561",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 salvage_cloth inventory",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "afadad1083bc499bf286d4a975e504a293866c4aa14ba019aff0ce5fe6e30484",
      "goal": false
    },
    {
      "index": 2,
      "action": "craft 2 war_parchment",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.",
      "rejected": true,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "df9f682729b37b5c55472135733f7657bfa3c8212934e358070d273ffd529563",
      "goal": false
    }
  ],
  "stop": "public_plan_complete_or_blocked",
  "actions": 3,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "df9f682729b37b5c55472135733f7657bfa3c8212934e358070d273ffd529563",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_64d1c15df952 / inspect / hellcoal</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "hellcoal",
    "category": "unconnected_visible",
    "evidence": "currently observed, not previously inspected",
    "id": "c_64d1c15df952",
    "confirmed_connection": false,
    "next_action": "inspect hellcoal",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect hellcoal",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "6c85001af2e676006bccd593c41f7cad24bf417cb10d1568010211dba804be2d",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "6c85001af2e676006bccd593c41f7cad24bf417cb10d1568010211dba804be2d",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_9a5fdfafa653 / visit / crucible</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "enter courtyard",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "616580509716cfdb97032b67b2393fc7f2406dcba650524c1ea7a070a282224b",
      "goal": false
    },
    {
      "index": 1,
      "action": "inspect crucible",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "3dea6da55fae14db60857163b3d28240cee4606e3c7fdad74e5e9f0b56a17926",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "3dea6da55fae14db60857163b3d28240cee4606e3c7fdad74e5e9f0b56a17926",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_3005d7648aa4 / craft / war_strap</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "0f23ddc167920ce0ddb609a02f5bbddd02fd578112ed89923d572a7a7cd7e4df",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "8e35dfdf1e7fb55114ed4ebb419dd032ca38b0ce85737e4a85942de99fc83a42",
      "goal": false
    },
    {
      "index": 2,
      "action": "craft 2 war_strap",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft war_strap. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "Cannot craft war_strap. Missing necessary war_bench in the current area.",
      "rejected": true,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "05d06499e5b464cb0bfeebb988f2311126a91214a350219b1e3526a146a1917a",
      "goal": false
    },
    {
      "index": 3,
      "action": "enter courtyard",
      "before": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft war_strap. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 22,
        "text": "\nCurrent Time: 0001-01-01 11:40:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "5367599e044968089d6fc26387de1aab56595d50eaa6451b66fca4c37493ddda",
      "goal": false
    }
  ],
  "stop": "action_limit",
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "5367599e044968089d6fc26387de1aab56595d50eaa6451b66fca4c37493ddda",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_fe960f3c0293 / craft / brimite_ingot</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "enter courtyard",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "616580509716cfdb97032b67b2393fc7f2406dcba650524c1ea7a070a282224b",
      "goal": false
    },
    {
      "index": 1,
      "action": "craft 2 brimite_ingot",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nOnly enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "Only enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {
        "brimite_nugget": 2
      },
      "action_production": {
        "brimite_ingot": 1
      },
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "6da87cd382c0de7c4c06cec4be5509bc3ceb40d10a3a4a092d3efb6f5e43387d",
      "goal": false
    },
    {
      "index": 2,
      "action": "inspect brimite_ingot",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nOnly enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.\nIt can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.\nIt can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [
        "brimite_blade_blank",
        "fiend_alloy"
      ],
      "new_key_recipes": [
        "fiend_alloy"
      ],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "d993342ad461133f580afaba0d358a64fa707455319bf90e398afb04e225932f",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
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
  "final_hash": "d993342ad461133f580afaba0d358a64fa707455319bf90e398afb04e225932f",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_d6a4a748f3ca / craft / stitched_panel</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "1b4d1fda8e54db5fab078df4524061693b14fd9ad019ef3d84639e2225a0cf4e",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "537b4d00fc44383ed0da09a31f88776ea3c6c7117257f65f69786e1be7bcd418",
      "goal": false
    },
    {
      "index": 2,
      "action": "craft 2 stitched_panel",
      "before": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft stitched_panel. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
      "rejected": true,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "d457fde99b4f5cc4c7ae0e1c296ab557fbfe04a03f900a0588532be38b46d98b",
      "goal": false
    },
    {
      "index": 3,
      "action": "enter courtyard",
      "before": {
        "step": 21,
        "text": "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft stitched_panel. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 22,
        "text": "\nCurrent Time: 0001-01-01 11:40:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "75b0c9dc4a792a4e957dc05685abebac41cef18d2aaf9e9fa6a81ab4ba80d854",
      "goal": false
    }
  ],
  "stop": "action_limit",
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "75b0c9dc4a792a4e957dc05685abebac41cef18d2aaf9e9fa6a81ab4ba80d854",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_c9ee531b4a5f / inspect / fiend_helm</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "fiend_helm",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_c9ee531b4a5f",
    "confirmed_connection": true,
    "next_action": "inspect fiend_helm",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect fiend_helm",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "20cbd9b381412842f47807eb0094e73aeb7abf5dc759e26e9c3222013f0dbd87",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "20cbd9b381412842f47807eb0094e73aeb7abf5dc759e26e9c3222013f0dbd87",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_3f33cf002d85 / visit / war_bench</summary>

```json
{
  "candidate": {
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
  "trace": [
    {
      "index": 0,
      "action": "enter courtyard",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I entered courtyard.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "616580509716cfdb97032b67b2393fc7f2406dcba650524c1ea7a070a282224b",
      "goal": false
    },
    {
      "index": 1,
      "action": "inspect war_bench",
      "before": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 20,
        "text": "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "fc9232502d4e1bef872517633c05b618c9db67eda7a5c749f9c09649cd8345be",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "fc9232502d4e1bef872517633c05b618c9db67eda7a5c749f9c09649cd8345be",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_ff3dc4ae7a9a / inspect / sinew_cord</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "sinew_cord",
    "category": "unconnected_visible",
    "evidence": "currently observed, not previously inspected",
    "id": "c_ff3dc4ae7a9a",
    "confirmed_connection": false,
    "next_action": "inspect sinew_cord",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect sinew_cord",
      "before": {
        "step": 18,
        "text": "\nCurrent Time: 0001-01-01 11:00:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 19,
        "text": "\nCurrent Time: 0001-01-01 11:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [
        "chain_net",
        "cog_crossbow",
        "field_journal",
        "fiend_gauntlets",
        "fiend_scale_bundle",
        "hunter_gauntlets",
        "padded_tunic",
        "repair_kit",
        "ruin_spear",
        "scale_bundle",
        "scrap_buckler",
        "siege_crate",
        "spiked_club",
        "timber_sword",
        "war_codex",
        "warding_charm"
      ],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "453a42970be8ed04d36d6819d9b23d59231b12c25d22952e5899c66b672ef9bb",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "453a42970be8ed04d36d6819d9b23d59231b12c25d22952e5899c66b672ef9bb",
  "goal": false,
  "replayed_twice": true
}
```

</details>
