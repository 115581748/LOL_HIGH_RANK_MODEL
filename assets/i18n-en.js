/* RiftScale English presentation layer.
 *
 * The model payload deliberately remains language-neutral.  This layer runs
 * after every DOM update so content produced by the static page, the player
 * service, and the replay renderer is translated consistently.
 */
(() => {
  "use strict";

  const exact = new Map(Object.entries({
    "下载 Windows EXE": "Download Windows app",
    "正在读取条件模型": "Loading reference model",
    "不是一个混合平均值，而是同英雄参考模型。": "Not a blended average. A champion-matched reference model.",
    "不是一个混合平均值，": "Not a blended average,",
    "而是": "but a",
    "同英雄参考模型": "champion-matched reference model",
    "。": ".",
    "玩家单局记录": "Player-match records", "条件分布模型": "Conditional profiles",
    "同英雄比较模型": "Champion-matched profiles", "最低建模样本": "Minimum sample size",
    "选择英雄、位置、版本与阶段": "Choose champion, role, patch and phase",
    "聚合模型不足时自动回退": "Falls back when an exact profile is too small",
    "英雄": "Champion", "位置": "Role", "版本": "Patch", "段位层": "Rank band", "阶段": "Phase",
    "单项指标分布": "Metric distributions", "高分样本": "High-rank sample", "高分中位数": "High-rank median",
    "本地玩家中位数": "Player median", "差值 vs 高分中位数": "Gap vs high-rank median", "经验分位": "Empirical percentile", "指标判档": "Metric grade",
    "阶段行为相关矩阵": "Within-phase correlation matrix", "时间稳定性": "Time stability",
    "查询玩家": "Find a player", "Riot API Key（仅本机保存）": "Riot API key (stored locally only)",
    "保存 Key": "Save key", "切换并更新": "Load player", "刷新当前玩家": "Refresh player",
    "正在检查安全更新服务…": "Checking the secure update service…",
    "PRIORITY REVIEW / 优先复盘": "PRIORITY REVIEW", "哪些差距真的反复出现？": "Which gaps keep recurring?",
    "正在检查逐局证据…": "Checking match-level evidence…", "只呈现可复算的数据差距": "Only reproducible gaps are shown",
    "玩家统计量": "Player statistic", "逐场指标中位数": "Median across matches",
    "比较基线": "Comparison baseline", "D4+ 条件中位数": "Conditional D4+ median",
    "对位差定义": "Lane-opponent gap", "玩家本局 − 对手本局": "Player value − opponent value",
    "基准差定义": "Reference gap", "各方本局 − 各自英雄基准": "Each player − their champion reference",
    "最近 20 场同结构对照": "Last 20 matches in the same structure", "单双排": "Ranked Solo/Duo",
    "主位置": "Primary role", "主英雄": "Most-played champion", "等待数据。": "Waiting for data.",
    "场次": "Match", "你 / 对位英雄": "You / opponent", "胜负": "Result", "15 分钟 CS": "CS at 15",
    "中期 CS": "Mid-game CS", "中期伤害": "Mid-game damage", "后期首个阵亡": "First late death",
    "逐局双方数据与英雄基准": "Match-by-match values and champion references", "比较阶段": "Comparison phase",
    "网页版整场小地图与 TAB 面板": "Full-match map replay and scoreboard", "选择比赛": "Select match",
    "位置采样 —": "Position sample —", "播放": "Play", "暂停": "Pause", "选择比赛后显示事件。": "Select a match to view events.",
    "团战、资源与证据": "Teamfights, objectives and evidence", "蓝方": "Blue team", "红方": "Red team",
    "解释边界": "Interpretation limits", "非 Riot Games 官方项目": "Not endorsed by Riot Games",
    "返回全指标基准仪表盘 →": "Back to the full metric dashboard →",
    "同一场比赛可能贡献多名 D4+ 玩家记录，因此玩家单局并非完全独立；分布和相关矩阵是描述模型，不自动等于因果或正确决策。逐局对手按 Riot 标记的同位置匹配；异常位置或重开局可能没有对手。双方基准都只接受同英雄、同位置的跨版本样本，找不到就明确显示无基准。": "A single match may contribute multiple D4+ player records, so player-match observations are not fully independent. Distributions and correlations are descriptive; they do not prove causation or correct decisions. Opponents are matched by Riot's role assignment, and unusual role assignments or remakes may have no opponent. Both references require the same champion and role across patches; when no valid reference exists, the page says so explicitly.",
    "打野会额外显示对位资源差、有效 Gank、影响路线、团队史诗野怪和相对敌方打野的行动差。“有效 Gank”严格定义为参与击杀非打野目标；Riot 时间线不提供可靠的失败 Gank 事件，因此这里不伪造“尝试次数”。": "Jungle views add opponent resource gaps, effective ganks, lanes influenced, team epic objectives and action gaps versus the enemy jungler. An effective gank strictly means a takedown on a non-jungle target. Riot Timeline does not reliably record failed gank attempts, so this product does not invent an attempt count.",
    "每个单元格显示：你的本局值、对手本局值、双方各自英雄的 D4+ 基准中位数、你减对手的对位差，以及双方各自相对基准的差值与经验分位。基准只匹配“该方英雄＋该方位置”，不使用当局经济局势，也不回退到其他英雄；25 分钟后的伤害与承伤按实际 25+ 时长折算为每分钟，25 分钟前的口径保持不变。": "Each cell shows your value, the opponent value, each champion's D4+ reference median, the head-to-head gap, and both players' reference gaps and empirical percentiles. References match that player's champion and role only; they do not condition on the match economy or fall back to another champion. Damage and damage taken after 25 are rates over the actual time played after 25; pre-25 definitions are unchanged.",
    "前期 0–15": "Early 0–15", "中期 15–25": "Mid 15–25", "后期 25+": "Late 25+",
    "上路": "Top", "打野": "Jungle", "中路": "Mid", "下路": "Bot", "辅助": "Support",
    "高置信度": "High confidence", "中等置信度": "Medium confidence", "低置信度": "Low confidence",
    "胜": "Win", "负": "Loss", "未知": "Unknown", "无基准": "No reference", "指标": "Metric",
    "你本局": "Your match", "对手本局": "Opponent", "你英雄基准": "Your champion reference",
    "对手英雄基准": "Opponent champion reference", "你−对手": "You − opponent", "你−基准": "You − reference",
    "对手−基准": "Opponent − reference", "你的表现段位": "Your performance rank", "对手表现段位": "Opponent performance rank",
    "指标判档：": "Metric grades:", "P75+ 优秀": "P75+ Excellent", "P50+ 合格": "P50+ On track", "P25+ 欠缺": "P25+ Needs work", "低于 P25 垃圾": "Below P25 Poor",
    "仅评价该项指标相对同英雄同位置 D4+ 样本的表现，不评价玩家本人；团队结果和承伤不判档。": "Grades describe this metric against champion- and role-matched D4+ samples, not the player as a person. Team results and damage taken are not graded.",
    "本局先看": "Review first", "同英雄同位置基准或本局指标不足，暂不判定。": "Not enough champion- and role-matched evidence to suggest a review priority.",
    "没有低于 P50 的个人指标": "No individual metric is below P50",
    "可核对对位差和关键事件；不直接归因胜负。": "You can check matchup gaps and key events; this is not a claim about the match result.",
    "发育": "Farming", "对线": "Laning", "生存": "Survival", "输出": "Damage", "战斗": "Combat",
    "地图资源": "Objectives", "视野": "Vision", "本局最强": "Strongest this match", "优先复盘": "Review first",
    "局面": "State", "事件": "Events", "对比": "Comparison", "原因": "Reasons",
    "防御塔": "Turret", "召唤水晶": "Inhibitor", "纳什男爵": "Baron Nashor", "峡谷先锋": "Rift Herald",
    "虚空巢虫": "Void Grubs", "史诗野怪": "Epic monster", "龙魂": "Dragon Soul", "团战": "Teamfight",
    "王者": "Challenger", "宗师": "Grandmaster", "大师": "Master", "钻石 I": "Diamond I",
    "钻石 IV": "Diamond IV", "翡翠 II": "Emerald II", "铂金 II": "Platinum II", "黄金 II": "Gold II", "白银 I": "Silver I"
  }));

  const phrases = [
    ["按英雄、位置、版本、段位和阶段查看 D4+ 玩家行为分布。逐局案例同时显示你和同位置对手的本局值，并分别匹配双方英雄自己的跨版本高分基准。", "Explore D4+ behaviour distributions by champion, role, patch, rank band and phase. Each match compares you with your role opponent and matches both players to their own champion-specific high-rank reference."],
    ["中心以中位数为主，同时保留 P10–P90、MAD、缺失率和 Winsorize 边界。这里描述高分玩家在相同条件下“通常是什么样”，不把统计异常直接判成失误。", "The median is the centre, with P10–P90, MAD, missingness and Winsorisation bounds retained. These distributions describe what high-rank players usually look like under matching conditions; an outlier is not automatically labelled a mistake."],
    ["同一个低伤害结果，可能来自经济不足、死亡过早或到场问题。相关矩阵先保留这些联合关系，不急着压成一个总分。", "The same low-damage result may come from low income, an early death, or late arrival. The correlation matrix preserves these joint relationships instead of forcing them into one score."],
    ["把样本按时间切成前后两半，检查中位数位移是否仍落在可接受的 IQR 比例内。", "The sample is split into earlier and later halves to check whether median drift remains acceptable relative to the IQR."],
    ["正负号仅表示数值方向。例如死亡数为负差值只代表更少死亡；页面不自动把它解释成更好或更差。", "Signs show numerical direction only. A negative death gap means fewer deaths; the page does not automatically call every direction better or worse."],
    ["人物坐标来自赛后 Timeline 约每 60 秒一次的采样；击杀、购买、视野、塔和史诗野怪使用事件时间戳。阵亡地点是事实，复活时间只作估计且不进入评分。", "Champion positions come from post-match Timeline samples roughly every 60 seconds. Kills, purchases, vision, structures and epic objectives use event timestamps. Death locations are observed; respawn times are estimates and never enter ratings."],
    ["团战为规则派生事件：至少 3 次英雄击杀，且相邻击杀间隔不超过 15 秒。候选原因保留原始证据；时间先后不等于因果。", "Teamfights are derived events: at least three champion kills with no more than 15 seconds between consecutive kills. Candidate reasons retain their source evidence; sequence does not prove causation."],
    ["团队情境", "Team context"], ["承伤量级", "Damage taken magnitude"], ["无法判档", "Not graded"],
    ["优秀", "Excellent"], ["合格", "On track"], ["欠缺", "Needs work"], ["垃圾", "Poor"],
    ["你：", "You: "], ["对：", "Opp.: "], ["玩家：", "Player: "],
    ["优先复盘：", "Review first: "], ["仅为复盘线索，不证明输因。", "A review lead, not proof of why the match was lost."],
    ["回看阵亡前的站位、视野与撤退时机。", "Review positioning, vision and retreat timing before deaths."],
    ["回看兵线、回城和空转时间，核对资源差从何时开始。", "Review waves, recalls and idle time to see when the resource gap started."],
    ["回看路线与抓人时机，核对双方位置。", "Review pathing and gank timing alongside both teams' positions."],
    ["先核对到场、存活和可输出时间。", "First check arrival, survival and time able to deal damage."],
    ["回看资源争夺前的布眼与排眼。", "Review warding and clearing before objective contests."],
    ["回看团战到场与进场条件。", "Review arrival and engage conditions in teamfights."],
    ["回看相关时间点的事件与小地图。", "Review events and the map at the relevant time."],
    ["全场视野分/分钟", "Vision score/min"], ["全场视野得分", "Vision score"],
    ["15 分钟经济增长", "Gold at 15"], ["15 分钟经济", "Gold at 15"], ["15 分钟经验", "XP at 15"],
    ["15 分钟对位经济差", "Gold diff at 15"], ["15 分钟对位经验差", "XP diff at 15"], ["15 分钟对位 CS 差", "CS diff at 15"],
    ["前 15 分钟有效 Gank", "Effective ganks by 15"], ["前 15 分钟影响路线数", "Lanes influenced by 15"],
    ["首次有效 Gank 分钟", "First effective gank minute"], ["团队击杀参与率", "Team kill participation"],
    ["团队小龙", "Team dragons"], ["团队虚空巢虫", "Team Void Grubs"], ["团队峡谷先锋", "Team Rift Heralds"],
    ["个人史诗野怪击杀", "Personal epic objective secures"], ["有效 Gank 对位差", "Effective-gank opponent gap"],
    ["史诗野怪对位差", "Epic-objective opponent gap"], ["15–25 经济增长", "Gold gained 15–25"],
    ["15–25 CS 增长", "CS gained 15–25"], ["15–25 英雄伤害", "Champion damage 15–25"],
    ["中期经济增长", "Mid-game gold gained"], ["中期 CS 增长", "Mid-game CS gained"], ["中期英雄伤害", "Mid-game champion damage"],
    ["25 分钟后每分钟英雄伤害", "Champion damage/min after 25"], ["25 分钟后每分钟承伤", "Damage taken/min after 25"],
    ["25+ 每分钟英雄伤害", "Champion damage/min after 25"], ["25+ 每分钟承伤", "Damage taken/min after 25"],
    ["前期击杀", "Early kills"], ["前期死亡", "Early deaths"], ["前期助攻", "Early assists"],
    ["中期击杀", "Mid-game kills"], ["中期死亡", "Mid-game deaths"], ["中期助攻", "Mid-game assists"],
    ["后期击杀", "Late kills"], ["后期死亡", "Late deaths"], ["后期助攻", "Late assists"],
    ["后期团战参与率", "Late teamfight participation"], ["后期首个阵亡", "First death in late teamfights"],
    ["任意玩家名#TAG 或 OP.GG 链接", "Any Riot ID#TAG or OP.GG URL"], ["未知英雄", "Unknown champion"],
    ["没有基准", "No reference"], ["基准", "Reference"], ["对位差", "Opponent gap"], ["本局", "Match"],
    ["你 ", "You "], ["对 ", "Opp. "]
  ].sort((a, b) => b[0].length - a[0].length);

  function compact(value) { return value.replace(/\s+/g, " ").trim(); }
  function translate(value) {
    const source = String(value ?? "");
    const trimmed = compact(source);
    if (!trimmed) return source;
    if (exact.has(trimmed)) return exact.get(trimmed);
    let output = source;
    for (const [zh, en] of phrases) output = output.split(zh).join(en);
    output = output
      .replace(/正在读取条件模型/g, "Loading reference model")
      .replace(/正在载入/g, "Loading")
      .replace(/共\s*(\d+)\s*项/g, "$1 metrics")
      .replace(/(\d+)\s*项(Poor|Needs work)/g, "$1 $2 metrics")
      .replace(/(\d+)\s*项/g, "$1 metrics")
      .replace(/第\s*(\d+)\s*场/g, "Match $1")
      .replace(/位置采样\s*([\d:]+)/g, "Position sample $1")
      .replace(/约每\s*60\s*秒/g, "roughly every 60 seconds");
    return output;
  }

  function translateElement(element) {
    if (!(element instanceof Element)) return;
    for (const attribute of ["placeholder", "title", "aria-label", "alt"]) {
      if (element.hasAttribute(attribute)) element.setAttribute(attribute, translate(element.getAttribute(attribute)));
    }
    for (const node of element.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
        const next = translate(node.nodeValue);
        if (next !== node.nodeValue) node.nodeValue = next;
      }
    }
  }

  function translateTree(root = document.body) {
    if (!root) return;
    if (root instanceof Element) translateElement(root);
    root.querySelectorAll?.("*").forEach(translateElement);
  }

  document.documentElement.lang = "en";
  document.title = "RiftScale · Champion-Matched Performance Review";
  const ready = () => {
    translateTree();
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
            const next = translate(node.nodeValue);
            if (next !== node.nodeValue) node.nodeValue = next;
          }
          else if (node instanceof Element) translateTree(node);
        });
        if (record.type === "characterData" && record.target.nodeValue.trim()) {
          const next = translate(record.target.nodeValue);
          if (next !== record.target.nodeValue) record.target.nodeValue = next;
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready, { once: true }); else ready();
})();
