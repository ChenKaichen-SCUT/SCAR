# Stage32 修复后单种子

只记录修复后seed42一次运行。**NO_MAIN_PROGRESS_GAIN**，新请求1130，usage费用$0.718147098。旧Stage32结果已从当前目录和当前Git版本移除，Git历史未改写。

- [实验报告](Stage32实验报告.md)
- [语法修复与单种子协议](语法修复与单种子协议.md)
- [动作反思和语法审计](动作反思与语法审计.md)
- [研究判断](三游戏扩展与研究判断.md)
- [Git变更记录](Git变更记录.md)

配置冻结依赖、PYTHONHASHSEED=0、AGENTODYSSEY_ROOT和PYTHONPATH后，依次运行scar_stage32.verify --archive-only、analyze、cases、report、validate_analysis模块可复算，均零API；不要运行batch复算。原始响应、轨迹、局部反事实、逐步证据、模型usage和冻结哈希均在results/stage32。下载依赖和凭据不上传。
