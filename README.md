# 峡谷行为基准

这是 `https://115581748.github.io/LOL_HIGH_RANK_MODEL/` 的静态站点源文件。

- `index.html`：62,613 条 OCE D4+ 玩家—单局记录的完整指标仪表盘，覆盖 4,359 名玩家与 7,277 场比赛。
- `conditional-model.html`：按英雄、位置、补丁、段位和阶段查询的参考模型，以及 Geolonwe#OC 的纯数据差距案例。

本次冻结快照含 62,735 条原始记录；按“玩家 PUUID＋比赛 ID”移除 122 条内容完全相同的重复记录后，建模数据为 62,613 条。没有冲突重复、损坏 JSON、空身份键或 CSV 残留重复。

阶段口径为前期 0–15、中期 15–25、后期 25+；25 分钟取大龙首次刷新时点。逐局案例固定与同英雄、同位置的 D4+ 跨版本基准比较，不再按经济领先或落后切换基准。

发布方式：

站点由仓库 `115581748/LOL_HIGH_RANK_MODEL` 的 `main` 分支根目录发布。

模型数据不包含 Riot API Key 或玩家 PUUID；本地玩家案例只发布去标识化逐局行为指标与聚合统计，不含人工评价。

## Windows 赛后复盘程序

仓库同时包含 Python/Tkinter 原生程序源码，入口为 `desktop/lol_high_rank_comparator.py`，完整建模与运行说明见 [MODEL_README.md](MODEL_README.md)。程序可以输入 `玩家名#TAG` 和新的 Riot Development Key，每分钟检查一次最近比赛，并把本局与同英雄、同位置的 OCE D4+ 基准逐项比较。

`整场小地图` 使用 Riot Data Dragon 图标显示英雄、装备、召唤师技能、塔、龙、龙魂、水晶等信息；地图下方的图标化 TAB 面板随时间线重建双方等级、K/D/A、补刀、经济和装备。人物坐标约每分钟采样一次，击杀与目标事件保留原始毫秒时间戳，时间线可按秒拖动。

Riot Timeline API 不提供小兵实时坐标，因此三路兵线只依据 1:05 首波、每 30 秒刷新、标准路线和移动速度估算；界面会明确标注这一限制。仓库不提交 API Key、本地缓存、构建目录或 EXE，Windows 可执行文件可依据 `desktop/LOLHighRankComparator.spec` 在本地重建。
