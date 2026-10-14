# Stage28 Git 变更记录

基线：`87af2697b96128f0bab8d44bb81b5b360ef2508d`。冻结提交：`07c828474a45945e417097d9369ed54ad3275c8f`。实验/分析结果提交：`e4781a5c14231b74d87947e78b47224f34b99a82`。本归档说明另行提交，提交号可由 Git 历史取得，避免自引用。

基线到结果提交共 174 个文件，文本新增 117,747 行、删除 0 行；其中诊断 Python 新增 887 行、删除 0 行。生产 Agent 修改文件数 0，旧环境与旧数据哈希未变。逐文件增删与二进制标记见 `results/stage28/change_accounting.json`；本记录本身不计入这些统计。

|诊断代码文件|新增|删除|
|---|---|---|
|scar_stage28/__init__.py|1|0|
|scar_stage28/analyze.py|101|0|
|scar_stage28/audit.py|50|0|
|scar_stage28/batch.py|20|0|
|scar_stage28/chain.py|125|0|
|scar_stage28/common.py|35|0|
|scar_stage28/freeze.py|20|0|
|scar_stage28/prepare.py|58|0|
|scar_stage28/provider.py|22|0|
|scar_stage28/report.py|203|0|
|scar_stage28/review.py|31|0|
|scar_stage28/run.py|70|0|
|scar_stage28/smoke.py|46|0|
|scar_stage28/verify.py|105|0|

新增模型调用 **1723** 次；费用 **$1.431532680**（逐响应 usage 与单价核算，非供应商账单）。Original 复用 10 个保存后缀，新增调用 0。分析/离线重放新增调用 0。未重跑失败分支。

Stage28 的提示注入仅用于诊断，不是 Agent 算法更改；未实施后续恢复控制器。公开归档只包含本项目代码、结果、检查点与报告，不包含下载依赖和 API 凭据。
