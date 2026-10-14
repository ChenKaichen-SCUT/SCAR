# oracle032_a256 / Original

原目标：Craft a usable item from available materials at the workbench

恢复条件：Have access to a furnace for crafting glass_shard before continuing the original objective.

原失败动作：`craft 1 glass_shard`。以下为全部 44 个动作；完整理由/状态/请求见逐动作数据库及原轨迹。

|动作号|动作|公开结果|当前目标|状态|主线增量|原目标在归档/上下文（字面）|
|---|---|---|---|---|---|---|
|257|inspect cloth|I inspected cloth: A folded piece of cloth. / It can be used to craft: paper (made of cloth), brine_concentrate (made of sea_salt_crystal, cloth), thread (made of cloth), bandage (made of cloth, meadow_herb, crimson_lichen), padded_|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|258|craft 1 thread|I successfully crafted 1 thread. It is now on the ground.|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|259|pick up thread|Cannot pick up thread, not enough space in hand.|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|260|store 1 quartz_chunk small_bag_0|I stored 1 quartz_chunk in small_bag_0.|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|261|pick up thread|I picked up thread. / I have acquired a new item: thread. It can be used to craft: book (5 paper, 1 thread), wooden_sword (1 wood_plank, 1 wood_strip, 1 thread), cloth_tunic (1 padded_lining, 1 thread), lockpick (1 rust_scrap, 1 iro|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|262|craft 1 thread|Cannot craft a single thread. Do not have sufficient amount of necessary ingredients.|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|263|store 1 rust_scrap small_bag_0|Cannot store any number of rust_scrap, not enough space in small_bag_0.|Craft a usable item from available materials at the workbench|ACTIVE|0|False/True|
|264|drop rust_scrap|I dropped rust_scrap.|Craft a usable item from available materials at the workbench|SUSPICIOUS|0|False/True|
|265|pick up cloth|I picked up cloth.|Craft a usable item from available materials at the workbench|SUSPICIOUS|0|False/True|
|266|inspect workbench|I inspected workbench: A sturdy crafting bench where rough materials become real tools. / It can be used to craft: None. / It has nothing written on it.|Find a craftable item given current materials|ACTIVE|0|True/True|
|267|drop cloth|I dropped cloth.|Find a craftable item given current materials|ACTIVE|0|True/False|
|268|enter library|I entered library. / It is too dark to see anything here.|Find a craftable item given current materials|ACTIVE|0|True/False|
|269|enter hall|I entered hall. / An enemy peak_vulture_4 arrives from library and prowls into the area.|Find a craftable item given current materials|ACTIVE|0|True/False|
|270|defend|I am defending.|Find a craftable item given current materials|ACTIVE|0|True/False|
|271|enter armory|Cannot enter armory, the door is locked.|Find a craftable item given current materials|SUSPICIOUS|0|True/False|
|272|drop thread|I dropped thread.|Find a craftable item given current materials|SUSPICIOUS|0|True/False|
|273|pick up cloth|I picked up cloth.|Find a craftable item given current materials|SUSPICIOUS|0|True/False|
|274|inspect cloth|I inspected cloth: A folded piece of cloth. / It can be used to craft: paper (made of cloth), brine_concentrate (made of sea_salt_crystal, cloth), thread (made of cloth), bandage (made of cloth, meadow_herb, crimson_lichen), padded_|Find a craftable item given current materials|SUSPICIOUS|0|True/False|
|275|craft 1 thread|I successfully crafted 1 thread. It is now on the ground.|Craft thread from cloth to enable further crafting|ACTIVE|0|True/False|
|276|pick up thread|I picked up thread.|Craft thread from cloth to enable further crafting|ACTIVE|0|True/False|
|277|pick up thread|I picked up thread.|Craft thread from cloth to enable further crafting|ACTIVE|0|True/False|
|278|craft 1 cloth_roll|Cannot craft a single cloth_roll. Do not have sufficient amount of necessary ingredients.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|279|pick up cloth|Cannot pick up cloth, not enough space in hand.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|280|store 1 thread small_bag_0|Cannot store any number of thread, not enough space in small_bag_0.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|281|drop thread|I dropped thread.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|282|pick up cloth|I picked up cloth. / Sense of peacefulness sneaks in. Tempers settle, and hostility loosens its grip.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|283|craft 1 cloth_roll|Cannot craft a single cloth_roll. Do not have sufficient amount of necessary ingredients.|Craft cloth_roll using cloth and thread|ACTIVE|0|True/False|
|284|pick up cloth|Cannot pick up cloth, not enough space in hand.|Craft cloth_roll using cloth and thread|SUSPICIOUS|0|True/False|
|285|discard 1 thread hall|Cannot find hall to discard thread.|Free hand space to enable picking up more crafting materials|ACTIVE|0|True/False|
|286|drop thread|I dropped thread.|Free hand space to enable picking up more crafting materials|ACTIVE|0|True/False|
|287|pick up cloth|I picked up cloth.|Free hand space to enable picking up more crafting materials|ACTIVE|0|True/False|
|288|craft 1 cloth_roll|Cannot craft a single cloth_roll. Do not have sufficient amount of necessary ingredients.|Craft cloth_roll using available cloth|ACTIVE|0|True/False|
|289|pick up thread|Cannot pick up thread, not enough space in hand.|Craft cloth_roll using available cloth|ACTIVE|0|True/False|
|290|store 2 cloth small_bag_0|Cannot store any number of cloth, not enough space in small_bag_0. / I was attacked by peak_vulture_4 and lost 9 HP.|Craft cloth_roll using available cloth|ACTIVE|0|True/False|
|291|attack peak_vulture_4|I attacked peak_vulture_4 for 10 damage. peak_vulture_4 has 26 HP remaining. / peak_vulture_4 has engaged in combat. / peak_vulture_4 is attacking. / I was attacked by peak_vulture_4 and lost 19 HP.|Craft cloth_roll using available cloth|ACTIVE|0|True/False|
|292|enter armory|Cannot enter armory. peak_vulture_4 has blocked the way out. / peak_vulture_4 is waiting.|Survive the peak_vulture_4 encounter by retreating|ACTIVE|0|True/False|
|293|defend|I am defending. My stamina is now at 100%. / peak_vulture_4 is attacking. / I was attacked by peak_vulture_4 and lost 1 HP.|Survive the peak_vulture_4 encounter by retreating|ACTIVE|0|True/False|
|294|defend|I am defending. My stamina is now at 100%. / peak_vulture_4 is defending.|Survive the peak_vulture_4 encounter by retreating|ACTIVE|0|True/False|
|295|attack peak_vulture_4|I attacked peak_vulture_4 for 10 damage. peak_vulture_4 has 16 HP remaining. / peak_vulture_4 is attacking. / I was attacked by peak_vulture_4 and lost 19 HP. / I have been defeated by peak_vulture_4! / I have died. / I revived at the start|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
|296|enter library|I entered library. / It is too dark to see anything here.|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
|297|wait|I waited for a while. / It is too dark to see anything here.|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
|298|inspect library|Cannot inspect library, the object not found in hand, arms, inventory, or the current area. / It is too dark to see anything here.|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
|299|enter hall|I entered hall.|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
|300|defend|I am defending.|Survive the peak_vulture_4 encounter by defeating it|ACTIVE|0|True/False|
