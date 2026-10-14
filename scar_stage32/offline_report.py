"""Report the complete fixed-candidate cohort before opening the online phase."""
from collections import Counter
from scar_stage31.report import save,table
from .common import *

def main():
    offline();s=read(RESULTS/'offline_summary.json');assert s['complete'];c=s['counts'];data=read(RESULTS/'offline_comparison.json')
    grouped=[]
    for kind in ['rejected','condition_loss','terminal']:
        rr=[x for x in data if x['kind']==kind]
        grouped.append([kind,len(rr),sum(x['warning'] for x in rr),sum(x['changed'] for x in rr),sum(x['final_accepted'] for x in rr),sum(x['final_wait'] for x in rr)])
    detailed=table(['样本','类别','原候选','最终动作','风险','改变','原生接受 原/终','可见 原/终','后续原取物接受 原/终'],[
        [x['id'],x['kind'],x['candidate'],x['final_action'],x['risk'],x['changed'],f"{x['candidate_accepted']}/{x['final_accepted']}",
         f"{x['candidate_visible']}/{x['final_visible']}",f"{x['candidate_followup_accepted']}/{x['final_followup_accepted']}"] for x in data])
    save(REPORTS/'离线验证报告.md',f'''# Stage32 离线固定候选验证

完整 77 样本完成，70 个原拒绝动作中有 **{c['rejected_to_accepted']} 个**最终选择得到原生接受；这不等于主线恢复。五个 REC 终止状态合法候选中，最终原生接受 **{c['legal_terminal_final_accepted']}/5**，保持原动作 **{c['legal_terminal_same_action']}/5**。两个原条件损失动作中，最终接受且保持可见 **{c['loss_to_accepted_visible']}/2**。

## 样本及边界

三个 Stage31 REC 母轨迹，75 个物理状态、77 个固定候选，不是 77 个独立任务。全部 70 次公开拒绝、2 次实际移出物品后变暗及5个去重合法终止候选均纳入；一个原生语法非法的终止提案只作为来源记录，详见 preparation.json。候选来自旧响应；本次每个样本只调用一次预测和一次最终选择。候选后的真实反馈和原生诊断后续动作没有进入模型输入。

{table(['类型','样本','warning','动作改变','最终原生接受','最终wait'],grouped)}

warning 共 {c['warnings']}，warning 后改变 {c['warning_changed']}/{c['warnings']}；全部改变 {c['changed']}/77。预测格式无效 {c['invalid_prediction']}，最终动作语法无效 {c['invalid_final']}；最终 wait {c['final_wait']}。原拒绝动作原样保留 {c['same_rejected_action_retained']}/70。中高风险只是提示，不构成禁止，也没有新增风险重审或停止。

离线最终动作只做语法与原生可执行性探针，不经过完整在线 AGC 置信度工作流；因此不能用这里的接受率预测完整 Agent 一定执行。原候选受 REC 提示影响，本轮改为 SAER 摘要和预测，又额外采样最终决策；未隔离预测本身的因果效果。

## 全样本结果

一个明确负例是 s42_a114_terminal_017：原 drop torch 原生可行，预测却把“地上4 coin”误当可释放的手持coin，建议改 drop coin；最终被环境拒绝为“not found in hand”，随后取 rust_scrap 仍失败。相同状态另一固定候选 store torch 被保持，随后取物成功但失去照明。不能只凭4/5合法终止候选被接受就认定软预测没有误导。

s44_a149_terminal_076 保持 drop meadow_herb，随后 pick up herb_tea 原生成功，确实保留一条被旧REC阻断的局部恢复路径；但最终理由仍错误声称剩余1个meadow_herb足够以后制作，不能把动作可行升级为数量理解完整。两个已执行条件损失样本均继续 drop torch、均变暗，未观察到该类损失减少。

每个 ID 对应 results/stage32/offline/ID/result.json，保存原始模型预测、最终理由、同状态/RNG原生反馈、状态哈希和可用的两步恢复探针；requests.jsonl.gz 保存两次完整请求。None 表示没有该探针或字段，不能读作失败。

{detailed}

## 核验、费用与在线入口

保存响应精确重放 {s['exact_contexts']} 个输入上下文，{s['verified_native_probe_actions']} 个原生探针动作重放一致，验证新 API 为 0。本阶段新增 {s['new_requests']} 请求，输入 {s['input_tokens']:,}、输出 {s['output_tokens']:,} token，按保存 usage 与冻结单价核算 ${s['cost_usd']:.9f}；不是可见供应商账单。

离线结果只用于完整诊断，不据此改机制或筛选在线种子。依预登记继续同模型 remnant seeds42/43/44、各最多300动作；AGC-v2三个完整对照原样复用。没有启动其他游戏。
''')
    print(json.dumps(dict(report='离线验证报告.md',samples=len(data))),flush=True)

if __name__=='__main__':main()
