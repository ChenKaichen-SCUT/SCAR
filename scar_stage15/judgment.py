"""Batch-specific research interpretation; does not alter any frozen policy."""
from pathlib import Path
from scar_stage14.common import load
from scar.io import atomic_json
ROOT=Path('results/stage15');OUT=Path('reports/stage15')

TEXT='''# 研究判断：五个问题

**RQ1：解析修复可靠，但本批没有提高最终成功数，也没有普遍减少重复检查。** P1与新跑P0均为4/10；P1结束时公开名称关系243/243正确登记、公开数量221/221正确记录，P0分别为255/276和16/229。模型事实摘要明确展示的数量从0/1820个机会变为1497/1497；P0的STM原文和效果样本仍可能提供数量信息，因此“摘要未明确记录”不等于模型从未看到。制作材料不足拒绝由14次降至6次、全部动作326降至311，但重复无新增信息检查反从6升至9。数量知识正确并未解决全局发现与完成问题；不能宣称普遍减少无效探索。

**RQ2：数量增强没有成功率增益；收尾有一个有限的正例。** P2仍4/10，材料不足拒绝5次，局部批量被支配的次数2次，高于P1的1次。hunter_gauntlets第29步请求3份sinew_cord消耗2份salvage_cloth，而同状态请求4份也只消耗2份；局部更优批量仍被遗漏。请求数量提高不保证实际数量提高：padded_tunic中请求4份实际只产出2份。

P3为5/10，仅chain_net相对P1新增成功，未丢失P1的四个成功family。P3在第37步把原控制器的`store 1 iron_bar inventory`改为`store 2 iron_bar inventory`，第38步制作，第39步真实取得第二份chain_net。公开语义是先处理手上那份，再收地面那份；这是真实少一次转移动作的收尾。冻结前同一历史物理状态的原生分支也验证P1需4步、P3/P6需3步完成。正式P1在第40步才制作出地面chain_net，尚未取得，严格计失败。不过P3与P1更早的模型提案已经不同，这个配对全局差异不能全归因于最后一次改写。hellfire_bomb与hunter_gauntlets在七配置里都没有最终成功，故不能说已解决“知识已知但40步未完成”的一般问题。

**RQ3：没有观察到关键保护的整局收益，也没有证据表明本批复制了S2的严重囤积风险。** P4仍4/10，只有两次保护收取：padded_tunic第4步取得sinew_cord、hunter_gauntlets第20步取得iron_nugget。这两个动作当步都没有损血；P4累计损血189，P1为228，但不同采样轨迹不支持将该差额因果归给保护。已公开确认关键材料的环境损失均为1单位，未减少。P6也有两次保护，仍没有新增成功。对未公开的blade_blank必要依赖没有提前施加隐藏保护规则；对正在损血的库存也没有为了保护强制继续囤积。当前只证明动作可取得局部材料，不能证明避免了关键损失或额外步数值得。

**RQ4：续行的局部作用超出单个helm检查点，但没有整局收益。** P5在3个family触发3段、7个动作，完成2段生产加检查。hellfire_bomb的iron_bar续行真实产出1份，并于第20步补齐最终必要配方名称；forged_blade_blank的siege_key续行产出2份并检查，但没有新配方关系。这两局最终仍失败。fiend_helm的续行完成两次材料收取后遇工作台拒绝，按本轮规定首次失败即停；新增数量披露不等于完成stitched_panel，更不等于完成helm。P6共4段、8个动作、2段完成，其中hunter_gauntlets在最后一步进入一段未完成的准备，达到40步即由运行器结束；该步未节省最终预算，保留其成本。每局均不超过7个续行动作。这里只支持有界工程修复的局部作用，不支持新算法或泛化最优额度。

**RQ5：P6保留本批P0/P1的四个成功family，但没有提高真实成功数。** P6为4/10，全部动作310，材料不足拒绝4次；不能把这些局部改善说成任务成功率提升。P3的chain_net成功在P6没有重现。对P6该family逐步核查发现四个模块均未改变同状态P1最终动作（收尾条件没有触发），没有证据将失败称为模块互相覆盖造成的冲突。第35步S1批量逻辑选择的iron_bar制作被拒绝，后续只有在第38步才完成中间制作，40步内未到最终收取；不同提案和前期资源/健康状态已使它与P3路径分离。保留组合失败，不事后重排模块。独立组件配置有利于隔离开关，但单次随机闭环仍不能把每个差异独立因果归因。

结论是：解析修复应作为工程正确性修复保留；近完成收尾值得后续独立重复验证；数量、保护、续行及四项组合均未在本批建立最终成功率增益。10个长期开发family上的一次配对，不足以宣称显著优越或独立泛化。当前结果不支持增加新的未知规则规划复杂度。若以后验证稳定性，应另行预注册整批独立重复，不选择性重跑本批失败局。
'''


def main():
    a=load(ROOT/'aggregate_metrics.json');assert {m:x['R40'] for m,x in a.items()}=={'P0':4,'P1':4,'P2':4,'P3':5,'P4':4,'P5':4,'P6':4}
    atomic_json(ROOT/'research_judgment.json',{'successes':{m:x['R40'] for m,x in a.items()},
      'RQ1':'online knowledge correctness improved; no R40 gain; repeat inspections not uniformly reduced',
      'RQ2':'P2 no R40 gain; P3 one chain_net win with local one-step transfer evidence, not fully causal task attribution',
      'RQ3':'two conservative P4 acquisitions, no critical-loss or R40 reduction; immediate health cost0',
      'RQ4':'local production/inspection beyond helm, no full-task gain; no algorithmic novelty claim',
      'RQ5':'P6 retains four baseline successes but adds none; chain_net has no module override conflict evidence',
      'selective_paid_reruns':0,'proposed_followup':'separately preregistered full repeated batch, not performed'})
    (OUT/'研究判断.md').write_text(TEXT)
    p=OUT/'实验总报告.md';s=p.read_text();s=s.split('## 必答问题')[0]+'## 必答问题\n\n'+TEXT.split('\n',1)[1]
    s+='\n本批2198个真实环境动作对应2207次请求；9次响应未通过原有格式/解析校验后按继承的供应商重试协议重试，所有失败响应均计费留档。没有在多个合法回答中挑选较好回答，也没有重跑任何整局。服务端全部2198步两遍原生核验、本地2198步独立核验一致。\n'
    p.write_text(s)
    p=OUT/'目标收尾与材料保护.md';s=p.read_text();s+='\n## 收尾的实际一步收益\n\n冻结前chain_net第36号状态：P1为store1、store1、craft、pickup四步；P3/P6为store2、craft、pickup三步，四次原生重放一致。正式P3唯一改变同状态P1动作的收尾发生在第37步，最终第39步取得目标。不能将提前的全部差额归因于该一步，较早的模型提案亦存在差异。P6的chain_net并无模块对P1动作的实际改写，故其失败不能当作已证实的模块冲突。\n';p.write_text(s)
    print('Five bounded research answers written.')

if __name__=='__main__':main()
