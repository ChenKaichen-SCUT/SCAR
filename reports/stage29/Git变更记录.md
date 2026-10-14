# Stage29 Git 变更记录

基线 `14b16e0876bcf488cb33a037476ceeeee2d5b051`；冻结提交 `1353d3508714bd9d28dbd5994b021fb09382efa6`；分析结果提交 `33137ee952721a5ecd788958b43b629c2b3b9e79`。本记录另行提交，不作提交号自引用。

基线到结果提交共 56 个文件，新增文本 29,538 行，删除 0 行；诊断 Python 新增 625 行，删除 0 行。逐文件统计见 `results/stage29/change_accounting.json`。

|诊断代码|新增|删除|
|---|---|---|
|scar_stage29/__init__.py|1|0|
|scar_stage29/annotations.py|73|0|
|scar_stage29/audit.py|41|0|
|scar_stage29/common.py|22|0|
|scar_stage29/extract.py|82|0|
|scar_stage29/freeze.py|19|0|
|scar_stage29/native_probe.py|48|0|
|scar_stage29/report.py|186|0|
|scar_stage29/stacks.py|62|0|
|scar_stage29/summarize.py|40|0|
|scar_stage29/verify.py|51|0|

新增实验模型请求 **0**；新增实验费用 **$0**。原生离线前缀回放24步，隔离候选动作2次。未执行可选 Oracle Goal Stack 模型重放，没有以未运行代替“无收益”结果。

生产 Agent、模型配置、环境、prompt、Stage28及更早的数据均保持冻结。未实现Goal Stack或下一阶段算法。归档只包括本项目分析代码、统计、原文证据和报告，不包含下载依赖或API凭据。
