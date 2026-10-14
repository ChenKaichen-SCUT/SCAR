"""Assistant-reviewed public evidence; no hidden rules and no LLM evaluator."""
from .common import *
from .analyze import data,accepted
from scar_stage29.annotations import CASES_REVIEW as BASELINE_REVIEW

NOTES={
 'parent_a031':dict(condition_step=None,resume_by=None,alternate_parent_progress_by=35,
    evidence_steps=[32,33,34,35,36,38,41,45,46,47],category='C：未恢复开锁工具；合法替代路径取得局部主线进展',
    subgoal_assessment='未证实开锁工具可获得性；32/33 查看两个容器为空，34 拿 key、35 进入 library 是替代方法，不是 lockpick 恢复。',
    maintenance_assessment='32–35 保持原知情者目标，35 环境明确 Stage completed。无需先完成选错的开锁工具分支；不能把原动作未成功当成父目标被遗忘。',
    note='B 没有机械采纳 level 1 标题，而是保持 level 0，并在理由中识别缺工具。A 也可通过 key 替代；最终主线均 1。后续 41 在错误地点找 torch、46 容量拒绝、47 丢掉 wood_log 仍体现执行约束。'),
 'parent_a054':dict(condition_step=59,resume_by=59,alternate_parent_progress_by=None,
    evidence_steps=[55,56,57,58,59,60,61,90,120,126],category='B：成功重试但无净铁条增量；无长期收益',
    subgoal_assessment='持有和容量已由初始 observation 公开；不计新增知识。58 丢 iron_bar 后 59 重新捡回，证明动作可行，但并未多得一根铁条。',
    maintenance_assessment='55–60 仍保持恢复目标，59 理由明确联系制作武器；61 转入真实战斗。不能称从未续接父目标。',
    note='A 55 丢铁、56 捡回；B 55 丢 torch 导致黑暗、56 捡回、57 试装备 torch 被拒，再丢铁捡铁。层级没有避免照明和物品用途错误，B 成功重试还晚了 3 步。'),
 'parent_a060':dict(condition_step=62,resume_by=66,alternate_parent_progress_by=None,
    evidence_steps=[61,62,63,64,66,67,68,72,75,76,77,78,79,80,82,117],category='B：工作台与制作恢复，仍受容量/照明/执行影响',
    subgoal_assessment='62 observation 公开可用 workbench，63 制作、64 收取 wood_plank，临时条件和产出均达成。',
    maintenance_assessment='66 明确转 wooden_dagger 并尝试拿 thread，75/82 进一步表达材料子目标；并非没有分解或没有回到武器方向。',
    note='A 61/62/63 完成相同恢复链，B 先 defend，整体晚 1 步；67 丢 torch、72/77 存 torch 导致黑暗，后续 82 又因原材料不足拒绝。层级意图存在并不能保证照明/材料状态执行正确。'),
 'parent_a113':dict(condition_step=115,resume_by=118,alternate_parent_progress_by=None,
    evidence_steps=[114,115,116,118,119,120,129,130,132,133,135],category='B：局部取物成功并继续制作，长期无改善',
    subgoal_assessment='114 存 cloth 腾手、115 取 wooden_rod；初始手部占用已知，不应重复算为新知识。',
    maintenance_assessment='116 错试装备木杆后，118 已制作 thread 来改善装备，实际存在较大目标续接。',
    note='A 丢 cloth，B 存 cloth，两者均在 115 成功取出木杆、116 都错误装备。B 118 制成 2 thread 是有价值的局部行为，随后 130 容器嵌套、133 容量错误、135 死亡；不是层级单独解决全程。'),
 'parent_a136':dict(condition_step=140,resume_by=156,alternate_parent_progress_by=None,
    evidence_steps=[137,138,139,140,141,142,143,144,145,152,156,162,163,168],category='B：写字恢复；较大容量目标有续接，但没有主线收益',
    subgoal_assessment='pen 可见性初始已知；137 满手拿 pen 失败、138 将持有 cloth 错当包内丢弃，140 才获得 pen；141 再遇纸未持有，144 才成功写 quiet。',
    maintenance_assessment='144 写 quiet 与最外层“改善装备和容量”不同；152 死亡后 156 实际装备 bag 腾手并明确改善容量。语义续接发生，不等于控制器保存了父子链接。',
    note='A 138 持 pen、141 写成；B 分别晚 2/3 步。B 156 比 A 的已引用 212 证据更早出现容量方向，但这只是证据上界的差别，不是两条轨迹的精确最早回归差；死亡和模型分叉混杂。'),
 'parent_a235':dict(condition_step=None,resume_by=None,alternate_parent_progress_by=288,
    evidence_steps=[236,237,243,247,248,249,252,254,257,266,288,292,293],category='C：未恢复 torch 材料；知识与执行缺口仍在',
    subgoal_assessment='236 明确提到 goal hierarchy，却猜 cloth/goblin_eye 为 torch 材料；247 的 workbench 检查没有补全配方。两个 level 2 条件没有被证实全部完成。',
    maintenance_assessment='目标持续到 246；247 改为查配方，249 转 star_metal_sword；288 仍找光源。不能仅因换目标就认定遗忘；保持目标也没有纠正材料猜测。',
    note='A/B 首两动作相同：拿 cloth、存满 satchel 被拒；B 没有因层级变得知道正确配方。历史 torch 配方本轮未重新注入，信息可见性仍是重要限制；不能把受限 Oracle 无增益解释成信息与状态机制无用。'),
 'parent_a270':dict(condition_step=275,resume_by=None,alternate_parent_progress_by=274,condition_probe=True,
    evidence_steps=[271,272,273,274,275,278,281,284,289,291,297],category='B：容量条件恢复但未执行存储；状态理解与目标管理交织',
    subgoal_assessment='271–273 连丢包内 cloth，原生第5步探针核验 store 可执行；没有正式成功重试，不能把 0 次成功重试当作容量始终未恢复。',
    maintenance_assessment='274 明确说要回到 broader objective 并探索装备；同时错误说 satchel 仍满。旧缺口证据未更新与当前状态判断错误同时出现，未隔离因果。',
    note='A 271 查看、272 丢纸、273 存 cloth；B 三次丢 cloth，271/272 理由却声称丢的是手中 cloth，274 认为容量无进展。B 已有父目标续接，却未完成原存储操作，并消耗更多既有材料。'),
 'oracle032_a256':dict(condition_step=None,resume_by=None,alternate_parent_progress_by=265,
    evidence_steps=[257,258,259,260,261,262,264,265,266,267,268,269,275,285],category='C：未找到 furnace；可有替代制作但无原恢复',
    subgoal_assessment='没有 furnace 来源或可用性证据；257 进暗 library，258 wait，261 workbench 无配方。未知依赖没有被层级标题解决。',
    maintenance_assessment='262 转真实战斗，264 处理照明/通路；265 制成 thread 可对应原“制作可用物”方向，故不等于完全没有父目标能力。',
    note='A 257 也进暗 library；B 258 wait 而 A 回 hall。A/B 都在 265 制 thread。B 随后 267 错试 disassemble rust_scrap，多次材料不足制作；没有足够证据把这些问题归为层级缺失。'),
 'oracle037_a122':dict(condition_step=123,resume_by=None,alternate_parent_progress_by=None,
    evidence_steps=[123,124,125,126,127,128,129,130,131,132,135,137,138,141],category='B：设施条件达成；下一层材料/照明/战斗阻断',
    subgoal_assessment='123 到有 workbench 的 hall，124 制作转为材料不足。实际已满足本检查点临时设施条件，但 lockpick 从未制成。',
    maintenance_assessment='125–131 理由持续表达拿材料再回 workbench，层级计划并非缺席；127 仍主动丢 torch 导致黑暗，132 战斗、137 死亡。',
    note='A 也在 123 满足设施，并保持材料→返回的计划；B 126 满手拿 rust_scrap、127 丢照明、137 死亡。相比 A 的 147 丢 torch/169 死亡，时序不同，但都显示目标与行动计划在场时仍会出执行问题。'),
 'oracle079_a165':dict(condition_step=None,resume_by=None,alternate_parent_progress_by=284,
    evidence_steps=[166,167,168,169,170,171,172,173,174,175,176,179,180,181,182,267,284,291],category='C：必要材料不齐；部分知识保留改善不足以完成恢复',
    subgoal_assessment='精确 sword 配方在首次原输入已公开。166/173 明确列组件，但全部组件的获取条件未知；167 将 cloth 与 cloth_strap 混用，不能算材料齐备。',
    maintenance_assessment='173 仍记得 goblin_eye 是组件，比 A 同步丢掉必要 goblin_eye 的行为好；然而 B 在只持 torch 时说手满并丢 torch，174 退 hall、175 找不存在的 torch。层级/材料名仍在，状态与可行性错误也在。',
    note='166 将 goblin_eye 存包，173 保留组件关系，是有利细节，不能选择性忽略。但没有制造 sword；267 死亡，284 转探索装备。该有利细节不足以证明层级有效，也不能假定是严格因果效果。')
}

def main():
    offline();output=[];probes=rows(RESULTS/'native_feasibility_probes.jsonl.gz')
    for ident in CASES:
        n=NOTES[ident];base=BASELINE_REVIEW[ident]
        s,a,qa,ap,al=data(ident,'OriginalRecovery');_,b,qb,bp,bl=data(ident,'OracleGoalStack')
        amap={r['step']:r for r in a};bmap={r['step']:r for r in b}
        divergence=next((r['step'] for r in b if r['step'] in amap and r['action']!=amap[r['step']]['action']),None)
        result=dict(id=ident,**n,baseline_condition_step=base['condition_step'],baseline_resume_by=base['resume_by'],
            baseline_evidence_steps=base['evidence'],first_action_divergence_step=divergence,
            first_a_action=amap[divergence]['action'] if divergence else None,first_b_action=bmap[divergence]['action'] if divergence else None,
            reviewer='assistant semantic review of paired early windows, full goal/action timelines and cited later evidence; not independent blinded human review',
            no_hidden_state_used_for_semantic_labels=True,evidence={},baseline_evidence={},condition_probe_receipt=None)
        for which,steps,by,path,lines,qq in [('evidence',n['evidence_steps'],bmap,bp,bl,qb),('baseline_evidence',base['evidence'],amap,ap,al,qa)]:
            for step in steps:
                r=by[step];result[which][str(step)]=dict(source=str(path.relative_to(ROOT)),line=lines[step],step=step,
                    action=r['action'],proposal=r['decision']['attempts'][-1]['proposal'],observation=r['observation'],feedback=r['feedback'],
                    control_goal=r['control_after']['goal'],scores=r['scores'],request_ids=[q['request_id'] for q in qq if q['step']==step])
        if n.get('condition_probe'):
            probe=next(p for p in probes if p['id']==ident and p['variant']=='OracleGoalStack' and p['absolute_step']==n['condition_step'])
            assert probe['accepted'];result['condition_probe_receipt']=probe
        if n['resume_by'] is not None:
            success=[r['step'] for r in b if r['action']==s['candidate_action'] and accepted(r)]
            assert success and n['resume_by']>=success[0] and n['resume_by'] in n['evidence_steps']
        output.append(result)
    write(RESULTS/'semantic_review.json',output)
    write(RESULTS/'semantic_summary.json',dict(pairs=10,condition_demonstrated_A=sum(x['baseline_condition_step'] is not None for x in output),
        condition_demonstrated_B=sum(x['condition_step'] is not None for x in output),
        restored_action_with_parent_semantic_continuation_B=sum(x['resume_by'] is not None for x in output),
        alternative_parent_progress_B={x['id']:x['alternate_parent_progress_by'] for x in output if x['alternate_parent_progress_by'] is not None},
        causal_hierarchy_effect_proven=False,new_model_calls=0))
    print(json.dumps(read(RESULTS/'semantic_summary.json')),flush=True)

if __name__=='__main__':main()
