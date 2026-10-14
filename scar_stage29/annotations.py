"""Evidence-reviewed labels; hypotheses are not treated as measured stack effects."""
# Times below are absolute environment action numbers. 'resume_by' is a cited
# sufficient semantic example, not an exhaustive proof of the first return.
CASES_REVIEW={
'parent_a031':dict(plan='partial_unknown_acquisition',plan_steps=[32,33],condition_step=None,resume_by=None,
 evidence=[32,33,34,36,41,79],types=['B_candidate','D_constraint'],
 subgoals=['确定开锁工具的公开获取条件（当前未解）','持有工具后再评估原开门尝试是否仍必要'],
 note='明确要找/制作开锁工具，但检查工作台不提供方法。33 仍无工具重复 lockpick。34 拿 key、36 以 key 进入 armory，41 语义回到原知情者目标。原动作未恢复不等于不能回主任务，合法替代路径是反例。',
 residual='即使记住“需要开锁工具”，仍缺公开可执行的工具获取方法；强制保留此分支可能阻碍 key 替代方案。'),
'parent_a054':dict(plan='local_actionable',plan_steps=[55,56],condition_step=56,resume_by=58,
 evidence=[55,56,57,58,59],types=['D_constraint'],
 subgoals=['释放可供 iron_bar 使用的手部容量','容量满足后复核原资源需求及现有持有量'],
 note='55 丢 iron_bar、56 捡回，满足原动作成功但没有铁条净增量。58 目标及动作已回到武器材料采集，59 仍容量失败。存在资源配置/动作质量问题，不是没有回归。',
 residual='父子目标标题不能自动决定该保留照明还是哪种材料；本例“恢复成功”包含无净资源增长的搬运。'),
'parent_a060':dict(plan='local_actionable',plan_steps=[61,62,63],condition_step=61,resume_by=65,
 evidence=[61,62,63,65,66,71,75,79,84,92],types=['D_constraint'],
 subgoals=['可使用 workbench','wood_plank 制作及收取后重新评估武器材料目标'],
 note='61 到 workbench，62 制作、63 收取 wood_plank，65 回到武器制作意图。74/80 等目标已明确表达取木板→制作武器，仍反复受容量、照明及武器配方判断影响。',
 residual='层级意图实际已经出现；需要处理所选武器规则、当前资源与照明约束。'),
'parent_a113':dict(plan='local_actionable',plan_steps=[114,115,116],condition_step=115,resume_by=130,
 evidence=[114,115,116,119,126,128,130,131,132,136,151],types=['D_constraint'],
 subgoals=['腾出手部空间','能够取出 wooden_rod；用途仍须以公开规则核验'],
 note='114 腾手、115 取出木杆，116 错误装备，126 死亡。130–132 明确恢复收集制作材料，136 继续存储材料。不能把生存中断和目标改写当成从未回归；原基线也能取木杆并在 133 制作 torch。',
 residual='木杆可取出但不可装备，原计划包含错误的物品用途；已有子目标关系并不能纠正。'),
'parent_a136':dict(plan='local_actionable',plan_steps=[137,138,139,140,141],condition_step=138,resume_by=212,
 evidence=[137,138,139,140,141,148,149,167,212,218],types=['A_delay_candidate','D_constraint'],
 subgoals=['持有公开可识别的写字工具','核验写字动作的其他公开条件（本轮又遇持纸与手部空间约束）'],
 note='138 取得 pen，141 集齐 pen/paper 写字并明确提到原写字任务。较大的 equipment/capacity 父目标没有立即恢复：167 尝试收材料仍容量失败，至 212 有明确装备探索，218 再处理容量。存在延迟，不是全程遗忘；原始大目标与写 quiet 这个手段不能混为一层。',
 residual='提示只恢复工具条件，还要持纸、腾手、处理 torch 和生存。延迟也可能是合理优先级调整。'),
'parent_a235':dict(plan='unsupported_material_plan',plan_steps=[236,237,245,250],condition_step=None,resume_by=None,
 evidence=[236,237,241,243,245,248,250,265,296],types=['D_constraint'],
 subgoals=['从已公开配方恢复 torch 的必要材料条件','核验材料在当前状态是否可获得/可持有（未知位置保留未知）'],
 note='有“收材料→存储→制作”意图，且 245 战斗后明确恢复 torch 目标；问题是持续拿 cloth，而此前公开 torch 配方为 wooden_rod + mountain_sulfur。该旧配方没有进入 236 实际模型上下文。不能用这个例子排除信息/记忆利用问题。',
 residual='若纸面 Stack 直接补回旧配方，收益就混入信息补充，而非只改变层级。'),
'parent_a270':dict(plan='local_actionable',plan_steps=[271,272,273],condition_step=273,resume_by=274,
 evidence=[271,272,273,274,281,282,286,288,290,291],types=['D_constraint'],
 subgoals=['查明 small_satchel_0 当前占用','释放容器容量后完成 cloth 存储'],
 note='查看→丢弃→存储的恢复链完整；274 明确回到装备目标。后续缺材料、缺写字工具、未持纸与非法容器嵌套是真实新约束，不是原任务没回归。',
 residual='恢复一次容量不能保证后续嵌套前置条件管理正确。'),
'oracle032_a256':dict(plan='partial_unknown_acquisition',plan_steps=[257,258,262],condition_step=None,resume_by=None,
 evidence=[257,258,262,265,269,274,275,281,294,299],types=['B_candidate','C_transient_candidate','D_constraint'],
 subgoals=['确定 furnace 的公开可达来源或制作条件（当前无确定方法）','如探索遇已公开阻碍，明确是恢复照明还是更换制作方案'],
 note='257 找 furnace、262 转照明；265/269 制成 thread，可能满足更大的替代制作方向。274 否认黑暗证据，但实际 current_goal.evidence 仍有 verified=true 的黑暗引文；275 立即又恢复照明目标。是一次证据利用/有效性误判，不能称为持续遗忘炉子导致全部失败。',
 residual='炉子来源未解，cloth_roll 与照明关系缺公开支持；保留父目标不能凭空提供这两条知识。'),
'oracle037_a122':dict(plan='local_actionable',plan_steps=[123,124,127,138,139,143,146],condition_step=123,resume_by=None,
 evidence=[123,124,127,128,129,130,131,137,138,139,143,146,147,148,152,162,169,174,180,220],types=['C_interruption_candidate','D_constraint'],
 subgoals=['具备 workbench 条件','核验公开 lockpick 材料是否齐全','在照明与容量约束下保留已获得的必要材料'],
 note='123 设施已满足，124/127/143/146 连续给出材料→回工作台的计划，并正确记得 rust_scrap/thread 已存包。147 仍保持 lockpick 目标，却在只持 torch 时误说手满并丢照明。162 后转生存，169 死亡；未恢复 lockpick 可以是中断/优先级问题，不能孤立归因为目标栈缺失。',
 residual='原生同状态探针验证 147 可直接 pick up iron_bar 同时保留 torch。这个局部状态/动作错误发生在目标与计划仍明确时。'),
'oracle079_a165':dict(plan='partial_dependencies',plan_steps=[166,170,171,173],condition_step=None,resume_by=None,
 evidence=[166,167,170,171,173,174,175,176,177,187,188,203,271],types=['B_candidate','C_interruption_candidate','D_constraint'],
 subgoals=['保留已公开的 star_metal_sword 必要组件关系','分辨已持有组件与尚未知的组件制作/获取条件','缺少来源或规则的组件保持未知，不能把普通矿石当成已证实替代'],
 note='166 已列出缺失组件，170 先腾手取灯；173 在恢复目标仍 ACTIVE 时称 goblin_eye 不需要而丢弃，与 164 已公开配方相反。177 战斗优先、187 死亡、188 重建库存。既有组件规划也有资源语义和地点访问错误，不是纯目标标题丢失。',
 residual='精确组件配方在 166 上下文可见，到 173 已不在上下文；保留 Stack 若不保存资源事实，未必避免丢必要材料。')}

def write_annotations():
    import json
    from .common import RESULTS,write,data,CASES,offline
    offline()
    output=[]
    for ident,note in CASES_REVIEW.items():
        s,rr,qq,path,lines=data(ident,'OracleRecovery');by={r['step']:r for r in rr}
        evidence=[]
        for step in note['evidence']:
            r=by[step];p=r['decision']['attempts'][-1]['proposal']
            evidence.append(dict(step=step,source=path,line=lines[step],action=r['action'],reasoning=p['reasoning'],
                observation=r['observation'],feedback=r['feedback'],goal=r['control_after']['goal'],request_ids=[q['request_id'] for q in qq if q['step']==step]))
        output.append(dict(id=ident,reviewer='assistant review of full saved timeline plus cited raw decision/context; not independent blind human review',
            original_goal=s['current_goal'],recovery_objective=CASES[ident],phase0_adopted=True,phase1_understood=True,
            **{k:v for k,v in note.items() if k!='evidence'},evidence_steps=note['evidence'],evidence=evidence,stack_effect_causally_tested=False))
    write(RESULTS/'lifecycle_annotations.json',output)

if __name__=='__main__':write_annotations()
