# Stage17 SCAR失败原因归因

**14个失败任务全部纳入：13个原生失败/死亡、1个响应解析异常；没有100步耗尽，没有已制作最终目标却未取得的失败。** A–H允许重叠，表示有证据的现象/机制，不是唯一因果标签。

A：配方未发现（partial仅表示闭包部分未发现，未证明不可绕行）；B：已公开知识未转成对应制作链；C：材料/制作数量不一致；D：负重、库存、工作台、攻击等环境约束；E：同状态回放确认原提案具有局部信息/产出/生存优势；F(local)：探索额度、wait或停滞，但没有100步预算耗尽；G：已制最终目标却未取得；H：接口异常或不能隔离。所有分类需结合下文限定，不将B直接当成“已经具备可行执行条件”。

原生攻击死亡可能复活至100HP；腐蚀也可能直接令done为真、HP为0而death字段为false。诊断联合使用原始反馈、done、death、实际HP和统一终止状态。世界总量减少还包含NPC/世界动态，库存减少包含主动转移；未把原统计resource_loss_events等同于制作损耗。

## 02 war_banner：原生失败/死亡，53步

证据标签：A(partial), B, C, D, E(local)。

目标关系第11步、数量第12步公开；wooden_rod 关系始终未公开，尽管模型后来尝试制作它。第16、31步反复制作非目标依赖闭包内的 war_parchment，均材料不足；第49步 wooden_rod 缺工作台，第51步又材料不足，最终第53步遭攻击死亡。已知目标关系未形成有效材料链，但不能把未公开的所有闭包祖先都说成必须自行制作。批量2不是这两次拒绝的唯一解释：单件原提案也可能失败，详见反事实。

目标关系首次 11；目标数量首次 12。未知精确数量：scorched_plank, wooden_rod；已公开关系但未制作：scorched_plank, war_banner, wood_strip。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第11步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a011)|inspect war_parchment_0|inspect salvage_cloth|I was attacked by scrap_automaton_0 and lost 6 HP.|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a012)|pick up salvage_cloth|store 9 salvage_cloth inventory|I stored 9 salvage_cloth in my inventory.|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a016)|enter courtyard|craft 2 war_parchment|Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.|
|[A0 第22步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a022)|scavenge|inspect scorched_plank|I inspected scorched_plank: A plank cut from charred timber, still solid beneath the blackened surface.|
|[A0 第31步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a031)|enter courtyard|craft 2 war_parchment|Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.|
|[A0 第36步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a036)|pick up scorched_plank|store 1 scorched_plank inventory|I stored 1 scorched_plank in my inventory.|
|[A0 第49步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a049)|craft 1 wooden_rod|craft 2 wooden_rod|Cannot craft wooden_rod. Missing necessary war_bench in the current area. I was attacked by infernal_colossus_12 and lost 15 HP.|
|[A0 第51步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a051)|craft 1 wooden_rod|craft 2 wooden_rod|Cannot craft a single wooden_rod. Do not have sufficient amount of necessary ingredients.|
|[A0 第53步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a053)|scavenge|scavenge|I was attacked by iron_ravager_9 and lost 5 HP. I was attacked by scrap_automaton_15 and lost 2 HP. I have died.|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第9步](../../results/stage17/diagnostics/evidence/s17-02-robot_kingdom-war_banner.md#a0-a009)|talk to alex_smith → enter barracks|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均未成功，不能从本任务推断某基线已经解决此机制。

## 03 oil_bomb：原生失败/死亡，19步

证据标签：A(partial), B, D, E(local)。

oil_bomb 关系第11步、数量第13步已公开，但其依赖链没有完成。第14步把 talk to old_marshal 覆盖成一次存入10个 scrap_iron，随后每步出现14HP腐蚀损失；第15步制作与目标闭包无关的 iron_nugget 又缺 crucible。第19步公开 oil_flask 名称后当步遭攻击死亡。知识缺口与非目标资源负担并存，不能将死亡单独归因为规则发现不足。

目标关系首次 11；目标数量首次 13。未知精确数量：charcoal_brick, oil_flask, rubble_chunk；已公开关系但未制作：oil_bomb, oil_flask。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第11步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a011)|talk to old_marshal|inspect salvage_cloth|I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a013)|pick up salvage_cloth|pick up salvage_cloth|I picked up salvage_cloth.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a014)|talk to old_marshal|store 10 scrap_iron inventory|I stored 10 scrap_iron in my inventory. The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (86 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a015)|talk to old_marshal|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (72 HP remaining)|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a019)|pick up charite|inspect devil_oil|I was attacked by infernal_colossus_4 and lost 15 HP. I was attacked by infernal_colossus_9 and lost 15 HP. I have died.|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-03-robot_kingdom-oil_bomb.md#a0-a014)|talk to old_marshal → store 10 scrap_iron inventory|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败；ReAct、LongContext运行到100步也未完成。

## 05 cog_assembly：原生失败/死亡，20步

证据标签：A, D, E(local)。

直到终止都未公开 cog_assembly 关系。第15步将离开提案改为存入13个 scrap_iron，反馈同时给出攻击与20HP腐蚀；第18步丢弃后停止腐蚀，第19步检查确认空包，第20步控制器再次收取同样13个材料并触发原生失败。这里有明确的已知负面效果未约束后续收取证据，不是从最终失败反推模块错误。

目标关系首次 未达到；目标数量首次 未达到。未知精确数量：cog_assembly；已公开关系但未制作：∅。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a014)|pick up sinew_cord|inspect war_parchment_0|I was attacked by iron_ravager_0 and lost 17 HP.|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a015)|enter courtyard|store 13 scrap_iron inventory|I stored 13 scrap_iron in my inventory. I was attacked by infernal_colossus_0 and lost 15 HP. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (48 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a016)|enter courtyard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (28 HP remaining)|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a018)|discard 13 scrap_iron scout_satchel_0|discard 13 scrap_iron scout_satchel_0|I discarded 13 scrap_iron from scout_satchel_0.|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a019)|talk to alex_smith|inspect inventory|I inspected my inventory.|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a020)|talk to alex_smith|store 13 scrap_iron inventory|I stored 13 scrap_iron in my inventory. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (-12 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a015)|enter courtyard → store 13 scrap_iron inventory|原提案保留更多HP|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a0-a020)|talk to alex_smith → store 13 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** LongContext第1步谈话、第2步进入barracks、第6步到cellar、第7步取得devil_oil即公开目标配方，最后第56步制作、第58步取得。两者第1步便分叉；有解释价值的阶段是SCAR第15–20步囤积/丢弃/重收，与LC较早跨区取样。LC也有手部容量错误，不能描述成完美执行。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|LongContext|1|7|7|[A2 第56步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a2-a056)|[A2 第58步](../../results/stage17/diagnostics/evidence/s17-05-robot_kingdom-cog_assembly.md#a2-a058)|


## 06 cog_crossbow：原生失败/死亡，23步

证据标签：A(partial), B, D, E(local)。

目标关系第13步已公开，数量第20步公开，但 cog_assembly、gearwork_frame、iron_bar 关系仍缺。第14步收17个 scrap_iron 后每步腐蚀28HP；第15步覆盖模型的 discard 17 scrap_iron 为缺站点的 iron_nugget 制作；第16、19步实际丢弃均阻止继续腐蚀，控制器第18、23步又重新收17个。第23步原提案因手满也不可执行，但离线实测不会当步终止；只能称控制器造成已验证的局部生存损失，不能称原提案合理或可完成任务。

目标关系首次 13；目标数量首次 20。未知精确数量：cog_assembly, gearwork_frame, iron_bar；已公开关系但未制作：cog_crossbow, iron_nugget, sinew_cord。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a013)|enter courtyard|inspect sinew_cord|I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a014)|pick up sinew_cord|store 17 scrap_iron inventory|I stored 17 scrap_iron in my inventory. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (72 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a015)|discard 17 scrap_iron scout_satchel_0|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (44 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a016)|discard 17 scrap_iron scout_satchel_0|discard 17 scrap_iron scout_satchel_0|I discarded 17 scrap_iron from scout_satchel_0.|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a018)|pick up sinew_cord|store 17 scrap_iron inventory|I stored 17 scrap_iron in my inventory. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (16 HP remaining)|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a019)|discard 17 scrap_iron scout_satchel_0|discard 17 scrap_iron scout_satchel_0|I discarded 17 scrap_iron from scout_satchel_0.|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a020)|pick up sinew_cord|pick up sinew_cord|I picked up sinew_cord.|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a021)|pick up salvage_cloth|pick up salvage_cloth|I picked up salvage_cloth.|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a023)|pick up salvage_cloth|store 17 scrap_iron inventory|I stored 17 scrap_iron in my inventory. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (-12 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a012)|pick up sinew_cord → inspect scrap_iron|原提案新增闭包配方, 原提案新增相关材料类型|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a014)|pick up sinew_cord → store 17 scrap_iron inventory|原提案保留更多HP, 原提案新增相关材料类型|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a015)|discard 17 scrap_iron scout_satchel_0 → craft 2 iron_nugget|原提案保留更多HP|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a018)|pick up sinew_cord → store 17 scrap_iron inventory|原提案保留更多HP, 原提案新增相关材料类型|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-06-robot_kingdom-cog_crossbow.md#a0-a023)|pick up salvage_cloth → store 17 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败，没有成功轨迹可支持完整通关因果解释。

## 07 charcoal_brick：原生失败/死亡，23步

证据标签：B, C, D, E(local)。

第14步收8个 scrap_iron，之后持续10HP腐蚀；第21步才发现 charcoal_brick 关系，第22步取得2个charite后知道单件需3个，第23步终止。精确数量已经公开但材料数量仍不足，所在地还缺工作台。第21、22步原模型提案 craft 1 charcoal_brick 的同状态回放均不能成功，不能把这次覆盖称为阻止了可行制作。更早的无关材料收取与持续腐蚀缩短了可用生存窗口。

目标关系首次 21；目标数量首次 22。未知精确数量：∅；已公开关系但未制作：charcoal_brick。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a014)|talk to scout_lyra|store 8 scrap_iron inventory|I stored 8 scrap_iron in my inventory. The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (90 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a015)|talk to scout_lyra|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a020)|enter cellar|enter cellar|The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (30 HP remaining)|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a021)|craft 1 charcoal_brick|inspect charite|The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (20 HP remaining)|
|[A0 第22步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a022)|craft 1 charcoal_brick|store 2 charite inventory|I stored 2 charite in my inventory. The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (10 HP remaining)|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a023)|enter watchtower|inspect devil_oil|The malevolent energy of 8 devil-forged objects seeps into my flesh, draining 10 HP. Carrying more than 3 accursed items invites corruption! (0 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a0-a014)|talk to scout_lyra → store 8 scrap_iron inventory|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** LongContext第31步才公开目标关系，比SCAR更晚，但之后多次整理手部/包内材料，第48步仍制作失败，直到第66步成功制作、第67步取得；其成功来自存活后继续完成数量与可访问库存安排，不是更早发现规则。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|LongContext|1|31|31|[A2 第66步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a2-a066)|[A2 第67步](../../results/stage17/diagnostics/evidence/s17-07-robot_kingdom-charcoal_brick.md#a2-a067)|


## 08 iron_nugget：原生失败/死亡，17步

证据标签：B, D, E(local)。

第12步公开目标关系，第13步把单件拾取变为收13个scrap_iron，产生每步20HP腐蚀；第14步目标制作因缺crucible失败。之后第15步检查sinew_cord、第16步收7个charred_timber、第17步制作非目标ruin_club并终止。第10步原提案inspect scrap_iron的离线回放能提前获得目标关系，但不足以证明最终可成功；目标制作站点缺口同样直接可见。

目标关系首次 12；目标数量首次 13。未知精确数量：∅；已公开关系但未制作：iron_nugget。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第9步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a009)|talk to alex_smith|enter barracks|I was attacked by iron_ravager_0 and lost 17 HP.|
|[A0 第10步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a010)|inspect scrap_iron|inspect charred_timber|I inspected charred_timber: A blackened timber salvaged from a burned kingdom, still sturdy enough for crafting.|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a012)|pick up scrap_iron|inspect scrap_iron|I inspected scrap_iron: Bent iron fragments torn from a destroyed war machine's hull.|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a013)|pick up scrap_iron|store 13 scrap_iron inventory|I stored 13 scrap_iron in my inventory. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (63 HP remaining)|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a014)|craft 1 iron_nugget|craft 1 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (43 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a015)|enter courtyard|inspect sinew_cord|The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (23 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a016)|enter courtyard|store 7 charred_timber inventory|I stored 7 charred_timber in my inventory. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (3 HP remaining)|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a017)|enter courtyard|craft 2 ruin_club|I successfully crafted 2 ruin_club. It is now on the ground. The malevolent energy of 13 devil-forged objects seeps into my flesh, draining 20 HP. Carrying more than 3 accursed items invites corruption! (-17 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第9步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a009)|talk to alex_smith → enter barracks|原提案保留更多HP|
|[A0 第10步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a010)|inspect scrap_iron → inspect charred_timber|原提案新增闭包配方|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-08-robot_kingdom-iron_nugget.md#a0-a013)|pick up scrap_iron → store 13 scrap_iron inventory|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败；无证据支持只调整记忆即可解决站点与生存约束。

## 09 repair_kit：响应/解析异常，40步

证据标签：A(partial), B, D, F(local), H, E(local)。

目标关系/数量第12/13步公开。第27、28步原提案制作repair_kit被覆盖成wait，但同状态回放显示缺war_bench，故没有验证丢失可行制作；任务还未取得oil_flask。第29步开始携带过量诅咒物，第35–40步继续因devil_oil增加负担。实际执行40步，直接终止原因是第41个决策的三次响应均未通过解析；这不是100步耗尽。F只表示两步wait和探索停滞的局部浪费，H记录接口异常，不能写成确定的全部失败根因。

目标关系首次 12；目标数量首次 13。未知精确数量：rubble_chunk, sinew_cord；已公开关系但未制作：oil_flask, repair_kit, sinew_cord。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a012)|pick up salvage_cloth|inspect scrap_iron|I inspected scrap_iron: Bent iron fragments torn from a destroyed war machine's hull.|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a013)|pick up scrap_iron|pick up scrap_iron|I picked up scrap_iron.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a014)|pick up scrap_iron|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. I was attacked by scrap_automaton_0 and lost 6 HP.|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a017)|pick up sinew_cord|enter watchtower|I entered watchtower.|
|[A0 第22步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a022)|pick up sinew_cord|store 1 sinew_cord inventory|I stored 1 sinew_cord in my inventory. I was attacked by scrap_automaton_0 and lost 6 HP.|
|[A0 第24步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a024)|pick up scrap_iron|store 3 scrap_iron inventory|I stored 3 scrap_iron in my inventory.|
|[A0 第27步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a027)|craft 1 repair_kit|wait|I waited for a while.|
|[A0 第28步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a028)|craft 1 repair_kit|wait|I waited for a while.|
|[A0 第29步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a029)|pick up scrap_iron|pick up scrap_iron|The malevolent energy of 4 devil-forged objects seeps into my flesh, draining 2 HP. Carrying more than 3 accursed items invites corruption! (80 HP remaining)|
|[A0 第35步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a035)|pick up devil_oil|pick up devil_oil|I was attacked by scrap_automaton_1 and lost 10 HP. The malevolent energy of 6 devil-forged objects seeps into my flesh, draining 6 HP. Carrying more than 3 accursed items invites corruption! (44 HP remaining)|
|[A0 第38步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a038)|enter barracks|inspect devil_oil|The malevolent energy of 7 devil-forged objects seeps into my flesh, draining 8 HP. Carrying more than 3 accursed items invites corruption! (22 HP remaining)|
|[A0 第40步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a040)|store 1 devil_oil scout_satchel_0|inspect inventory|The malevolent energy of 7 devil-forged objects seeps into my flesh, draining 8 HP. Carrying more than 3 accursed items invites corruption! (6 HP remaining)|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第10步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a010)|pick up scrap_iron → inspect charred_timber|原提案新增闭包配方, 原提案新增相关材料类型|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a018)|enter barracks → inspect iron_bar|原提案保留更多HP|
|[A0 第30步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a0-a030)|pick up scrap_iron → store 2 scrap_iron inventory|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** LongContext第3步就公开目标关系，在第28步取得rubble后形成可执行路线：第31步rubble_chunk、第33步oil_flask、第35步repair_kit、第36步取得。SCAR第14步却转向不必要的iron_nugget，第17步去watchtower；这是第一段清晰的依赖链执行分歧，但两条模型采样并非严格因果对照。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|LongContext|1|3|3|[A2 第35步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a2-a035)|[A2 第36步](../../results/stage17/diagnostics/evidence/s17-09-robot_kingdom-repair_kit.md#a2-a036)|


## 11 hellcoal_concentrate：原生失败/死亡，24步

证据标签：A, D, E(local)。

目标配方始终未公开。第14步收11个scrap_iron后每步腐蚀16HP；第18步尝试drop失败，因为材料在包里，第19、22步discard成功。控制器在检查确认空包后第21、24步重收同样11个，最后触发腐蚀终止。负面反馈已经公开，重复收取仍发生；这比笼统的长期记忆不足更具体。

目标关系首次 未达到；目标数量首次 未达到。未知精确数量：hellcoal_concentrate；已公开关系但未制作：∅。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a014)|pick up sinew_cord|store 11 scrap_iron inventory|I stored 11 scrap_iron in my inventory. The malevolent energy of 11 devil-forged objects seeps into my flesh, draining 16 HP. Carrying more than 3 accursed items invites corruption! (84 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a015)|enter courtyard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 11 devil-forged objects seeps into my flesh, draining 16 HP. Carrying more than 3 accursed items invites corruption! (68 HP remaining)|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a018)|drop scrap_iron|drop scrap_iron|Cannot drop scrap_iron, not found in hand. The malevolent energy of 11 devil-forged objects seeps into my flesh, draining 16 HP. Carrying more than 3 accursed items invites corruption! (20 HP remaining)|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a019)|discard 11 scrap_iron scout_satchel_0|discard 11 scrap_iron scout_satchel_0|I discarded 11 scrap_iron from scout_satchel_0.|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a020)|enter cellar|inspect inventory|I inspected my inventory.|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a021)|enter cellar|store 11 scrap_iron inventory|I stored 11 scrap_iron in my inventory. The malevolent energy of 11 devil-forged objects seeps into my flesh, draining 16 HP. Carrying more than 3 accursed items invites corruption! (4 HP remaining)|
|[A0 第22步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a022)|discard 11 scrap_iron inventory|discard 11 scrap_iron inventory|I discarded 11 scrap_iron from my inventory.|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a023)|enter cellar|inspect inventory|I inspected my inventory.|
|[A0 第24步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a024)|enter cellar|store 11 scrap_iron inventory|I stored 11 scrap_iron in my inventory. The malevolent energy of 11 devil-forged objects seeps into my flesh, draining 16 HP. Carrying more than 3 accursed items invites corruption! (-12 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a014)|pick up sinew_cord → store 11 scrap_iron inventory|原提案保留更多HP|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a021)|enter cellar → store 11 scrap_iron inventory|原提案保留更多HP|
|[A0 第24步](../../results/stage17/diagnostics/evidence/s17-11-robot_kingdom-hellcoal_concentrate.md#a0-a024)|enter cellar → store 11 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败。

## 12 ruin_spear：原生失败/死亡，24步

证据标签：A(partial), B, D, E(local)。

目标关系第13步、数量第17步公开。第15步制作2个ruin_club不属于目标依赖闭包，之后第18步收12个scrap_iron并每步腐蚀18HP；第22步丢弃、第23步确认库存后，第24步再次收取导致终止。目标依赖关系仍缺多项，不能断言只修复收取循环便能完成复杂目标。

目标关系首次 13；目标数量首次 17。未知精确数量：knapped_edge, rubble_chunk, ruin_slab, sinew_cord, wood_strip, wooden_rod；已公开关系但未制作：ruin_spear, scorched_plank, sinew_cord。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a013)|enter courtyard|inspect sinew_cord|I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a014)|pick up sinew_cord|store 8 charred_timber inventory|I stored 8 charred_timber in my inventory.|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a015)|pick up sinew_cord|craft 2 ruin_club|I successfully crafted 2 ruin_club. It is now on the ground.|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a017)|pick up sinew_cord|pick up sinew_cord|I picked up sinew_cord.|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a018)|enter courtyard|store 12 scrap_iron inventory|I stored 12 scrap_iron in my inventory. The malevolent energy of 12 devil-forged objects seeps into my flesh, draining 18 HP. Carrying more than 3 accursed items invites corruption! (71 HP remaining)|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a019)|enter courtyard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 12 devil-forged objects seeps into my flesh, draining 18 HP. Carrying more than 3 accursed items invites corruption! (53 HP remaining)|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a021)|inspect war_bench|inspect war_bench|The malevolent energy of 12 devil-forged objects seeps into my flesh, draining 18 HP. Carrying more than 3 accursed items invites corruption! (17 HP remaining)|
|[A0 第22步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a022)|discard 12 scrap_iron scout_satchel_0|discard 12 scrap_iron scout_satchel_0|I discarded 12 scrap_iron from scout_satchel_0.|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a023)|talk to alex_smith|inspect inventory|I inspected my inventory.|
|[A0 第24步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a024)|talk to alex_smith|store 12 scrap_iron inventory|I stored 12 scrap_iron in my inventory. The malevolent energy of 12 devil-forged objects seeps into my flesh, draining 18 HP. Carrying more than 3 accursed items invites corruption! (-1 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第11步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a011)|pick up sinew_cord → inspect salvage_cloth|原提案新增闭包配方, 原提案新增相关材料类型|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a016)|enter courtyard → inspect inventory|原提案保留更多HP|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a018)|enter courtyard → store 12 scrap_iron inventory|原提案保留更多HP|
|[A0 第24步](../../results/stage17/diagnostics/evidence/s17-12-robot_kingdom-ruin_spear.md#a0-a024)|talk to alex_smith → store 12 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败；深依赖难度和生存执行问题无法从本轮单任务隔离。

## 13 rubble_chunk：原生失败/死亡，19步

证据标签：A, D, E(local)。

rubble_chunk 关系始终未公开。第14步收17个scrap_iron并每步腐蚀28HP，第15步试制缺crucible的iron_nugget；第17步丢弃、第18步确认空包，第19步控制器把单件拾取改成收17个导致原生失败。离线单件拾取同状态可执行且保留16HP，这是最清楚的数量收取导致局部生存损失之一；它不是制作批量错误，故归D/E而不是把所有数量相关现象塞入C。

目标关系首次 未达到；目标数量首次 未达到。未知精确数量：rubble_chunk；已公开关系但未制作：∅。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a014)|pick up sinew_cord|store 17 scrap_iron inventory|I stored 17 scrap_iron in my inventory. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (72 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a015)|inspect crown_shard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (44 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a016)|enter courtyard|enter courtyard|The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (16 HP remaining)|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a017)|discard 17 scrap_iron scout_satchel_0|discard 17 scrap_iron scout_satchel_0|I discarded 17 scrap_iron from scout_satchel_0.|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a018)|pick up scrap_iron|inspect inventory|I inspected my inventory.|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a019)|pick up scrap_iron|store 17 scrap_iron inventory|I stored 17 scrap_iron in my inventory. The malevolent energy of 17 devil-forged objects seeps into my flesh, draining 28 HP. Carrying more than 3 accursed items invites corruption! (-12 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a014)|pick up sinew_cord → store 17 scrap_iron inventory|原提案保留更多HP|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a0-a019)|pick up scrap_iron → store 17 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** ReAct第12步到cellar、第13步拾取rubble公开配方，第20步制作、第21步取得；Ada第9步到cellar、第12步inspect rubble公开关系，第21步制作、第22步取得。两者都也有无效动作，但实际从探索转到目标材料；SCAR较早的非必要scrap_iron路线截断了探索。DAG也在第29步成功。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|ReAct+STM|1|13|13|[A1 第20步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a1-a020)|[A1 第21步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a1-a021)|
|AdaPlanner适配|1|12|19|[A3 第21步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a3-a021)|[A3 第22步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a3-a022)|
|Deterministic DAG Planner|1|24|25|[A4 第27步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a4-a027)|[A4 第29步](../../results/stage17/diagnostics/evidence/s17-13-robot_kingdom-rubble_chunk.md#a4-a029)|


## 14 oil_flask：原生失败/死亡，20步

证据标签：A, D, E(local)。

oil_flask 关系始终未公开。第14步收10个scrap_iron后持续14HP腐蚀；第18步丢弃后仅剩7HP，第19步检查空包，第20步把enter cellar覆盖成再收10个并终止。离线原提案确实能进入cellar且保留7HP，但未验证之后能否完成目标。

目标关系首次 未达到；目标数量首次 未达到。未知精确数量：oil_flask, rubble_chunk；已公开关系但未制作：∅。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a013)|enter courtyard|inspect sinew_cord|I was attacked by scrap_automaton_0 and lost 10 HP.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a014)|enter courtyard|store 10 scrap_iron inventory|I stored 10 scrap_iron in my inventory. I was attacked by scrap_automaton_0 and lost 10 HP. The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (49 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a015)|enter courtyard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (35 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a016)|enter courtyard|enter courtyard|The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (21 HP remaining)|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a017)|talk to alex_smith|talk to alex_smith|The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (7 HP remaining)|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a018)|discard 10 scrap_iron scout_satchel_0|discard 10 scrap_iron scout_satchel_0|I discarded 10 scrap_iron from scout_satchel_0.|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a019)|drop scrap_iron|inspect inventory|I inspected my inventory.|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a020)|enter cellar|store 10 scrap_iron inventory|I stored 10 scrap_iron in my inventory. The malevolent energy of 10 devil-forged objects seeps into my flesh, draining 14 HP. Carrying more than 3 accursed items invites corruption! (-7 HP remaining) The creeping corruption of the devil-forged machines has overwhelmed me!|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a012)|enter courtyard → inspect scrap_iron|原提案保留更多HP|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a013)|enter courtyard → inspect sinew_cord|原提案保留更多HP|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a014)|enter courtyard → store 10 scrap_iron inventory|原提案保留更多HP|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a0-a020)|enter cellar → store 10 scrap_iron inventory|原提案避免当步失败|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** LongContext第15、18步只取/存少量scrap_iron，第22步取得devil_oil公开目标，第23步取得rubble，第33步制作rubble_chunk；经历后续库存整理，第60步制作oil_flask、第61步取得。SCAR第14步大量收取是关键风险分歧；DAG第34步也成功。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|LongContext|1|22|22|[A2 第60步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a2-a060)|[A2 第61步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a2-a061)|
|Deterministic DAG Planner|1|22|23|[A4 第32步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a4-a032)|[A4 第34步](../../results/stage17/diagnostics/evidence/s17-14-robot_kingdom-oil_flask.md#a4-a034)|


## 15 gate_cipher：原生失败/死亡，33步

证据标签：B, D, E(local)。

目标关系第12步、数量第14步公开，仍未取得关键cog并制作。第14步收16个scrap_iron后每步腐蚀26HP；第17步discard15个后停止腐蚀，但仅剩11HP。后续多次跨区/检查，到第33步遭攻击死亡。不能因关系已公开就认定所有材料和执行条件已就绪；更直接的是早期过量材料负担与随后低血量探索。

目标关系首次 12；目标数量首次 14。未知精确数量：∅；已公开关系但未制作：gate_cipher。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a012)|talk to vessa_ironhand|inspect scrap_iron|I inspected scrap_iron: Bent iron fragments torn from a destroyed war machine's hull.|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a014)|pick up scrap_iron|store 16 scrap_iron inventory|I stored 16 scrap_iron in my inventory. The malevolent energy of 16 devil-forged objects seeps into my flesh, draining 26 HP. Carrying more than 3 accursed items invites corruption! (63 HP remaining)|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a015)|enter courtyard|craft 2 iron_nugget|Cannot craft iron_nugget. Missing necessary crucible in the current area. The malevolent energy of 16 devil-forged objects seeps into my flesh, draining 26 HP. Carrying more than 3 accursed items invites corruption! (37 HP remaining)|
|[A0 第16步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a016)|enter courtyard|enter courtyard|The malevolent energy of 16 devil-forged objects seeps into my flesh, draining 26 HP. Carrying more than 3 accursed items invites corruption! (11 HP remaining)|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a017)|discard 15 scrap_iron scout_satchel_0|discard 15 scrap_iron scout_satchel_0|I discarded 15 scrap_iron from scout_satchel_0.|
|[A0 第18步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a018)|scavenge|inspect inventory|I inspected my inventory.|
|[A0 第23步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a023)|enter watchtower|enter watchtower|I was attacked by ember_scavenger_12 and lost 8 HP.|
|[A0 第25步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a025)|scavenge|scavenge|I searched the ruins but found nothing. Defeating different types of war machines might reveal knowledge of hidden caches.|
|[A0 第27步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a027)|inspect war_bench|inspect war_bench|I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.|
|[A0 第31步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a031)|pick up charcoal_stylus|pick up charcoal_stylus|I picked up charcoal_stylus.|
|[A0 第33步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a033)|enter watchtower|enter watchtower|I was attacked by ember_scavenger_3 and lost 8 HP. I have died.|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第14步](../../results/stage17/diagnostics/evidence/s17-15-robot_kingdom-gate_cipher.md#a0-a014)|pick up scrap_iron → store 16 scrap_iron inventory|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败；ReAct和LongContext到100步也未完成，目标cog取得问题仍需保留。

## 18 sharpened_blade：原生失败/死亡，78步

证据标签：B, C, D, F(local), E(local)。

第47步依赖闭包关系与数量全部公开，但只在第53步实际制成pipe_handle；第56步forged_blade因缺furnace失败，尚不能说执行条件已齐。第21、53步请求制作2个，环境仅够1个并实际制作1个，证实批量与可用材料不一致但不是完整制作失败。第34–36、39–40步共5次wait，探索额度达到上限；随后仍有行动，第78步攻击死亡，未耗尽100步。第71步原提案最终制作在离线回放中缺workbench，故不能宣称控制器阻止了成功；furnace约束和未完成依赖仍在。

目标关系首次 12；目标数量首次 13。未知精确数量：∅；已公开关系但未制作：duct_tape, forged_blade, iron_bar, sharpened_blade。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a012)|pick up wood_log|inspect glass_shard|I inspected glass_shard: A jagged piece of broken window glass, dangerously sharp.|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a013)|pick up glass_shard|pick up glass_shard|I picked up glass_shard.|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a019)|enter ward|craft 2 bandage|Cannot craft bandage. Missing necessary workbench in the current area. I was attacked by licker_1 and lost 15 HP.|
|[A0 第21步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a021)|enter ward|craft 2 bandage|Only enough ingredients to craft 1 bandage. I successfully crafted 1 bandage. It is now on the ground.|
|[A0 第34步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a034)|enter room|wait|I waited for a while.|
|[A0 第35步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a035)|enter room|wait|I waited for a while.|
|[A0 第36步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a036)|enter room|wait|I waited for a while.|
|[A0 第39步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a039)|enter morgue|wait|I waited for a while.|
|[A0 第40步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a040)|enter morgue|wait|I waited for a while.|
|[A0 第42步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a042)|pick up scrap_metal|store 1 scrap_metal inventory|I stored 1 scrap_metal in my inventory.|
|[A0 第47步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a047)|pick up iron_bar|store 1 iron_bar inventory|I stored 1 iron_bar in my inventory.|
|[A0 第51步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a051)|pick up scrap_metal|craft 2 pipe_handle|Cannot craft pipe_handle. Missing necessary workbench in the current area.|
|[A0 第53步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a053)|craft 1 pipe_handle|craft 2 pipe_handle|Only enough ingredients to craft 1 pipe_handle. I successfully crafted 1 pipe_handle. It is now on the ground.|
|[A0 第54步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a054)|pick up pipe_handle|inspect inventory|I inspected my inventory.|
|[A0 第56步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a056)|craft 1 forged_blade|craft 2 forged_blade|Cannot craft forged_blade. Missing necessary furnace in the current area.|
|[A0 第69步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a069)|enter lobby|inspect iron_bar|I was attacked by zombie_1 and lost 11 HP.|
|[A0 第71步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a071)|craft 1 sharpened_blade|inspect pipe_handle|I inspected pipe_handle: A short section of pipe wrapped in tape for a better grip.|
|[A0 第77步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a077)|craft 1 forged_blade|store 1 scrap_metal inventory|I stored 1 scrap_metal in my inventory. I was attacked by zombie_1 and lost 11 HP.|
|[A0 第78步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a078)|enter lobby|inspect blue_herb|I was attacked by licker_0 and lost 21 HP. I have died.|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-18-quarantine-sharpened_blade.md#a0-a019)|enter ward → craft 2 bandage|原提案保留更多HP|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** 五方法均失败，不能把SCAR的已知规则未完成转化为LongContext在该任务已解决的证据。

## 21 pipe_handle：原生失败/死亡，20步

证据标签：B, D, E(local)。

第10步进入rooftop时天黑，第11步进入morgue；第12–19步持续检查多种物品并遭多次攻击。第19步才公开目标关系，数量仍未知；第20步拾取rag后死亡。第12步模型提议pick up scrap_metal可在同状态提前公开目标关系，而控制器先检查blue_herb，形成可验证的局部信息机会损失；不能保证能消除同状态攻击或完成任务。

目标关系首次 19；目标数量首次 未达到。未知精确数量：pipe_handle；已公开关系但未制作：duct_tape, pipe_handle。

|动作证据|原始LLM提案|实际动作|原始反馈摘录|
|---|---|---|---|
|[A0 第10步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a010)|talk to alex_smith|enter rooftop|I was attacked by zombie_2 and lost 7 HP.|
|[A0 第11步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a011)|enter lobby|enter morgue|I entered morgue.|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a012)|pick up scrap_metal|inspect blue_herb|I was attacked by licker_0 and lost 15 HP.|
|[A0 第13步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a013)|talk to olivia_grant|inspect chemical|I was attacked by licker_0 and lost 15 HP.|
|[A0 第15步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a015)|talk to olivia_grant|inspect iron_bar|I was attacked by tyrant_0 and lost 29 HP.|
|[A0 第17步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a017)|talk to olivia_grant|inspect rag|I was attacked by licker_0 and lost 15 HP.|
|[A0 第19步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a019)|enter ward|inspect scrap_metal|I inspected scrap_metal: Twisted metal salvaged from wrecked equipment and collapsed walls.|
|[A0 第20步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a020)|pick up rag|pick up rag|I was attacked by zombie_4 and lost 19 HP. I have died.|


|同状态动作|原提案→实际|直接验证的局部差异|
|---|---|---|
|[A0 第10步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a010)|talk to alex_smith → enter rooftop|原提案保留更多HP|
|[A0 第12步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a0-a012)|pick up scrap_metal → inspect blue_herb|原提案新增闭包配方, 原提案新增相关材料类型|


局部信息/生命优势不等于完整任务成功；不同维度有取舍。原提案也可能非法，例如cog_crossbow末步手满，但仍避免了控制器引入的当步致命负重。

**成功对照的实际路线与分歧：** ReAct、LongContext均第4步谈话、第5步进入ward，从现成scrap_metal与duct_tape转向lobby工作台，分别第9/13步制作、第10/14步取得。Ada同样第5步进入ward，虽有反复库存错误，第36步首次制作、第42步才取得。SCAR第10–11步选择rooftop/morgue并持续检查，是与三条成功轨迹相比最早明确的路线机制分歧；时间/天气/敌人随后分叉，不能当作模块因果效应。

|成功对照|首次动作不同|目标关系首次|数量首次|首次目标制作|成功取得|
|---|---|---|---|---|---|
|ReAct+STM|1|6|6|[A1 第9步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a1-a009)|[A1 第10步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a1-a010)|
|LongContext|1|8|9|[A2 第13步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a2-a013)|[A2 第14步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a2-a014)|
|AdaPlanner适配|1|24|24|[A3 第36步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a3-a036)|[A3 第42步](../../results/stage17/diagnostics/evidence/s17-21-quarantine-pipe_handle.md#a3-a042)|


## 证据强度与不成立的归因

|重叠标签|任务数|
|---|---|
|A|4|
|A(partial)|5|
|B|10|
|C|3|
|D|14|
|E(local)|14|
|F(local)|2|
|H|1|


最重复、最直接的机制证据是robot任务中过量诅咒材料负重，以及丢弃后被控制器重新收取。A0的12个robot失败任务中，除war_banner外11个都出现明确腐蚀反馈；6个末步原生失败可被同状态原提案避免。这个结论的证据强于“全部因为规则没发现”或“都是LLM失误”。

F严格意义上的100步耗尽为0；只在repair_kit（2次wait）和sharpened_blade（5次wait）有明确局部停滞，不能称它们最后死于动作预算用完。G为0。制作批量/数量不一致有具体证据，但“请求2仅产1”并不自动造成任务失败；早期大量收取的主要损失是负重环境约束。闭包配方未制作不能忽略天然物品旁路。

不同方法的轨迹从早期就分叉，之后NPC、时间、资源和模型状态也不同。比较成功路线只用于提出解释；只有保存原生状态和随机数的单步回放允许宣称对应一步的局部反事实效应。未开发或验证任何Stage18算法。
