"""Transparent assistant evidence review of all ten paired 20-action windows."""
from .common import *

NOTES={
 'parent_a031':dict(steps=[32,33,34,36,41],finding='提示被采纳；32 检查工作台，33 仍在无开锁工具时 lockpick；34 拿 key、36 用 key 进入 armory，41 改回寻找知情者。替代开门成功不等于获得 lockpick；原动作不是更大目标唯一必要路径。',original='Original 32 同样重复 lockpick，后续用 key 进入 library 并在 39 获得主线奖励。'),
 'parent_a054':dict(steps=[55,56,57,58,59],finding='55 丢下已有 iron_bar，56 捡回，满足原动作成功指标但没有增加铁条净持有量；57 再丢、58 捡木头、59 又因容量拒绝。不能把这个指标命中称为有效资源积累。',original='Original 55 丢 torch 导致黑暗、56 捡回；58 也丢 iron_bar，但之后改捡 wood_log，20 步内没有再捡 iron_bar。'),
 'parent_a060':dict(steps=[61,62,63,65,66,71,75,79],finding='61 到 hall 看见 workbench，62 制成 wood_plank，63 收取；65 转向武器制作。随后照明与手部容量冲突，66 丢 torch 导致黑暗，71 丢木板，75 捡木板容量失败，79 再捡回。局部恢复与后续资源执行困难并存。',original='Original 61 明确知道缺 workbench，却在已持 torch+wood_log 时说自己有手部空间并捡 stone，遭容量拒绝，随后进入防御循环。'),
 'parent_a113':dict(steps=[114,115,116,119,128],finding='114 丢 cloth，115 取出木杆，116 尝试装备却被告知不可装备；119 丢木杆。更快取得物品未修复物品用途判断。',original='Original 121 也能取出、122 同样错误装备；但原轨迹 133 已成功制作 torch，不能只按更快取木杆宣布 Oracle 整体更好。'),
 'parent_a136':dict(steps=[137,138,139,140,141,148,149],finding='137 丢 cloth、138 拿 pen；139 丢 torch、140 拿 paper，141 写 quiet 成功。148 拿 torch 又遇容量拒绝，149 丢写好的纸时出现 hush 的公开效果。恢复后仍需处理照明和生存约束。',original='Original 137 承认缺 pen，但优先逃离受攻击地点；20 步内未完成写字。优先生存不能仅凭未恢复写字判为不合理。'),
 'parent_a235':dict(steps=[236,237,241,243,245],finding='236 拿 cloth，237 存储容量失败，241 错误装备 cloth，243 转战斗；245 说收集 torch 材料，仍未制作 torch。提示本身只给缺材料，没有给配方；材料选择与容量执行并未因此解决。',original='Original 236 识别缺材料并去 library 找配方或现成光源，是已存在的恢复/替代意图。'),
 'parent_a270':dict(steps=[271,272,273,274,281,282,286,288],finding='271 查看容量，272 丢弃 paper_7，273 存 cloth 成功，274 回到装备探索。随后 281 缺材料、282 缺写字工具、286 未持纸、288 非法容器嵌套，形成新的前置条件链。',original='Original 271 丢 cloth 释放手部空间，没有在 20 步内恢复该存储动作。'),
 'oracle032_a256':dict(steps=[257,258,260,265,269,274,275],finding='257 探 library、258 因黑暗返回，未找到 furnace；260 尝试装备未持有的包；265/269 成功制作 thread，属于替代制作而非恢复 glass_shard。不能把未找到 furnace 等同没有任何有用行为。',original='Original 257 明确选择不需要 furnace 的其他配方，符合更大的 craft usable item 目标。强制关注原失败动作的前置条件不一定是最优子目标。'),
 'oracle037_a122':dict(steps=[123,124,127,128,129,130,131,137,138,139],finding='123 到达已有 workbench 的 hall，设施缺口已解决；随后转向材料：127 容量拒绝、128 存 torch 后黑暗、129 取回，130 丢 iron_bar 捡 rust_scrap，137 拿 thread 又容量拒绝。已形成多步计划但约束交互使其反复。',original='Original 125 也到 hall，126 重试 craft lockpick 从缺设施转为缺材料，说明原 Agent 也会解决第一层前置条件。'),
 'oracle079_a165':dict(steps=[166,167,168,170,173,174,175,176,177],finding='166 列出缺少的成品组件并拿 cloth；167 声称有空手却容量拒绝，168 进入黑暗，170 存 cloth，173 丢 goblin_eye，174 拿 iron_ore，175 容量拒绝，176 尝试使用当前位置不可访问的包，177 转战斗。目标采纳未保证世界状态和材料链一致。',original='Original 首步也拿 cloth，说明最初材料恢复方向并非提示独有。')}

def main():
    offline();reviews=[]
    for ident,s in selected().items():
        rr=rows(RESULTS/'runs'/ident/'OracleRecovery'/'trajectory.jsonl.gz');first=rr[0]
        proposal=first['decision']['attempts'][-1]['proposal'];goal=first['control_after']['goal']['goal_description']
        assert proposal['goal_description']==goal
        reviews.append(dict(id=ident,reviewer='assistant evidence review; not independent human adjudication',
            scope='Both actual first 20-action windows; all selected pairs, no outcome exclusions',
            initial_recovery_goal_adopted=True,model_goal=proposal['goal_description'],controller_goal=goal,
            initial_action=first['action'],initial_reasoning=proposal['reasoning'],
            oracle_evidence_steps=NOTES[ident]['steps'],oracle_finding=NOTES[ident]['finding'],original_comparison=NOTES[ident]['original'],
            original_evidence=s['source_trajectory'],oracle_evidence=f'results/stage28/runs/{ident}/OracleRecovery/trajectory.jsonl.gz'))
    write(RESULTS/'selected_pair_semantic_review.json',reviews)
    print(json.dumps(dict(reviewed_pairs=len(reviews),adopted=sum(r['initial_recovery_goal_adopted'] for r in reviews))),flush=True)

if __name__=='__main__':main()
