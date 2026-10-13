# 按需LLM触发与规划机制

执行顺序保留公开确定性FIFO，并在无可靠动作时展开当前未完成依赖；具体记录目标配方、材料路径、必要区域对象路径或已知执行条件阻塞。已知公开解决方式直接执行。公开候选仅提供探索入口，不宣称隐藏配方关联。

| 触发类型 | 逻辑请求记录数 |
| --- | --- |
| missing_target_recipe | 150 |
| missing_material_path | 34 |
| missing_area_object_path | 7 |

本轮 344/513 个真实动作无需模型（67.1%）。接受 105、拒绝 86 个提案，接受率 55.0%。每个有效逻辑请求关联 1.340 步意图执行，意图执行期内实际生产动作 0 次、持有量增加的收取动作 0 次。这里只描述时序关联，不能解释为每个请求的因果增益。

拒绝理由：`{"target_not_publicly_named": 11, "evidence_unrelated_to_execution_entry": 44, "not_a_current_dependency_or_blocker": 10, "inherited_exploration_budget_exhausted": 11, "duplicate_subgoal_same_conditions": 3, "no_admissible_entry_or_known_conditions_blocked": 4, "recipe_unpublished_not_an_executable_craft_intent": 1, "already_inspected": 2}`。

相同公开上下文的有限重规划 11 次；同类型/对象/入口的重复提案 33 次，重复失败意图 0 次。所有触发、公开证据、引用和接受决定见 `planning_outcomes.jsonl.gz`。本轮无全局LLM排序、无多智能体、无每步强制模型调用。

## 从具体触发到实际进展

| 阻碍 | 逻辑请求 | 接受 | 完成 | 执行步 | 有必要配方增益的意图 | 多步完成 |
| --- | --- | --- | --- | --- | --- | --- |
| missing_area_object_path | 7 | 5 | 0 | 9 | 0 | 0 |
| missing_material_path | 34 | 13 | 3 | 28 | 3 | 2 |
| missing_target_recipe | 150 | 87 | 48 | 219 | 15 | 6 |

150/191（78.5%）请求仍在目标配方未知时发出；对象已经明确，但并非已形成必要制作链上的精确子问题。34次材料路径与7次区域对象路径请求更具体。接受意图期间的配方增益与后续制作要分开：本轮意图执行期没有制作/收取增益，但oil_bomb等任务确实在意图发现配方后由确定性模块完成制作，不能把“执行期0制作”解释为LLM毫无作用。
