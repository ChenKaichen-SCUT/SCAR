# d12_db9cf8a8d4ddadac：craft 1 padded_tunic

来源：Stage10 / sequence-f5bbe8ac06891a7d-S1-c3876e4fe87c / index 2。

## 当时的公开观察、知识和 STM5

```json
{
  "observation": {
    "step": 12,
    "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
  },
  "public_knowledge": {
    "objective": "Obtain at least 2 padded_tunic in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
    "target_action": "craft 1 padded_tunic",
    "current": {
      "location": "barracks",
      "hands": {
        "padded_tunic": 1.0
      },
      "ground": {
        "bandage_roll": 1.0,
        "sinew_cord": 1.0
      },
      "equipment": {
        "scout_satchel_0": 1.0
      },
      "neighbors": [
        "cellar"
      ]
    },
    "confirmed_recipe_relations": {
      "padded_tunic": {
        "ingredients": "UNKNOWN",
        "stations": [
          "war_bench"
        ]
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
        "counts": {},
        "load": 0.0,
        "capacity": 20.0,
        "location": "barracks",
        "step": 2,
        "source": "public_container_inspection"
      }
    },
    "known_locations": {
      "barracks": {
        "objects": {
          "bandage_roll": 1.0,
          "sinew_cord": 1.0
        },
        "step": 12,
        "source": "public_ground_observation"
      },
      "cellar": {
        "objects": {
          "salvage_cloth": 2.0
        },
        "step": 8,
        "source": "public_ground_observation"
      },
      "courtyard": {
        "objects": {
          "war_bench": 1.0
        },
        "step": 7,
        "source": "public_ground_observation"
      }
    },
    "inspected": [
      "scout_satchel_0",
      "padded_tunic",
      "bandage_roll"
    ],
    "produced": {},
    "recent_attempts": [
      {
        "action": "inspect padded_tunic",
        "target": "padded_tunic",
        "context": {
          "location": "barracks",
          "stations": {
            "war_bench": false
          },
          "materials": {},
          "visible": true
        },
        "feedback": "I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.",
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
        "action": "inspect bandage_roll",
        "target": "bandage_roll",
        "context": {
          "location": "barracks",
          "stations": {},
          "materials": {},
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
        "step": 12,
        "retry_after_block": false
      }
    ],
    "unresolved_public_nodes": [
      "padded_tunic"
    ],
    "uncertainty": "Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe."
  },
  "memory": [
    "\nCurrent Time: 0001-01-01 09:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n\nAction: enter barracks\n\nCurrent Time: 0001-01-01 09:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n",
    "\nCurrent Time: 0001-01-01 09:30:00\nCurrent Location: Ashen Bastion, barracks\n\nI entered barracks.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nAction: craft 1 padded_tunic\n\nCurrent Time: 0001-01-01 09:40:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft padded_tunic. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n",
    "Recovery objective: Obtain at least 2 padded_tunic in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
    "\nCurrent Time: 0001-01-01 09:40:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft padded_tunic. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter courtyard\nExecuted action: inspect padded_tunic",
    "\nCurrent Time: 0001-01-01 09:50:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n\nProposed: enter courtyard\nExecuted action: inspect bandage_roll"
  ]
}
```

## 原模型提案与两个规则参考

```json
{
  "historical_model_proposal": "enter courtyard",
  "rule_actions": {
    "J0": "inspect sinew_cord",
    "J1": "store 1 bandage_roll inventory"
  },
  "rule_decisions": {
    "J0": {
      "node": "padded_tunic",
      "action": "inspect sinew_cord",
      "structured_action": "inspect sinew_cord",
      "graph": {},
      "queue": [
        "padded_tunic"
      ],
      "resource_table": {
        "state": {
          "location": "barracks",
          "location_full": "Ashen Bastion, barracks",
          "hands": {
            "padded_tunic": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "bandage_roll": 1.0,
            "sinew_cord": 1.0
          },
          "neighbors": [
            "cellar"
          ],
          "step": 12,
          "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
          "public_goal": null
        },
        "places": {
          "barracks": {
            "objects": {
              "bandage_roll": 1.0,
              "sinew_cord": 1.0
            },
            "step": 12,
            "source": "public_ground_observation"
          },
          "cellar": {
            "objects": {
              "salvage_cloth": 2.0
            },
            "step": 8,
            "source": "public_ground_observation"
          },
          "courtyard": {
            "objects": {
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
            "counts": {},
            "load": 0.0,
            "capacity": 20.0,
            "location": "barracks",
            "step": 2,
            "source": "public_container_inspection"
          }
        },
        "inventory": "scout_satchel_0",
        "recipes": {
          "padded_tunic": {
            "ingredients": [],
            "quantities": null,
            "stations": [
              "war_bench"
            ]
          },
          "stitched_panel": {
            "quantities": null,
            "ingredients": [
              "bandage_roll",
              "sinew_cord"
            ],
            "step": 12,
            "source": "public_inspection"
          },
          "ruin_maul": {
            "quantities": null,
            "ingredients": [
              "ruin_blade",
              "wooden_rod",
              "bandage_roll"
            ],
            "step": 12,
            "source": "public_inspection"
          },
          "war_strap": {
            "quantities": null,
            "ingredients": [
              "sinew_cord",
              "bandage_roll"
            ],
            "step": 12,
            "source": "public_inspection"
          }
        },
        "inspected": [
          "scout_satchel_0",
          "padded_tunic",
          "bandage_roll"
        ],
        "guards": {
          "barracks->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 6
          },
          "cellar->courtyard": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered courtyard.\njames_owen enters the area.\n\n=== SIDE QUESTS UNLOCKED ===\nSide quests are now available! Completing them will grant you coins.\nTalk to james_owen to see your current tasks.\n============================",
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
        "observations": 36,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 padded_tunic",
      "reason": "retain_F0",
      "mechanisms": {
        "exploration": {
          "reason": "unknown recipe/material link",
          "source": {
            "public_entity": "sinew_cord",
            "missing_nodes": [
              "padded_tunic"
            ]
          },
          "spent": 3,
          "limit": 18
        }
      },
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "inspect sinew_cord",
        "base_action": "enter courtyard",
        "selected_action": "inspect sinew_cord",
        "reason": "retain_F0",
        "override": true,
        "overlay_changed_F0": false,
        "conditions": [
          {
            "action": "inspect sinew_cord",
            "status": "UNKNOWN",
            "conditions": [
              {
                "kind": "public_trial",
                "status": "UNKNOWN",
                "evidence": "no known negative condition",
                "observed_step": 12,
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
      "node": "padded_tunic",
      "action": "store 1 bandage_roll inventory",
      "structured_action": "store 1 bandage_roll inventory",
      "graph": {},
      "queue": [
        "padded_tunic"
      ],
      "resource_table": {
        "state": {
          "location": "barracks",
          "location_full": "Ashen Bastion, barracks",
          "hands": {
            "padded_tunic": 1.0
          },
          "equipment": {
            "scout_satchel_0": 1.0
          },
          "ground": {
            "bandage_roll": 1.0,
            "sinew_cord": 1.0
          },
          "neighbors": [
            "cellar"
          ],
          "step": 12,
          "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
          "public_goal": null
        },
        "places": {
          "barracks": {
            "objects": {
              "bandage_roll": 1.0,
              "sinew_cord": 1.0
            },
            "step": 12,
            "source": "public_ground_observation"
          },
          "cellar": {
            "objects": {
              "salvage_cloth": 2.0
            },
            "step": 8,
            "source": "public_ground_observation"
          },
          "courtyard": {
            "objects": {
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
            "counts": {},
            "load": 0.0,
            "capacity": 20.0,
            "location": "barracks",
            "step": 2,
            "source": "public_container_inspection"
          }
        },
        "inventory": "scout_satchel_0",
        "recipes": {
          "padded_tunic": {
            "ingredients": [],
            "quantities": null,
            "stations": [
              "war_bench"
            ]
          },
          "stitched_panel": {
            "quantities": null,
            "ingredients": [
              "bandage_roll",
              "sinew_cord"
            ],
            "step": 12,
            "source": "public_inspection"
          },
          "ruin_maul": {
            "quantities": null,
            "ingredients": [
              "ruin_blade",
              "wooden_rod",
              "bandage_roll"
            ],
            "step": 12,
            "source": "public_inspection"
          },
          "war_strap": {
            "quantities": null,
            "ingredients": [
              "sinew_cord",
              "bandage_roll"
            ],
            "step": 12,
            "source": "public_inspection"
          }
        },
        "inspected": [
          "scout_satchel_0",
          "padded_tunic",
          "bandage_roll"
        ],
        "guards": {
          "barracks->cellar": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered cellar.",
            "step": 6
          },
          "cellar->courtyard": {
            "locked": false,
            "required": null,
            "expires_on": "explicit_locked_failure",
            "source": "I entered courtyard.\njames_owen enters the area.\n\n=== SIDE QUESTS UNLOCKED ===\nSide quests are now available! Completing them will grant you coins.\nTalk to james_owen to see your current tasks.\n============================",
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
        "observations": 37,
        "events": [],
        "pending_craft": null
      },
      "target": "craft 1 padded_tunic",
      "reason": "stage11_known_forward_bridge",
      "mechanisms": {
        "exploration": {
          "reason": "stage11_known_forward_bridge",
          "source": {
            "public_recipe": {
              "quantities": null,
              "ingredients": [
                "bandage_roll",
                "sinew_cord"
              ],
              "step": 12,
              "source": "public_inspection"
            },
            "unresolved_nodes": [
              "padded_tunic"
            ],
            "confirmed_goal_connection": false,
            "unknown_downstream_connection": true,
            "claim": "possible source of further rules, not a known hidden dependency"
          },
          "spent": 3,
          "limit": 18
        }
      },
      "stage7": {},
      "stage10": {
        "frozen_F0_candidate": "store 1 bandage_roll inventory",
        "base_action": "enter courtyard",
        "selected_action": "store 1 bandage_roll inventory",
        "reason": "retain_F0",
        "override": true,
        "overlay_changed_F0": false,
        "conditions": [
          {
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
                "observed_step": 12,
                "valid_until": "relevant public condition changes",
                "container": "scout_satchel_0"
              },
              {
                "kind": "transfer_source",
                "status": "SUPPORTED",
                "evidence": {
                  "current_held_and_ground": 1.0
                },
                "observed_step": 12,
                "valid_until": "relevant public condition changes"
              },
              {
                "kind": "container_capacity",
                "status": "UNKNOWN",
                "evidence": {
                  "load": 0.0,
                  "capacity": 20.0,
                  "item_volume": "UNKNOWN"
                },
                "observed_step": 12,
                "valid_until": "relevant public condition changes",
                "container": "scout_satchel_0"
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
        "S1_with_rank_candidate": "store 1 bandage_roll inventory",
        "selected_action": "store 1 bandage_roll inventory",
        "exploration_candidates": [
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
                "step": 12,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "padded_tunic"
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
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                },
                {
                  "kind": "transfer_source",
                  "status": "SUPPORTED",
                  "evidence": {
                    "current_held_and_ground": 1.0
                  },
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes"
                },
                {
                  "kind": "container_capacity",
                  "status": "UNKNOWN",
                  "evidence": {
                    "load": 0.0,
                    "capacity": 20.0,
                    "item_volume": "UNKNOWN"
                  },
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
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
                "step": 12,
                "source": "public_inspection"
              },
              "unresolved_nodes": [
                "padded_tunic"
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
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                },
                {
                  "kind": "transfer_source",
                  "status": "SUPPORTED",
                  "evidence": {
                    "current_held_and_ground": 1.0
                  },
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes"
                },
                {
                  "kind": "container_capacity",
                  "status": "UNKNOWN",
                  "evidence": {
                    "load": 0.0,
                    "capacity": 20.0,
                    "item_volume": "UNKNOWN"
                  },
                  "observed_step": 12,
                  "valid_until": "relevant public condition changes",
                  "container": "scout_satchel_0"
                }
              ]
            },
            "eligible": true,
            "preparation_steps": 1
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
                  "observed_step": 12,
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
              "step": 12,
              "source": "public_inspection"
            },
            "unresolved_nodes": [
              "padded_tunic"
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
                "observed_step": 12,
                "valid_until": "relevant public condition changes",
                "container": "scout_satchel_0"
              },
              {
                "kind": "transfer_source",
                "status": "SUPPORTED",
                "evidence": {
                  "current_held_and_ground": 1.0
                },
                "observed_step": 12,
                "valid_until": "relevant public condition changes"
              },
              {
                "kind": "container_capacity",
                "status": "UNKNOWN",
                "evidence": {
                  "load": 0.0,
                  "capacity": 20.0,
                  "item_volume": "UNKNOWN"
                },
                "observed_step": 12,
                "valid_until": "relevant public condition changes",
                "container": "scout_satchel_0"
              }
            ]
          },
          "eligible": true,
          "preparation_steps": 1
        },
        "public_goal_view": {
          "goal": "padded_tunic",
          "known_dependency_nodes": [
            "padded_tunic"
          ],
          "active_nodes": [
            "padded_tunic"
          ],
          "unresolved_recipe_nodes": [
            "padded_tunic"
          ],
          "nodes": {
            "padded_tunic": {
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
                  "war_bench"
                ]
              },
              "assessment": {
                "action": "craft 1 padded_tunic",
                "status": "REJECT",
                "conditions": [
                  {
                    "kind": "unchanged_failure",
                    "status": "REJECT",
                    "evidence": {
                      "action": "craft 1 padded_tunic",
                      "context": {
                        "ingredients": [],
                        "materials": {},
                        "stations": {
                          "war_bench": 0
                        },
                        "unknown_recipe_carried": {
                          "hands": {
                            "padded_tunic": 1.0
                          },
                          "equipment": {
                            "scout_satchel_0": 1.0
                          },
                          "containers": {
                            "scout_satchel_0": {}
                          }
                        }
                      },
                      "feedback": "Cannot craft padded_tunic. Missing necessary war_bench in the current area.",
                      "step": 10
                    },
                    "observed_step": 12,
                    "valid_until": "relevant public condition changes"
                  },
                  {
                    "kind": "station",
                    "status": "REJECT",
                    "evidence": {
                      "required": [
                        "war_bench"
                      ],
                      "current_ground": {
                        "bandage_roll": 1.0,
                        "sinew_cord": 1.0
                      }
                    },
                    "observed_step": 12,
                    "valid_until": "relevant public condition changes"
                  },
                  {
                    "kind": "recipe",
                    "status": "UNKNOWN",
                    "evidence": "ingredient names not publicly disclosed",
                    "observed_step": 12,
                    "valid_until": "relevant public condition changes"
                  }
                ]
              },
              "quantity_certainty": "UNKNOWN",
              "readiness_scope": "observed conditions and inherited FIFO floor; never native legality guarantee"
            }
          },
          "edges": {
            "padded_tunic": []
          },
          "unknown_scope": "missing recipe may be a raw material; possible bridges are not graph edges"
        },
        "queue": [
          "padded_tunic"
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
      "kind": "visit",
      "target": "salvage_cloth",
      "category": "known_location",
      "location": "cellar",
      "evidence": "historically seen object; current presence requires reconfirmation",
      "id": "c_e02a00b1c3e8",
      "confirmed_connection": false,
      "next_action": "enter cellar",
      "public_condition": "UNKNOWN"
    },
    {
      "kind": "inspect",
      "target": "padded_tunic",
      "category": "other_inspect",
      "evidence": "visible unresolved public prerequisite; repeat",
      "id": "c_0450ed6211e2",
      "confirmed_connection": true,
      "next_action": "inspect padded_tunic",
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
      "target": "sinew_cord",
      "category": "primitive",
      "evidence": "public method proposal; exact first action retained",
      "first_action": "inspect sinew_cord",
      "id": "c_9336e1422f2b",
      "confirmed_connection": false,
      "next_action": "inspect sinew_cord",
      "public_condition": "UNKNOWN"
    },
    {
      "kind": "primitive",
      "target": "bandage_roll",
      "category": "primitive",
      "evidence": "public method proposal; exact first action retained",
      "first_action": "store 1 bandage_roll inventory",
      "id": "c_e20aa056f29e",
      "confirmed_connection": false,
      "next_action": "store 1 bandage_roll inventory",
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
      "next_action": "enter cellar",
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
    "state_id": "d12_db9cf8a8d4ddadac",
    "method": "J3",
    "replicate": 0,
    "status": "completed",
    "parsed": {
      "selected_candidate_id": "c_3f33cf002d85",
      "ranked_candidate_ids": [
        "c_3f33cf002d85",
        "c_d6a4a748f3ca",
        "c_3005d7648aa4"
      ],
      "reason": "Need war_bench to craft padded_tunic; courtyard historically had one. Verify current presence before crafting intermediates.",
      "hypothesized_connection": "war_bench in courtyard enables padded_tunic craft, possibly via intermediate stitched_panel or war_strap.",
      "confidence": 0.5,
      "expected_information": "Whether war_bench currently exists in courtyard and what it enables.",
      "alternative_if_failed": "c_d6a4a748f3ca"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.001066212,
    "charged_or_reserved_usd": 0.001066212
  },
  {
    "state_id": "d12_db9cf8a8d4ddadac",
    "method": "J2",
    "replicate": 1,
    "status": "completed",
    "parsed": {
      "reasoning": "The padded_tunic recipe requires a war_bench, which was last seen in the courtyard. I need to reach the courtyard to craft another padded_tunic. The barracks only connects to the cellar, so I must go through the cellar to reach the courtyard.",
      "action": "enter cellar"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.000165732,
    "charged_or_reserved_usd": 0.000165732
  },
  {
    "state_id": "d12_db9cf8a8d4ddadac",
    "method": "J2",
    "replicate": 0,
    "status": "completed",
    "parsed": {
      "reasoning": "The padded_tunic recipe requires a war_bench, which was last observed in the courtyard. The barracks only connects to the cellar, but the courtyard is a known location I need to reach. I should explore toward the courtyard to find the war_bench and craft the second padded_tunic. First, I'll enter the cellar as the only available neighbor to progress toward the courtyard.",
      "action": "enter cellar"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.000195732,
    "charged_or_reserved_usd": 0.000195732
  },
  {
    "state_id": "d12_db9cf8a8d4ddadac",
    "method": "J3",
    "replicate": 1,
    "status": "completed",
    "parsed": {
      "selected_candidate_id": "c_3f33cf002d85",
      "ranked_candidate_ids": [
        "c_3f33cf002d85",
        "c_0450ed6211e2",
        "c_9336e1422f2b"
      ],
      "reason": "Need war_bench to craft padded_tunic; courtyard historically had one but current presence unknown.",
      "hypothesized_connection": "war_bench in courtyard enables padded_tunic craft once ingredients known.",
      "confidence": 0.4,
      "expected_information": "Whether war_bench is currently present in courtyard.",
      "alternative_if_failed": "c_0450ed6211e2"
    },
    "validation_errors": [],
    "requests": 1,
    "cost_usd": 0.00027953999999999994,
    "charged_or_reserved_usd": 0.00027953999999999994
  }
]
```

## 四方法的主选择与真实结果

| 方法 | 候选/提案 | 实际短分支 | 新增必要配方 | 原生拒绝数 | 停止原因 |
| --- | --- | --- | --- | --- | --- |
| J0 | c_9336e1422f2b | ["inspect sinew_cord"] | ["padded_tunic"] | 0 | inspection_attempt_completed |
| J1 | c_e20aa056f29e | ["store 1 bandage_roll inventory"] | [] | 0 | public_plan_complete_or_blocked |
| J2 | c_07db86249dd6 | ["enter cellar"] | [] | 0 | public_plan_complete_or_blocked |
| J3 | c_3f33cf002d85 | ["enter cellar","enter courtyard","inspect war_bench"] | [] | 0 | inspection_attempt_completed |

## 所有候选的真实分支（包括未选择候选）

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
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "567d5993e42900a9a7580a69764b28aff9250bfc8034847b5bed810a48f0f0b9",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "e60011a12227d9f2c8fbebb66265fa31703f2b3279ddb856de080f0f43c35684",
      "goal": false
    },
    {
      "index": 2,
      "action": "craft 2 war_strap",
      "before": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 15,
        "text": "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft war_strap. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "0213a4e847567a6863474e4b96773a2e9584b4c53876b3e542baf10b13aed42f",
      "goal": false
    },
    {
      "index": 3,
      "action": "enter cellar",
      "before": {
        "step": 15,
        "text": "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft war_strap. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 16,
        "text": "\nCurrent Time: 0001-01-01 10:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "e5668b8abd1cd73870c100356ca001c9e4add468ba932d44bf52bf3e9c6e81e6",
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
  "final_hash": "e5668b8abd1cd73870c100356ca001c9e4add468ba932d44bf52bf3e9c6e81e6",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_e02a00b1c3e8 / visit / salvage_cloth</summary>

```json
{
  "candidate": {
    "kind": "visit",
    "target": "salvage_cloth",
    "category": "known_location",
    "location": "cellar",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_e02a00b1c3e8",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "c2a0dae53bb8eb57e51ee2408ab75a63b04dbc41772a531e14aafb6d4a89b739",
      "goal": false
    },
    {
      "index": 1,
      "action": "inspect salvage_cloth",
      "before": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, cellar\n\nI inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "feedback": "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [
        "bandage_roll",
        "oil_bomb",
        "padded_lining",
        "ruin_gauntlets",
        "scout_satchel",
        "scrap_helm",
        "scrap_lantern",
        "sinew_cord",
        "war_banner",
        "war_parchment"
      ],
      "new_key_recipes": [
        "padded_lining",
        "sinew_cord"
      ],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "b10ee6e955dc801bbe8b9147b7f707e8919d21013a6f96b713a50b10360146ae",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 2,
  "new_key_recipes": [
    "padded_lining",
    "sinew_cord"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "b10ee6e955dc801bbe8b9147b7f707e8919d21013a6f96b713a50b10360146ae",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_0450ed6211e2 / inspect / padded_tunic</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "padded_tunic",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_0450ed6211e2",
    "confirmed_connection": true,
    "next_action": "inspect padded_tunic",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect padded_tunic",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [],
      "new_key_recipes": [],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "231fea0f2bdf471dee0c1a914e21733ca06bc120c60d640a68a4b052741a5fc5",
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
  "final_hash": "231fea0f2bdf471dee0c1a914e21733ca06bc120c60d640a68a4b052741a5fc5",
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
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "c9fb60b0cbfabacdc12b11c2fc01fa0edb6bc9fd45f557b2628c9cebabf4cfea",
      "goal": false
    },
    {
      "index": 1,
      "action": "store 1 sinew_cord inventory",
      "before": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "8ddf9a9d8cdcf012b1ecaafd4137f71f61a834dd5748ea45dee77ac1acd66758",
      "goal": false
    },
    {
      "index": 2,
      "action": "craft 2 stitched_panel",
      "before": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 15,
        "text": "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft stitched_panel. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "4bce3fbeb6d4a98ad1d9770dfb36eba6cb807187ae37b42cefa6917ae4ba9d32",
      "goal": false
    },
    {
      "index": 3,
      "action": "enter cellar",
      "before": {
        "step": 15,
        "text": "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, barracks\n\nCannot craft stitched_panel. Missing necessary war_bench in the current area.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see no objects near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 16,
        "text": "\nCurrent Time: 0001-01-01 10:40:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "eee8ea2f1f79aa6e8310b7548789637ce28878d6731596436fee0a0a45b00dde",
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
  "final_hash": "eee8ea2f1f79aa6e8310b7548789637ce28878d6731596436fee0a0a45b00dde",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_9336e1422f2b / inspect / sinew_cord</summary>

```json
{
  "candidate": {
    "kind": "inspect",
    "target": "sinew_cord",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "inspect sinew_cord",
    "id": "c_9336e1422f2b",
    "confirmed_connection": false,
    "next_action": "inspect sinew_cord",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "inspect sinew_cord",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [
        "bandage_roll",
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
        "scout_satchel",
        "scrap_buckler",
        "siege_crate",
        "spiked_club",
        "timber_sword",
        "war_codex",
        "warding_charm"
      ],
      "new_key_recipes": [
        "padded_tunic"
      ],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "13000d8c33736af242cdd43f567cd499b5dc128e6d24e80503482bee7c2e5afd",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [
    "padded_tunic"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "13000d8c33736af242cdd43f567cd499b5dc128e6d24e80503482bee7c2e5afd",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_e20aa056f29e / primitive / bandage_roll</summary>

```json
{
  "candidate": {
    "kind": "primitive",
    "target": "bandage_roll",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "store 1 bandage_roll inventory",
    "id": "c_e20aa056f29e",
    "confirmed_connection": false,
    "next_action": "store 1 bandage_roll inventory",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "store 1 bandage_roll inventory",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "c9fb60b0cbfabacdc12b11c2fc01fa0edb6bc9fd45f557b2628c9cebabf4cfea",
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
  "final_hash": "c9fb60b0cbfabacdc12b11c2fc01fa0edb6bc9fd45f557b2628c9cebabf4cfea",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "c2a0dae53bb8eb57e51ee2408ab75a63b04dbc41772a531e14aafb6d4a89b739",
      "goal": false
    },
    {
      "index": 1,
      "action": "enter courtyard",
      "before": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
      },
      "after": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 war_bench near me.\nI see james_owen nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "4d5c8901db0142c5f0fa5d318583bae9a774c35202edf49ca73b70f79bab1959",
      "goal": false
    },
    {
      "index": 2,
      "action": "inspect war_bench",
      "before": {
        "step": 14,
        "text": "\nCurrent Time: 0001-01-01 10:20:00\nCurrent Location: Ashen Bastion, courtyard\n\nI entered courtyard.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 war_bench near me.\nI see james_owen nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 15,
        "text": "\nCurrent Time: 0001-01-01 10:30:00\nCurrent Location: Ashen Bastion, courtyard\n\nI inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 war_bench near me.\nI see james_owen nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
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
      "state_hash": "a4e86c4ce4a42c7fafc3b40661f19529087362bdb0a372ff6842bb59bb718d6f",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 3,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "a4e86c4ce4a42c7fafc3b40661f19529087362bdb0a372ff6842bb59bb718d6f",
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
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "rejected": false,
      "new_public_recipes": [
        "bandage_roll",
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
        "scout_satchel",
        "scrap_buckler",
        "siege_crate",
        "spiked_club",
        "timber_sword",
        "war_codex",
        "warding_charm"
      ],
      "new_key_recipes": [
        "padded_tunic"
      ],
      "action_consumption": {},
      "action_production": {},
      "unrelated_craft": false,
      "unrelated_key_input_consumption": {},
      "environment_key_loss": {},
      "state_hash": "13000d8c33736af242cdd43f567cd499b5dc128e6d24e80503482bee7c2e5afd",
      "goal": false
    }
  ],
  "stop": "inspection_attempt_completed",
  "actions": 1,
  "new_key_recipes": [
    "padded_tunic"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "final_hash": "13000d8c33736af242cdd43f567cd499b5dc128e6d24e80503482bee7c2e5afd",
  "goal": false,
  "replayed_twice": true
}
```

</details>

<details><summary>c_07db86249dd6 / primitive / cellar</summary>

```json
{
  "candidate": {
    "kind": "primitive",
    "target": "cellar",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "enter cellar",
    "id": "c_07db86249dd6"
  },
  "trace": [
    {
      "index": 0,
      "action": "enter cellar",
      "before": {
        "step": 12,
        "text": "\nCurrent Time: 0001-01-01 10:00:00\nCurrent Location: Ashen Bastion, barracks\n\nI inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 1 bandage_roll, 1 sinew_cord near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: cellar.\n"
      },
      "after": {
        "step": 13,
        "text": "\nCurrent Time: 0001-01-01 10:10:00\nCurrent Location: Ashen Bastion, cellar\n\nI entered cellar.\n\nI am holding 1 padded_tunic.\nI have equipped 1 scout_satchel_0.\nI see 2 salvage_cloth near me.\nI see no one nearby.\n\nMy level is 1.\nMy attack is at 10.\nMy defense is at 0.\nMy health is at 100.\nMy experience is at 10.\n\nNeighboring areas: barracks, courtyard.\n"
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
      "state_hash": "c2a0dae53bb8eb57e51ee2408ab75a63b04dbc41772a531e14aafb6d4a89b739",
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
  "final_hash": "c2a0dae53bb8eb57e51ee2408ab75a63b04dbc41772a531e14aafb6d4a89b739",
  "goal": false,
  "replayed_twice": true
}
```

</details>
