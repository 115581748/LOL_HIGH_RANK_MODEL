"""English presentation layer for the native RiftScale application.

The analysis and persisted JSON stay language-neutral.  The desktop renderer
creates some labels dynamically (including Canvas and Treeview content), so a
small idempotent localisation pass also covers updates after a Riot refresh.
"""
from __future__ import annotations

import re


EXACT = {
    "峡谷天平": "RiftScale",
    "峡谷天平 · 高分段赛后对比": "RiftScale · High-rank match review",
    "请输入以 RGAPI- 开头的 Riot Development API Key。": "Enter a Riot Development API key beginning with RGAPI-.",
    "API Key 格式不正确。": "The API key format is invalid.",
    "请先输入并保存 Riot API Key。": "Enter and save a Riot API key first.",
    "本机已经保存了一个 API Key": "An API key is already saved on this device.",
    "API Key 已只保存在本机应用数据目录": "The API key is stored only in this app's local data folder.",
    "Riot API Key 已失效，请粘贴新 Key": "The Riot API key has expired. Paste a new key.",
    "无法把 API Key 保存到本机应用目录：": "Could not save the API key to the local app folder: ",
    "更新失败：": "Refresh failed: ",
    "更新完成 · 新增 ": "Updated · ",
    "OCE D4+ 基准 · 每一局都有上下文": "OCE D4+ reference · Every match in context",
    "API Key（仅保存在本机）": "API key (stored locally only)",
    "仅保存 Key": "Save key",
    "应用输入并刷新": "Load player",
    "样本宇宙": "Reference universe", "D4+ 玩家单局": "D4+ player-matches",
    "条件模型": "Conditional profiles", "英雄 × 位置 × 阶段": "Champion × role × phase",
    "当前档案": "Current profile", "最近单双排": "Recent Solo/Duo",
    "自动检查": "Auto refresh", "后台轮询": "Background polling",
    "近期手感": "Recent form", "结果": "Result", "你 vs 对位": "You vs opponent", "时长": "Duration",
    "刷新玩家后生成近期战绩轨迹": "Refresh a player to show recent match form",
    "请选择比赛": "Select a match", "请选择一场比赛": "Select a match",
    "优先复盘": "Priority review", "数据对比": "Data comparison", "整场小地图": "Full-match map",
    "正在检查反复出现的差距…": "Checking recurring gaps…",
    "比赛 / 英雄 / 胜负": "Match / champion / result", "本局": "Match", "基准中位数": "Reference median",
    "差距": "Gap", "状态": "Status", "基准样本": "Reference sample",
    "指标": "Metric", "你本局": "Your match", "对手本局": "Opponent",
    "你英雄基准（n=局数）": "Your champion reference (n=matches)",
    "对手英雄基准（n=局数）": "Opponent reference (n=matches)",
    "你−对手": "You − opponent", "你−基准": "You − reference", "对手−基准": "Opponent − reference",
    "你的表现段位": "Your performance rank", "对手表现段位": "Opponent performance rank",
    "你的指标判档": "Your metric grade", "对手指标判档": "Opponent metric grade",
    "优秀": "Excellent", "合格": "On track", "欠缺": "Needs work", "垃圾": "Poor",
    "团队情境": "Team context", "承伤量级": "Damage taken magnitude",
    "复盘时间线（拖动滑块即可跳转）": "Replay timeline (drag to seek)", "播放": "Play", "暂停": "Pause",
    "人物坐标约每 60 秒采样；事件按毫秒记录；推断信息会明确标注": "Positions are sampled about every 60s; events use millisecond timestamps; inferences are labelled",
    "地图信息层": "Map layer", "局面": "State", "事件": "Events", "对比": "Comparison", "原因": "Reasons",
    "局面 · 当前目标窗口与区域人数": "State · objective window and nearby players",
    "TAB 对局面板 · 当前时刻": "Scoreboard · current moment", "蓝方": "Blue team", "红方": "Red team",
    "每 1 分钟自动检查新比赛": "Check for new matches every minute",
    " · 对局进行中无法读取实时坐标": " · Live match coordinates are unavailable",
    "程序已就绪": "Ready", "等待 Riot API Key": "Waiting for Riot API key",
    "正在检查 Riot 最近比赛…": "Checking recent Riot matches…",
    "输入 Riot ID 与 API Key 后生成本机赛后分析。": "Enter a Riot ID and API key to generate a local post-match review.",
    "前期 0–15": "Early 0–15", "中期 15–25": "Mid 15–25", "后期 25+": "Late 25+",
    "上路": "Top", "打野": "Jungle", "中路": "Mid", "下路": "Bot", "辅助": "Support",
    "发育": "Farming", "对线": "Laning", "生存": "Survival", "输出": "Damage",
    "战斗": "Combat", "地图资源": "Objectives", "视野": "Vision", "野区节奏": "Jungle tempo",
    "本局最强": "Strongest this match", "弱四分位 · 优先看": "Bottom quartile · review first",
    "不弱于中位数": "At or above median", "弱于中位数": "Below median",
    "胜": "Win", "负": "Loss", "未知": "Unknown", "未知英雄": "Unknown champion",
    "当前局面": "Current state", "最近事件": "Recent events", "当前对位": "Current matchup",
    "目标窗口": "Objective window", "目标区域人数（位置估计）": "Players near objective (position estimate)",
    "你的移动趋势": "Your movement trend", "最近 90 秒视野动作": "Vision actions in last 90s",
    "支持证据": "Supporting evidence", "主要候选原因": "Leading candidate reason",
    "候选关联（非确定因果）": "Candidate relationship (not proven causation)",
    "防御塔": "Turret", "召唤水晶": "Inhibitor", "纳什男爵": "Baron Nashor",
    "峡谷先锋": "Rift Herald", "虚空巢虫": "Void Grubs", "史诗野怪": "Epic monster",
    "火龙": "Infernal Drake", "土龙": "Mountain Drake", "水龙": "Ocean Drake", "风龙": "Cloud Drake",
    "海克斯龙": "Hextech Drake", "炼金龙": "Chemtech Drake", "远古龙": "Elder Dragon",
    "王者": "Challenger", "宗师": "Grandmaster", "大师": "Master", "钻石 I": "Diamond I",
    "钻石 IV": "Diamond IV", "翡翠 II": "Emerald II", "铂金 II": "Platinum II",
    "黄金 II": "Gold II", "白银 I": "Silver I", "高": "High", "中": "Medium", "低": "Low",
    "全场视野分/分钟": "Vision score/min", "全场视野得分": "Vision score",
    "弱四分位": "bottom quartile", "优先看": "review first",
    "双击证据可回到该局的数据对比。": "Double-click an evidence row to open that match's data comparison.",
    "本局没有检测到己方丢失的龙或先锋": "No allied dragon or Rift Herald loss was detected in this match",
    "现有数据不足以判断主要原因": "There is not enough available data to identify a leading reason",
    "不会强行生成因果结论。": "No causal conclusion will be forced.",
    "另一种解释：": "Alternative explanation: ",
    "置信": " confidence",
    "阶段结果与英雄基准": "Phase results and champion reference",
    "Riot 原始事件 + 紫色规则识别团战": "Riot source events + purple rule-derived teamfights",
    "紫色规则识别团战": "purple rule-derived teamfights",
    "Riot 原始事件": "Riot source events",
    "本机已经保存了一个 API Key": "An API key is already saved on this device.",
    "正在检查 Riot 最近比赛…": "Checking recent Riot matches…",
    "15 分钟经济": "Gold at 15", "15 分钟经验": "XP at 15", "15 分钟 CS": "CS at 15",
    "15 分钟补刀": "CS at 15", "15–25 分钟补刀增长": "CS gained 15–25 min",
    "前期有效 Gank": "Early effective ganks",
    "15–25 经济增长": "Gold gained 15–25", "15–25 CS 增长": "CS gained 15–25",
    "15–25 英雄伤害": "Champion damage 15–25", "25+ 每分钟英雄伤害": "Champion damage/min after 25",
    "25+ 每分钟承伤": "Damage taken/min after 25", "后期团战参与率": "Late teamfight participation",
    "后期首个阵亡": "First late-teamfight death", "当前窗口没有关键事件": "No key events in this window",
    "未来 90 秒无史诗事件": "No epic objective in the next 90s", "明显位移": "Significant movement",
    "位置变化较小": "Little movement", "等待复盘数据": "Waiting for replay data",
    "该局未达到 25 分钟": "Match ended before 25 minutes", "该局未进入 25+ 分钟阶段": "Match did not reach the 25+ phase",
    "选择一场比赛后显示优先复盘方向。": "Select a match to see what to review first.",
    "同英雄同位置基准或本局指标不足，暂不判定优先复盘项。": "Not enough champion- and role-matched evidence to suggest a review priority.",
    "没有低于 P50 的个人指标；可继续核对对位差与关键事件。": "No individual metric is below P50; check matchup gaps and key events if needed.",
    "这是复盘线索，不证明输因。": "This is a review lead, not proof of why the match was lost.",
    "回看漏刀、回城和空转时间。": "Review missed CS, recalls and idle time.",
    "回看对线或抓人时机，核对当时的队友与敌方位置。": "Review laning or gank timing alongside allied and enemy positions.",
    "回看死亡前的位置、视野和撤退时机。": "Review positioning, vision and escape timing before each death.",
    "先核对到场、存活与可输出时间。": "First check arrival, survival and time able to deal damage.",
    "回看团战到场与进场条件。": "Review arrival and engage conditions in teamfights.",
    "回看资源刷新前的转线与到场时机。": "Review rotations and arrival timing before objective spawns.",
    "回看资源争夺前的布眼与排眼；得分不等于眼位质量。": "Review warding and clearing before objectives; score does not measure ward quality.",
    "回看该指标对应的关键事件。": "Review the key events relevant to this metric.",
    "没有满足英雄、位置和最低样本量要求的指标": "No metrics meet the champion, role and minimum-sample requirements",
    "这场比赛还没有分钟复盘数据；使用 API 刷新后会自动生成": "This match has no minute replay yet; an API refresh will generate it.",
    "最近 20 场没有指标达到重复弱项阈值；偶发差距仍列出，但不会被包装成稳定问题。": "No metric crossed the recurring weakness threshold in the last 20 matches. One-off gaps remain visible but are not presented as a persistent problem.",
    "同英雄同位置 D4+ 跨版本参考；差距提示复盘方向，不证明输因，也不等于实际段位。": "Champion- and role-matched D4+ cross-patch reference. A gap suggests what to review; it does not prove why the match was lost or equal actual rank.",
    "回看 15 分钟前漏掉的兵线或空转时间，找一次可避免的资源损失。": "Review missed waves or idle time before 15 minutes and identify one avoidable resource loss.",
    "对照补刀和死亡，确认经济差来自哪里，再选择一个可改变的环节。": "Compare CS and deaths to identify the source of the gold gap, then pick one changeable moment.",
    "逐次检查死亡前的位置和已知敌人信息，记录一次可以提前撤退的时机。": "Review your position and known enemy information before each death; identify one earlier retreat opportunity.",
    "回看前 15 分钟路线与队友交战时机；这里只统计参与击杀非打野目标。": "Review early jungle pathing and teammate fights. This metric counts takedowns of non-jungle targets only.",
    "检查转线、回城和等待团战之间是否有可安全获取的资源。": "Check whether safe farm was available during rotations, recalls and waits for fights.",
    "回看死亡前是否缺少队友支援或敌人位置，记录可改变的进场条件。": "Review teammate support and enemy positions before death, then note a changeable condition for entering.",
    "先检查到场、存活和可攻击时间，再判断是否存在输出机会浪费。": "Check arrival, survival and time in range before judging whether damage opportunities were missed.",
    "辅助复盘下一次资源争夺前的视野布置；得分本身不代表眼位质量。": "Review vision setup before the next objective contest. Vision score alone does not measure ward quality.",
    "前期击杀": "Early kills", "前期死亡": "Early deaths", "前期助攻": "Early assists",
    "中期击杀": "Mid-game kills", "中期死亡": "Mid-game deaths", "中期助攻": "Mid-game assists",
    "后期击杀": "Late kills", "后期死亡": "Late deaths", "后期助攻": "Late assists",
    "15 分钟对位经济差": "Gold diff at 15 vs jungler", "15 分钟对位经验差": "XP diff at 15 vs jungler",
    "15 分钟对位 CS 差": "CS diff at 15 vs jungler", "前 15 分钟有效 Gank": "Effective ganks by 15",
    "前 15 分钟影响路线数": "Lanes influenced by 15", "首次有效 Gank 分钟": "First effective gank minute",
    "前期对敌方打野击杀参与": "Early takedowns of enemy jungler",
    "前期团队击杀参与率": "Early team kill participation", "前期团队小龙": "Early team dragons",
    "前期团队虚空巢虫": "Early team Void Grubs", "前期团队峡谷先锋": "Early team Rift Heralds",
    "前期个人史诗野怪击杀": "Early personal epic objective secures",
    "前期有效 Gank 对位差": "Early effective-gank gap vs jungler",
    "前期史诗野怪对位差": "Early epic objective gap vs jungler",
    "中期有效 Gank": "Mid-game effective ganks", "中期影响路线数": "Mid-game lanes influenced",
    "中期首次有效 Gank 分钟": "First mid-game effective gank minute",
    "中期对敌方打野击杀参与": "Mid-game takedowns of enemy jungler",
    "中期团队击杀参与率": "Mid-game team kill participation",
    "中期团队小龙": "Mid-game team dragons", "中期团队虚空巢虫": "Mid-game team Void Grubs",
    "中期团队峡谷先锋": "Mid-game team Rift Heralds",
    "中期个人史诗野怪击杀": "Mid-game personal epic objective secures",
    "中期有效 Gank 对位差": "Mid-game effective-gank gap vs jungler",
    "中期史诗野怪对位差": "Mid-game epic objective gap vs jungler",
    "人物坐标采样": "position sample", "当前 ": "Current ",
    "局面 · 当前目标窗口、区域人数与移动趋势": "State · objective window, nearby players and movement",
    "己方": "Allies", "对方": "Enemies", "塔/": " turrets / ",
    "无法读取本机玩家缓存，已使用内置案例：": "Could not read the local player cache; using the built-in demo: ",
}

PHRASES = sorted([
    ("本局指标按同英雄＋同位置 D4+ 分位判档：P75+ 优秀、P50+ 合格、P25+ 欠缺、低于 P25 垃圾。仅评指标，不评人；团队结果只作情境。", "Match metrics use champion- and role-matched D4+ percentiles: P75+ Excellent, P50+ On track, P25+ Needs work, below P25 Poor. These labels describe metrics, not people; team results are context only."),
    ("本局能力段位", "match performance profile"), ("选择一场比赛后生成单局能力段位", "Select a match to generate its performance profile"),
    ("本局指标判档", "match metric grades"), ("选择一场比赛后生成单局指标判档", "Select a match to see its metric grades"),
    ("优先复盘：", "Review first: "), ("这是复盘线索，不证明输因。", "This is a review lead, not proof of why the match was lost."),
    ("团队情境", "Team context"), ("承伤量级", "Damage taken magnitude"),
    ("优秀", "Excellent"), ("合格", "On track"), ("欠缺", "Needs work"), ("垃圾", "Poor"),
    ("每 1 分钟", "Every minute"), ("场 · 胜率", " matches · win rate"), ("连胜", "win streak"), ("连败", "loss streak"),
    ("下一步：", "Next step: "), ("最近 ", "Last "), ("项指标", " metrics"),
    ("前期 0–15", "Early 0–15"), ("中期 15–25", "Mid 15–25"), ("后期 25+", "Late 25+"),
    ("钻石 IV", "Diamond IV"), ("钻石 I", "Diamond I"), ("翡翠 II", "Emerald II"),
    ("铂金 II", "Platinum II"), ("黄金 II", "Gold II"), ("白银 I", "Silver I"),
    ("王者", "Challenger"), ("宗师", "Grandmaster"), ("大师", "Master"),
    ("生存", "Survival"), ("野区节奏", "Jungle tempo"), ("发育", "Farming"),
    ("战斗", "Combat"), ("地图资源", "Objectives"), ("视野", "Vision"), ("对线", "Laning"),
    ("前期击杀", "Early kills"), ("前期死亡", "Early deaths"), ("前期助攻", "Early assists"),
    ("基准", "reference"), ("表现段位", "performance rank"), ("对位经济", "matchup gold"),
    ("局面 · 当前目标窗口、区域人数与移动趋势", "State · objective window, nearby players and movement"),
    ("当前 ", "Current "), ("人物坐标采样", "position sample"),
    ("己方", "Allies"), ("对方", "Enemies"), ("塔/", " turrets / "),
    ("分钟位置快照", "minute position snapshot"), ("分钟状态快照", "minute state snapshot"),
    ("Riot事件", "Riot event"), ("规则识别", "rule-derived"), ("购买事件", "purchase event"),
    ("插眼", "wards placed"), ("排眼", "wards cleared"), ("已阵亡", "dead"), ("预计", "estimated"),
    ("人参与", " participants"),
], key=lambda pair: len(pair[0]), reverse=True)


def english(text: object) -> str:
    """Translate UI text while leaving identifiers and numeric values intact."""
    value = str(text or "")
    stripped = " ".join(value.split())
    if stripped in EXACT:
        return EXACT[stripped]
    translated = re.sub(
        r"最近\s*(\d+)\s*场发现\s*(\d+)\s*项达到重复弱项规则。双击证据可回到该局的数据对比。",
        lambda match: (
            f"In the last {match.group(1)} matches, {match.group(2)} recurring "
            f"{'weakness' if match.group(2) == '1' else 'weaknesses'} met the rule. "
            "Double-click an evidence row to open that match's data comparison."
        ),
        value,
    )
    translated = re.sub(
        r"最近\s*(\d+)\s*场没有指标达到重复弱项阈值；偶发差距仍列出，但不会被包装成稳定问题。",
        r"No metric crossed the recurring weakness threshold in the last \1 matches. One-off gaps remain visible but are not presented as persistent problems.",
        translated,
    )
    for source, target in sorted(EXACT.items(), key=lambda pair: len(pair[0]), reverse=True):
        if len(source) > 2:
            translated = translated.replace(source, target)
    for source, target in PHRASES:
        translated = translated.replace(source, target)
    translated = re.sub(r"(\d+)\s*场", r"\1 matches", translated)
    translated = re.sub(r"(\d+(?:\.\d+)?)\s*分钟", r"\1 min", translated)
    translated = re.sub(r"\s*项达到重复弱项规则。", " recurring weakness(es) met the rule.", translated)
    translated = re.sub(r"更新完成\s*·\s*新增\s*(\d+)\s*matches", r"Updated · \1 new matches", translated)
    translated = re.sub(r"(\d+)龙", r"\1 dragons", translated)
    translated = re.sub(r"第\s*(\d+)\s*match", r"Match \1", translated)
    translated = translated.replace("未知事件", "Unknown event").replace("未知时间", "Unknown time")
    translated = re.sub(r"(?<= · )胜(?= · |$)", "Win", translated)
    translated = re.sub(r"(?<= · )负(?= · |$)", "Loss", translated)
    translated = translated.replace("Priority review：", "Review first: ").replace("（", " (").replace("）", ")").replace("。", ". ")
    return re.sub(r"[ \t]{2,}", " ", translated)


def localize_widget_tree(root) -> None:
    """Translate standard widgets, Notebook tabs, Treeviews and Canvas text."""
    try:
        text = root.cget("text")
        if text:
            root.configure(text=english(text))
    except Exception:
        pass


    try:
        placeholder = root.cget("placeholder")
        if placeholder:
            root.configure(placeholder=english(placeholder))
    except Exception:
        pass


    widget_class = str(root.winfo_class()) if hasattr(root, "winfo_class") else ""
    if widget_class == "TNotebook":
        try:
            for tab in root.tabs():
                root.tab(tab, text=english(root.tab(tab, "text")))
        except Exception:
            pass
    if widget_class == "Treeview":
        try:
            for column in root.cget("columns"):
                root.heading(column, text=english(root.heading(column, "text")))
            for item in root.get_children(""):
                values = root.item(item, "values")
                if values:
                    root.item(item, values=tuple(english(value) for value in values))
        except Exception:
            pass
    if widget_class == "TCombobox":
        try:
            values = root.cget("values")
            if values:
                root.configure(values=tuple(english(value) for value in values))
            value = root.get()
            translated_value = english(value)
            if value and translated_value != value:
                root.set(translated_value)
        except Exception:
            pass
    if widget_class == "Canvas":
        try:
            for item in root.find_all():
                if root.type(item) == "text":
                    value = root.itemcget(item, "text")
                    if value:
                        root.itemconfigure(item, text=english(value))
        except Exception:
            pass
    try:
        for child in root.winfo_children():
            localize_widget_tree(child)
    except Exception:
        pass


def untranslated_widget_text(root) -> list[str]:
    """Return visible Chinese UI strings for packaging smoke checks."""
    values: list[str] = []
    try:
        value = root.cget("text")
        if value and re.search("[\u4e00-\u9fff]", str(value)):
            values.append(str(value))
    except Exception:
        pass
    try:
        widget_class = str(root.winfo_class())
        if widget_class == "Canvas":
            for item in root.find_all():
                if root.type(item) == "text":
                    value = root.itemcget(item, "text")
                    if re.search("[\u4e00-\u9fff]", value):
                        values.append(value)
        elif widget_class == "Treeview":
            for column in root.cget("columns"):
                value = root.heading(column, "text")
                if re.search("[\u4e00-\u9fff]", value):
                    values.append(value)
            for item in root.get_children(""):
                for value in root.item(item, "values"):
                    if re.search("[\u4e00-\u9fff]", str(value)):
                        values.append(str(value))
        elif widget_class == "TCombobox":
            for value in root.cget("values"):
                if re.search("[\u4e00-\u9fff]", str(value)):
                    values.append(str(value))
            value = root.get()
            if re.search("[\u4e00-\u9fff]", str(value)):
                values.append(str(value))
    except Exception:
        pass
    try:
        for child in root.winfo_children():
            values.extend(untranslated_widget_text(child))
    except Exception:
        pass
    return values
