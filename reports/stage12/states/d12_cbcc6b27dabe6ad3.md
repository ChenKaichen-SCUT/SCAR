# d12_cbcc6b27dabe6ad3：craft 1 fiend_helm

来源：Stage11 / sequence-303b2d8fdefd2859-E0-d560807b7e4b / index 15。

## 当时的公开观察、知识和 STM5

```json
{
  "observation": {
    "step": 25,
    "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
  },
  "public_knowledge": {
    "objective": "Obtain at least 2 fiend_helm in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
    "target_action": "craft 1 fiend_helm",
    "current": {
      "location": "courtyard",
      "hands": {
        "fiend_helm": 1.0
      },
      "ground": {
        "crucible": 1.0,
        "war_bench": 1.0,
        "brimite_ingot": 1.0
      },
      "equipment": {
        "scout_satchel_0": 1.0
      },
      "neighbors": [
        "cellar"
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
      "hunter_gauntlets": {
        "ingredients": [
          "iron_bar",
          "war_strap",
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
      }
    },
    "containers": {
      "scout_satchel_0": {
        "counts": {},
        "load": 0.0,
        "capacity": 20.0,
        "location": "courtyard",
        "step": 25,
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
        "step": 20,
        "source": "public_ground_observation"
      },
      "courtyard": {
        "objects": {
          "crucible": 1.0,
          "war_bench": 1.0,
          "brimite_ingot": 1.0
        },
        "step": 25,
        "source": "public_ground_observation"
      }
    },
    "inspected": [
      "scout_satchel_0",
      "fiend_helm",
      "brimite_nugget",
      "devil_oil",
      "salvage_cloth",
      "bandage_roll",
      "hellcoal",
      "sinew_cord",
      "crucible",
      "war_bench",
      "inventory"
    ],
    "produced": {
      "brimite_ingot": 1
    },
    "recent_attempts": [
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
      },
      {
        "action": "inspect hellcoal",
        "target": "hellcoal",
        "context": {
          "location": "cellar",
          "stations": {},
          "materials": {},
          "visible": true
        },
        "feedback": "I inspected hellcoal: A smoldering lump of infernal fuel that never fully cools, salvaged from machine furnaces.\nIt can be used to craft: hellcoal_concentrate (made of hellcoal, devil_oil).\nIt has nothing written on it.",
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
        "action": "inspect sinew_cord",
        "target": "sinew_cord",
        "context": {
          "location": "cellar",
          "stations": {},
          "materials": {
            "salvage_cloth": 0
          },
          "visible": true
        },
        "feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
        "state": "SUCCESS",
        "meaningful_trial": true,
        "failure_type": null,
        "retry_condition": null,
        "actual_action_cost": 1,
        "observed_resource_consumption": null,
        "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
        "was_forward_trial": false,
        "step": 20,
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
        "step": 22,
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
        "step": 23,
        "retry_after_block": false
      },
      {
        "action": "craft 2 brimite_ingot",
        "target": "brimite_ingot",
        "context": {
          "location": "courtyard",
          "stations": {
            "crucible": true
          },
          "materials": {
            "brimite_nugget": 2.0
          },
          "visible": false
        },
        "feedback": "Only enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.",
        "state": "SUCCESS",
        "meaningful_trial": true,
        "failure_type": null,
        "retry_condition": null,
        "actual_action_cost": 1,
        "observed_resource_consumption": null,
        "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
        "was_forward_trial": true,
        "step": 24,
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
        "feedback": "I inspected my inventory.\nIt contains: no objects (capacity: 0/20).",
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
      }
    ],
    "unresolved_public_nodes": [
      "fiend_helm"
    ],
    "uncertainty": "Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe."
  },
  "memory": [
    "\nCurrent Time: 0001-01-01 11:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n\nProposed: enter courtyard\nExecuted action: enter courtyard",
    "\nCurrent Time: 0001-01-01 11:30:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: talk to olivia_grant\nExecuted action: inspect crucible",
    "\nCurrent Time: 0001-01-01 11:40:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: craft 1 fiend_helm\nExecuted action: inspect war_bench",
    "\nCurrent Time: 0001-01-01 11:50:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: craft 1 fiend_helm\nExecuted action: craft 2 brimite_ingot",
    "\nCurrent Time: 0001-01-01 12:00:00\nCurrent Location: Ashen Bastion, courtyard\n\nOnly enough ingredients to craft 1 brimite_ingot.\nI successfully crafted 1 brimite_ingot. It is now on the ground.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n\nProposed: craft 1 fiend_helm\nExecuted action: inspect inventory"
  ]
}
```

## 原模型提案与两个规则参考

```json
{
  "historical_model_proposal": "talk to olivia_grant",
  "rule_actions": {
    "J0": "inspect brimite_ingot",
    "J1": "inspect brimite_ingot"
  },
  "rule_decisions": {
    "J0": {
      "node": "fiend_helm",
      "action": "inspect brimite_ingot",
      "structured_action": "inspect brimite_ingot",
      "graph": {},
      "queue": [
        "fiend_helm"
      ],
      "resource_table": {
        "state": {
          "location": "courtyard",
          "location_full": "Ashen Bastion, courtyard",
          "hands": {
            "fiend_helm": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "crucible": 1.0,
            "war_bench": 1.0,
            "brimite_ingot": 1.0
          },
          "neighbors": [
            "cellar"
          ],
          "step": 25,
          "feedback": "I inspected my inventory.\nIt contains: no objects (capacity: 0/20).",
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
            "step": 20,
            "source": "public_ground_observation"
          },
          "courtyard": {
            "objects": {
              "crucible": 1.0,
              "war_bench": 1.0,
              "brimite_ingot": 1.0
            },
            "step": 25,
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
            "counts": {},
            "load": 0.0,
            "capacity": 20.0,
            "location": "courtyard",
            "step": 25,
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
            "quantities": {
              "brimite_nugget": 2.0
            },
            "ingredients": [
              "brimite_nugget"
            ],
            "step": 12,
            "source": "public_inspection",
            "stations": [
              "crucible"
            ],
            "quantity_source": {
              "kind": "observed_successful_consumption",
              "step": 24
            }
          },
          "hellcoal_concentrate": {
            "quantities": null,
            "ingredients": [
              "hellcoal",
              "devil_oil"
            ],
            "step": 19,
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
            "step": 20,
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
            "step": 20,
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
            "step": 20,
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
            "step": 20,
            "source": "public_inspection"
          },
          "timber_sword": {
            "quantities": null,
            "ingredients": [
              "scorched_plank",
              "wood_strip",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "spiked_club": {
            "quantities": null,
            "ingredients": [
              "charred_timber",
              "rubble_chunk",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "war_codex": {
            "quantities": null,
            "ingredients": [
              "field_journal",
              "sinew_cord",
              "fiend_strip"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "cog_crossbow": {
            "quantities": null,
            "ingredients": [
              "gearwork_frame",
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "ruin_spear": {
            "quantities": null,
            "ingredients": [
              "knapped_edge",
              "wooden_rod",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "hunter_gauntlets": {
            "quantities": null,
            "ingredients": [
              "iron_bar",
              "war_strap",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "fiend_scale_bundle": {
            "quantities": null,
            "ingredients": [
              "fiend_alloy_scale",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "scale_bundle": {
            "quantities": null,
            "ingredients": [
              "iron_scale",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "siege_crate": {
            "quantities": null,
            "ingredients": [
              "scorched_plank",
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "fiend_gauntlets": {
            "quantities": null,
            "ingredients": [
              "fiend_alloy",
              "war_strap",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "padded_tunic": {
            "quantities": null,
            "ingredients": [
              "padded_lining",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "scrap_buckler": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "repair_kit": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "sinew_cord",
              "oil_flask"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "warding_charm": {
            "quantities": null,
            "ingredients": [
              "demon_core_shard",
              "sinew_cord",
              "hellcoal_concentrate"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "field_journal": {
            "quantities": null,
            "ingredients": [
              "war_parchment",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "chain_net": {
            "quantities": null,
            "ingredients": [
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          }
        },
        "inspected": [
          "scout_satchel_0",
          "fiend_helm",
          "brimite_nugget",
          "devil_oil",
          "salvage_cloth",
          "bandage_roll",
          "hellcoal",
          "sinew_cord",
          "crucible",
          "war_bench",
          "inventory"
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
            "source": "I entered courtyard.",
            "step": 21
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
        "observations": 88,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 fiend_helm",
      "reason": "retain_F0",
      "mechanisms": {
        "exploration": {
          "reason": "unknown recipe/material link",
          "source": {
            "public_entity": "brimite_ingot",
            "missing_nodes": [
              "fiend_helm"
            ]
          },
          "spent": 15,
          "limit": 18
        }
      },
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "inspect brimite_ingot",
        "base_action": "talk to olivia_grant",
        "selected_action": "inspect brimite_ingot",
        "reason": "retain_F0",
        "override": true,
        "overlay_changed_F0": false,
        "conditions": [
          {
            "action": "inspect brimite_ingot",
            "status": "UNKNOWN",
            "conditions": [
              {
                "kind": "public_trial",
                "status": "UNKNOWN",
                "evidence": "no known negative condition",
                "observed_step": 25,
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
      "action": "inspect brimite_ingot",
      "structured_action": "inspect brimite_ingot",
      "graph": {},
      "queue": [
        "fiend_helm"
      ],
      "resource_table": {
        "state": {
          "location": "courtyard",
          "location_full": "Ashen Bastion, courtyard",
          "hands": {
            "fiend_helm": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "crucible": 1.0,
            "war_bench": 1.0,
            "brimite_ingot": 1.0
          },
          "neighbors": [
            "cellar"
          ],
          "step": 25,
          "feedback": "I inspected my inventory.\nIt contains: no objects (capacity: 0/20).",
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
            "step": 20,
            "source": "public_ground_observation"
          },
          "courtyard": {
            "objects": {
              "crucible": 1.0,
              "war_bench": 1.0,
              "brimite_ingot": 1.0
            },
            "step": 25,
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
            "counts": {},
            "load": 0.0,
            "capacity": 20.0,
            "location": "courtyard",
            "step": 25,
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
            "quantities": {
              "brimite_nugget": 2.0
            },
            "ingredients": [
              "brimite_nugget"
            ],
            "step": 12,
            "source": "public_inspection",
            "stations": [
              "crucible"
            ],
            "quantity_source": {
              "kind": "observed_successful_consumption",
              "step": 24
            }
          },
          "hellcoal_concentrate": {
            "quantities": null,
            "ingredients": [
              "hellcoal",
              "devil_oil"
            ],
            "step": 19,
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
            "step": 20,
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
            "step": 20,
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
            "step": 20,
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
            "step": 20,
            "source": "public_inspection"
          },
          "timber_sword": {
            "quantities": null,
            "ingredients": [
              "scorched_plank",
              "wood_strip",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "spiked_club": {
            "quantities": null,
            "ingredients": [
              "charred_timber",
              "rubble_chunk",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "war_codex": {
            "quantities": null,
            "ingredients": [
              "field_journal",
              "sinew_cord",
              "fiend_strip"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "cog_crossbow": {
            "quantities": null,
            "ingredients": [
              "gearwork_frame",
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "ruin_spear": {
            "quantities": null,
            "ingredients": [
              "knapped_edge",
              "wooden_rod",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "hunter_gauntlets": {
            "quantities": null,
            "ingredients": [
              "iron_bar",
              "war_strap",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "fiend_scale_bundle": {
            "quantities": null,
            "ingredients": [
              "fiend_alloy_scale",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "scale_bundle": {
            "quantities": null,
            "ingredients": [
              "iron_scale",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "siege_crate": {
            "quantities": null,
            "ingredients": [
              "scorched_plank",
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "fiend_gauntlets": {
            "quantities": null,
            "ingredients": [
              "fiend_alloy",
              "war_strap",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "padded_tunic": {
            "quantities": null,
            "ingredients": [
              "padded_lining",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "scrap_buckler": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "repair_kit": {
            "quantities": null,
            "ingredients": [
              "scrap_iron",
              "sinew_cord",
              "oil_flask"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "warding_charm": {
            "quantities": null,
            "ingredients": [
              "demon_core_shard",
              "sinew_cord",
              "hellcoal_concentrate"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "field_journal": {
            "quantities": null,
            "ingredients": [
              "war_parchment",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          },
          "chain_net": {
            "quantities": null,
            "ingredients": [
              "iron_bar",
              "sinew_cord"
            ],
            "step": 20,
            "source": "public_inspection"
          }
        },
        "inspected": [
          "scout_satchel_0",
          "fiend_helm",
          "brimite_nugget",
          "devil_oil",
          "salvage_cloth",
          "bandage_roll",
          "hellcoal",
          "sinew_cord",
          "crucible",
          "war_bench",
          "inventory"
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
            "source": "I entered courtyard.",
            "step": 21
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
        "observations": 89,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 fiend_helm",
      "reason": "stage11_inspect_public_object",
      "mechanisms": {
        "exploration": {
          "reason": "stage11_inspect_public_object",
          "source": {
            "confirmed_goal_connection": false,
            "unresolved_node": false,
            "actually_produced": true,
            "observed_material_source": false,
            "unknown_downstream_connection": true
          },
          "spent": 15,
          "limit": 18
        }
      },
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "inspect brimite_ingot",
        "base_action": "talk to olivia_grant",
        "selected_action": "inspect brimite_ingot",
        "reason": "retain_F0",
        "override": true,
        "overlay_changed_F0": false,
        "conditions": [
          {
            "action": "inspect brimite_ingot",
            "status": "UNKNOWN",
            "conditions": [
              {
                "kind": "public_trial",
                "status": "UNKNOWN",
                "evidence": "no known negative condition",
                "observed_step": 25,
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
        "base_action": "talk to olivia_grant",
        "S1_with_rank_candidate": "inspect brimite_ingot",
        "selected_action": "inspect brimite_ingot",
        "exploration_candidates": [
          {
            "action": "inspect brimite_ingot",
            "priority": 2,
            "kind": "inspect_public_object",
            "target": "brimite_ingot",
            "basis": {
              "confirmed_goal_connection": false,
              "unresolved_node": false,
              "actually_produced": true,
              "observed_material_source": false,
              "unknown_downstream_connection": true
            },
            "assessment": {
              "action": "inspect brimite_ingot",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "public_trial",
                  "status": "UNKNOWN",
                  "evidence": "no known negative condition",
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 0
          },
          {
            "action": "enter cellar",
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
                "step": 19,
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
              "action": "enter cellar",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "route",
                  "status": "UNKNOWN",
                  "evidence": {
                    "neighbors": [
                      "cellar"
                    ],
                    "guard": "UNLOCKED"
                  },
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter cellar",
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
                "step": 20,
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
              "action": "enter cellar",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "route",
                  "status": "UNKNOWN",
                  "evidence": {
                    "neighbors": [
                      "cellar"
                    ],
                    "guard": "UNLOCKED"
                  },
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter cellar",
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
                "step": 20,
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
              "action": "enter cellar",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "route",
                  "status": "UNKNOWN",
                  "evidence": {
                    "neighbors": [
                      "cellar"
                    ],
                    "guard": "UNLOCKED"
                  },
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter cellar",
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
              "action": "enter cellar",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "route",
                  "status": "UNKNOWN",
                  "evidence": {
                    "neighbors": [
                      "cellar"
                    ],
                    "guard": "UNLOCKED"
                  },
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          },
          {
            "action": "enter cellar",
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
                "step": 20,
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
              "action": "enter cellar",
              "status": "UNKNOWN",
              "conditions": [
                {
                  "kind": "route",
                  "status": "UNKNOWN",
                  "evidence": {
                    "neighbors": [
                      "cellar"
                    ],
                    "guard": "UNLOCKED"
                  },
                  "observed_step": 25,
                  "valid_until": "relevant public condition changes"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
          }
        ],
        "execution_candidates": [],
        "selected": {
          "action": "inspect brimite_ingot",
          "priority": 2,
          "kind": "inspect_public_object",
          "target": "brimite_ingot",
          "basis": {
            "confirmed_goal_connection": false,
            "unresolved_node": false,
            "actually_produced": true,
            "observed_material_source": false,
            "unknown_downstream_connection": true
          },
          "assessment": {
            "action": "inspect brimite_ingot",
            "status": "UNKNOWN",
            "conditions": [
              {
                "kind": "public_trial",
                "status": "UNKNOWN",
                "evidence": "no known negative condition",
                "observed_step": 25,
                "valid_until": "relevant public condition changes"
              }
            ]
          },
          "eligible": true,
          "preparation_steps": 0
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
              "status": "UNKNOWN",
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
                "status": "UNKNOWN",
                "conditions": [
                  {
                    "kind": "station",
                    "status": "SUPPORTED",
                    "evidence": {
                      "required": [
                        "war_bench",
                        "crucible"
                      ],
                      "current_ground": {
                        "crucible": 1.0,
                        "war_bench": 1.0,
                        "brimite_ingot": 1.0
                      }
                    },
                    "observed_step": 25,
                    "valid_until": "relevant public condition changes"
                  },
                  {
                    "kind": "recipe",
                    "status": "UNKNOWN",
                    "evidence": "ingredient names not publicly disclosed",
                    "observed_step": 25,
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
      "next_action": "enter cellar",
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
      "next_action": "enter cellar",
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
      "next_action": "enter cellar",
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
      "next_action": "enter cellar",
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
      "next_action": "enter cellar",
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
      "kind": "inspect",
      "target": "brimite_ingot",
      "category": "primitive",
      "evidence": "public method proposal; exact first action retained",
      "first_action": "inspect brimite_ingot",
      "id": "c_c4b21bc50fb6",
      "confirmed_connection": false,
      "next_action": "inspect brimite_ingot",
      "public_condition": "UNKNOWN"
    },
    {
      "kind": "inspect",
      "target": "brimite_ingot",
      "category": "fresh_product",
      "evidence": "currently observed, not previously inspected",
      "id": "c_d6fbc47d772b",
      "confirmed_connection": false,
      "next_action": "inspect brimite_ingot",
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
      "confirmed_connection": false,
      "next_action": "enter cellar",
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
      "confirmed_connection": false,
      "next_action": "enter cellar",
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
    "state_id": "d12_cbcc6b27dabe6ad3",
    "method": "J2",
    "replicate": 0,
    "status": "completed",
    "parsed": {
      "reasoning": "I have a brimite_ingot on the ground and stations (crucible, war_bench) here. The fiend_helm recipe is unknown, but brimite_ingot was a prior craft attempt toward it. I should inspect the brimite_ingot to learn any recipe relations, as inspecting intermediate products has revealed recipe info before.",
      "action": "inspect brimite_ingot"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.00155412,
    "charged_or_reserved_usd": 0.00155412
  },
  {
    "state_id": "d12_cbcc6b27dabe6ad3",
    "method": "J3",
    "replicate": 0,
    "status": "completed",
    "parsed": {
      "selected_candidate_id": "c_d6fbc47d772b",
      "ranked_candidate_ids": [
        "c_d6fbc47d772b",
        "c_c9ee531b4a5f",
        "c_c4b21bc50fb6"
      ],
      "reason": "Freshly crafted brimite_ingot may reveal fiend_helm recipe details when inspected; inspecting fiend_helm itself could also expose its ingredient list.",
      "hypothesized_connection": "brimite_ingot is likely an intermediate material for fiend_helm crafting, so its inspection may reveal the recipe.",
      "confidence": 0.35,
      "expected_information": "Possible fiend_helm recipe ingredients or station requirements, or confirmation brimite_ingot is unrelated.",
      "alternative_if_failed": "c_c9ee531b4a5f"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.000546336,
    "charged_or_reserved_usd": 0.000546336
  }
]
```

## 四方法的主选择与真实结果

| 方法 | 候选/提案 | 实际短分支 | 新增必要配方 | 原生拒绝数 | 停止原因 |
| --- | --- | --- | --- | --- | --- |
| J0 | c_c4b21bc50fb6 | ["inspect brimite_ingot"] | ["fiend_alloy"] | 0 | inspection_attempt_completed |
| J1 | c_c4b21bc50fb6 | ["inspect brimite_ingot"] | ["fiend_alloy"] | 0 | inspection_attempt_completed |
| J2 | c_c4b21bc50fb6 | ["inspect brimite_ingot"] | ["fiend_alloy"] | 0 | inspection_attempt_completed |
| J3 | c_d6fbc47d772b | ["inspect brimite_ingot"] | ["fiend_alloy"] | 0 | inspection_attempt_completed |

## 所有候选的真实分支（包括未选择候选）

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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 3 hellcoal inventory",
      "before": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {
        "salvage_cloth": 1
      },
      "state_hash": "3fb1a27a440ae5d415daf2251fb00ffcf401e0cd197db0cff2bc03222ce65ff9",
      "goal": false
    },
    {
      "index": 2,
      "action": "enter barracks",
      "before": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 3 hellcoal in my inventory.\nI have acquired a new item: hellcoal. It can be used to craft: hellcoal_concentrate (3 hellcoal, 1 devil_oil)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see scrap_automaton_17 nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "1a433634ee4c873981eb22b2e04fcafb6e666ddbaa11a4a1aef42cfa3667b052",
      "goal": false
    }
  ],
  "stop": "public_plan_complete_or_blocked",
  "actions": 3,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": true,
  "final_hash": "1a433634ee4c873981eb22b2e04fcafb6e666ddbaa11a4a1aef42cfa3667b052",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
      "goal": false
    },
    {
      "index": 1,
      "action": "enter barracks",
      "before": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "9660871a3baa88f89d9bf780393c5683dbd3c201d5036bc3cd1a4aca2f107d04",
      "goal": false
    },
    {
      "index": 2,
      "action": "store 1 salvage_cloth inventory",
      "before": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "aa222d5967662c1f54099bf9cb9ef7f885046569c9412766dec6d16598ce1fbf",
      "goal": false
    },
    {
      "index": 3,
      "action": "enter cellar",
      "before": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 29,
        "text": "\nCurrent Time: 0001-01-01 12:50:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "8c5224d024d0f94c5db88f4068005d6c2c2edd3f7bc2d3ca8adbab3b2551c6c4",
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
  "final_hash": "8c5224d024d0f94c5db88f4068005d6c2c2edd3f7bc2d3ca8adbab3b2551c6c4",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
      "goal": false
    },
    {
      "index": 1,
      "action": "enter barracks",
      "before": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "9660871a3baa88f89d9bf780393c5683dbd3c201d5036bc3cd1a4aca2f107d04",
      "goal": false
    },
    {
      "index": 2,
      "action": "store 1 salvage_cloth inventory",
      "before": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 1 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "aa222d5967662c1f54099bf9cb9ef7f885046569c9412766dec6d16598ce1fbf",
      "goal": false
    },
    {
      "index": 3,
      "action": "craft 2 war_parchment",
      "before": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 salvage_cloth in my inventory.\nolivia_grant enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 3 coins!\nTalk to olivia_grant to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 29,
        "text": "\nCurrent Time: 0001-01-01 12:50:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 devil_oil, 3 crown_shard near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 20.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "ad51079ed336888c6a23b58e6dda233dc453c4d9366f9b29d0b5a86f78a92a7d",
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
  "final_hash": "ad51079ed336888c6a23b58e6dda233dc453c4d9366f9b29d0b5a86f78a92a7d",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {
        "salvage_cloth": 1
      },
      "state_hash": "edde3bc50c0549bd1a6368b91ff13d98ee127c9845e71455be09dfcb31549949",
      "goal": false
    },
    {
      "index": 2,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "f846a0a5f86973213bec271c7c65bc53a565e42c4a977381d0ae731087efb822",
      "goal": false
    },
    {
      "index": 3,
      "action": "craft 2 war_strap",
      "before": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 29,
        "text": "\nCurrent Time: 0001-01-01 12:50:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft war_strap. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "c58a3b0eeaa842e147f1e4d8836ee99b669ddb7bbe3cc82fb3b3fe1be4cdf9c2",
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
  "environment_key_loss": true,
  "final_hash": "c58a3b0eeaa842e147f1e4d8836ee99b669ddb7bbe3cc82fb3b3fe1be4cdf9c2",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {
        "salvage_cloth": 1
      },
      "state_hash": "9ee3dd935bcf55ff3fdde2d433e80eedf5ab262cacdb6f12d7fcbc30663fff12",
      "goal": false
    },
    {
      "index": 2,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 27,
        "text": "\nCurrent Time: 0001-01-01 12:30:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\nOminous mechanical grinding echoes from the nearby barracks. Dormant war machines are reclaiming the abandoned territory — a scrap_automaton_17 has emerged from the wreckage.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "6866d02b9701c5fa436e24615c4a8a43340f741031c59985cc89546977ac6327",
      "goal": false
    },
    {
      "index": 3,
      "action": "craft 2 stitched_panel",
      "before": {
        "step": 28,
        "text": "\nCurrent Time: 0001-01-01 12:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 29,
        "text": "\nCurrent Time: 0001-01-01 12:50:00\nCurrent Location: Ashen Bastion, cellar\n\nCannot craft stitched_panel. Missing necessary war_bench in the current area.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 3 hellcoal near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "ac1e12d2c0169b398e9029619936362ee4dd6ff069065cf8bb092e75f54640ae",
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
  "environment_key_loss": true,
  "final_hash": "ac1e12d2c0169b398e9029619936362ee4dd6ff069065cf8bb092e75f54640ae",
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
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected fiend_helm: A helm forged from fiend alloy, its visor shaped like a snarling devil's face.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "bdbd0171aa95c78d35434ee23da968d5d2247e796ba91157d4b3b3301dac9403",
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
  "final_hash": "bdbd0171aa95c78d35434ee23da968d5d2247e796ba91157d4b3b3301dac9403",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_c4b21bc50fb6 / inspect / brimite_ingot</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "brimite_ingot",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "inspect brimite_ingot",
    "id": "c_c4b21bc50fb6"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect brimite_ingot",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.\nIt can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "7a15391a15452a5e47ed6f583e0f052b4ca13a580eee4bcffb9b12c042479b9b",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [
    "fiend_alloy"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "7a15391a15452a5e47ed6f583e0f052b4ca13a580eee4bcffb9b12c042479b9b",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_d6fbc47d772b / inspect / brimite_ingot</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "brimite_ingot",
    "category": "fresh_product",
    "evidence": "currently observed, not previously inspected",
    "id": "c_d6fbc47d772b",
    "confirmed_connection": false,
    "next_action": "inspect brimite_ingot",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect brimite_ingot",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected brimite_ingot: A refined brimite ingot that pulses with trapped hellfire, forged for the strongest gear.\nIt can be used to craft: fiend_alloy (made of brimite_ingot, hellcoal_concentrate), brimite_blade_blank (made of brimite_ingot, wooden_rod).\nIt has nothing written on it.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "7a15391a15452a5e47ed6f583e0f052b4ca13a580eee4bcffb9b12c042479b9b",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [
    "fiend_alloy"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "7a15391a15452a5e47ed6f583e0f052b4ca13a580eee4bcffb9b12c042479b9b",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_51d20e64a67f / craft / sinew_cord</summary>

```json
{
  "candidate": {
    "kind": "craft",
    "target": "sinew_cord",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_51d20e64a67f",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
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
  "final_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_a31e0c0dfecd / craft / bandage_roll</summary>

```json
{
  "candidate": {
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
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 25,
        "text": "\nCurrent Time: 0001-01-01 12:10:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected my inventory.\nIt contains: no objects (capacity: 0/20).\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 crucible, 1 war_bench, 1 brimite_ingot near me.\nI see olivia_grant nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 26,
        "text": "\nCurrent Time: 0001-01-01 12:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 fiend_helm.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 3 hellcoal, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 15.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
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
  "final_hash": "0334a676765569964ff1da25c056a99df37668c774dfe4a253af65795bd329e4",
  "goal": false,
  "replayed_twice": true
}
```

</details>
