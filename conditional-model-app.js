(() => {
  const model = window.CONDITIONAL_MODEL || { meta: {}, dimensions: {}, profiles: {}, comparisonProfiles: {} };
  const playerCase = window.PLAYER_CASE || { meta: {}, summaries: {}, matches: [] };
  const playerReplays = window.PLAYER_REPLAYS || {};
  const $ = (id) => document.getElementById(id);
  const lateStartMinute = Number(model.meta?.parameters?.late_phase_start_minute || 25);
  const playerServiceBase = "api/player-case";
  const loadedRevision = String(window.MODEL_MANIFEST?.revision || "");
  const replayUi = { matchRef: null, second: 0, timer: null, itemData: {} };

  const phaseNames = { EARLY: "前期 0–15", MID: `中期 15–${lateStartMinute}`, LATE: `后期 ${lateStartMinute}+` };
  const rankNames = { ALL: "D4+ 整体", DIAMOND_IV_II: "Diamond IV–II", DIAMOND_I: "Diamond I", MASTER_PLUS: "Master+" };
  const positionNames = { TOP: "上路", JUNGLE: "打野", MIDDLE: "中路", BOTTOM: "下路", UTILITY: "辅助" };
  const scopeNames = { EXACT: "英雄 × 位置 × 版本", CHAMPION_ALL_PATCH: "英雄 × 位置 × 跨版本", ROLE_PATCH: "位置 × 版本", ROLE_ALL: "位置 × 跨版本" };
  const confidenceNames = { HIGH: "高置信度", MEDIUM: "中等置信度", LOW: "低置信度" };
  const metricNames = {
    early_gold_15: "15 分钟经济增长", early_xp_15: "15 分钟经验", early_cs_15: "15 分钟 CS",
    early_kills: "前期击杀", early_deaths: "前期死亡", early_assists: "前期助攻",
    mid_gold_gain: "中期经济增长", mid_cs_gain: "中期 CS 增长", mid_champion_damage: "中期英雄伤害",
    mid_kills: "中期击杀", mid_deaths: "中期死亡", mid_assists: "中期助攻", mid_team_turrets: "中期团队塔", mid_team_dragons: "中期团队龙",
    late_champion_damage_per_min: "25 分钟后每分钟英雄伤害", late_damage_taken_per_min: "25 分钟后每分钟承伤", late_kills: "后期击杀", late_deaths: "后期死亡",
    late_assists: "后期助攻", late_teamfight_participation_rate: "后期团战参与率", late_first_target_deaths: "后期首个阵亡",
  };
  Object.assign(metricNames, {
    early_gold_diff_vs_enemy_jungle: "15 分钟对位经济差",
    early_xp_diff_vs_enemy_jungle: "15 分钟对位经验差",
    early_cs_diff_vs_enemy_jungle: "15 分钟对位 CS 差",
    early_gank_takedowns: "前 15 分钟有效 Gank",
    early_gank_lanes: "前 15 分钟影响路线数",
    early_first_gank_minute: "首次有效 Gank 分钟",
    early_enemy_jungle_takedowns: "前 15 分钟对敌方打野击杀参与",
    early_kill_participation_rate: "前 15 分钟团队击杀参与率",
    early_team_dragons: "前 15 分钟团队小龙",
    early_team_void_grubs: "前 15 分钟团队虚空巢虫",
    early_team_rift_heralds: "前 15 分钟团队峡谷先锋",
    early_personal_epic_secures: "前 15 分钟个人史诗野怪击杀",
    early_gank_takedown_diff_vs_enemy_jungle: "有效 Gank 对位差",
    early_epic_monster_diff_vs_enemy_jungle: "史诗野怪对位差",
    mid_gank_takedowns: "中期有效 Gank",
    mid_gank_lanes: "中期影响路线数",
    mid_first_gank_minute: "中期首次有效 Gank 分钟",
    mid_enemy_jungle_takedowns: "中期对敌方打野击杀参与",
    mid_kill_participation_rate: "中期团队击杀参与率",
    mid_team_void_grubs: "中期团队虚空巢虫",
    mid_team_rift_heralds: "中期团队峡谷先锋",
    mid_personal_epic_secures: "中期个人史诗野怪击杀",
    mid_gank_takedown_diff_vs_enemy_jungle: "中期有效 Gank 对位差",
    mid_epic_monster_diff_vs_enemy_jungle: "中期史诗野怪对位差",
  });

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }

  function fmt(value) {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const absolute = Math.abs(number);
    if (absolute >= 10000) return `${(number / 1000).toFixed(1)}k`;
    if (absolute >= 1000) return number.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
    return number.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  }

  function fmtMetric(metric, value) {
    if (metric.includes("rate") && Number.isFinite(Number(value))) return `${(Number(value) * 100).toFixed(1)}%`;
    return fmt(value);
  }

  function option(value, label, selected = false) {
    return `<option value="${escapeHtml(value)}"${selected ? " selected" : ""}>${escapeHtml(label)}</option>`;
  }

  function key(parts) { return parts.join("|"); }

  function metricsForPhase(phase, position) {
    return [
      ...(model.phaseMetrics?.[phase] || []),
      ...(model.positionPhaseMetrics?.[position]?.[phase] || []),
    ];
  }

  function candidateKeys(phase) {
    const patch = $("patchFilter").value;
    const champion = $("championFilter").value;
    const position = $("positionFilter").value;
    const selectedBand = $("rankFilter").value;
    const bands = selectedBand === "ALL" ? ["ALL"] : [selectedBand, "ALL"];
    const candidates = [];
    bands.forEach((band) => {
      candidates.push(key(["EXACT", patch, champion, position, band, phase]));
      candidates.push(key(["CHAMPION_ALL_PATCH", "ALL", champion, position, band, phase]));
      candidates.push(key(["ROLE_PATCH", patch, "ALL", position, band, phase]));
      candidates.push(key(["ROLE_ALL", "ALL", "ALL", position, band, phase]));
    });
    return candidates;
  }

  function resolve(collection, phase) {
    for (const candidate of candidateKeys(phase)) {
      if (collection[candidate]) return { key: candidate, value: collection[candidate] };
    }
    return null;
  }

  function playerSummary(phase) {
    const champion = $("championFilter").value;
    const position = $("positionFilter").value;
    const patch = $("patchFilter").value;
    const rows = (playerCase.matches || []).filter((match) => (
      match.champion === champion
      && match.position === position
      && match.patch === patch
      && (phase !== "LATE" || Number(match.durationMin) >= lateStartMinute)
    ));
    if (!rows.length) return null;
    const metrics = {};
    metricsForPhase(phase, position).forEach((metric) => {
      const values = rows
        .map((row) => row[metric])
        .filter((value) => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value)))
        .map(Number)
        .sort((a, b) => a - b);
      if (!values.length) return;
      const middle = Math.floor(values.length / 2);
      metrics[metric] = { n: values.length, median: values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2 };
    });
    return { sampleSize: rows.length, metrics };
  }

  function signedMetric(metric, value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const sign = number > 0 ? "+" : number < 0 ? "−" : "";
    if (metric.includes("rate")) return `${sign}${Math.abs(number * 100).toFixed(1)}pp`;
    return `${sign}${fmtMetric(metric, Math.abs(number))}`;
  }

  function relativeGap(value, baseline) {
    const player = Number(value);
    const reference = Number(baseline);
    if (!Number.isFinite(player) || !Number.isFinite(reference) || Math.abs(reference) < 1e-9) return null;
    return (player - reference) / Math.abs(reference) * 100;
  }

  function signedRelativeGap(value, baseline) {
    const gap = relativeGap(value, baseline);
    if (gap == null) return "基线为 0";
    return `${gap > 0 ? "+" : ""}${gap.toFixed(1)}%`;
  }

  function heroBaselineKeys(match, phase, side = "player") {
    const selectedBand = $("rankFilter").value;
    const bands = selectedBand === "ALL" ? ["ALL"] : [selectedBand, "ALL"];
    const champion = side === "opponent" ? match.opponentChampion : match.champion;
    const position = side === "opponent" ? match.opponentPosition : match.position;
    if (!champion || !position) return [];
    const candidates = [];
    bands.forEach((band) => {
      candidates.push(key(["CHAMPION_ALL_PATCH", "ALL", champion, position, band, phase]));
    });
    return candidates;
  }

  function resolveHeroBaseline(match, phase, side = "player") {
    for (const candidate of heroBaselineKeys(match, phase, side)) {
      const profile = model.comparisonProfiles?.[candidate] || model.profiles?.[candidate];
      if (profile) return { value: profile };
    }
    return null;
  }

  function matchMetricCell(match, metric, playerProfile, opponentProfile) {
    const playerValue = Number(match[metric]);
    const opponentValue = Number(match[`opponent_${metric}`]);
    const hasPlayer = match[metric] !== null && match[metric] !== undefined && match[metric] !== "" && Number.isFinite(playerValue);
    const hasOpponent = match[`opponent_${metric}`] !== null && match[`opponent_${metric}`] !== undefined && match[`opponent_${metric}`] !== "" && Number.isFinite(opponentValue);
    if (!hasPlayer && !hasOpponent) return `<td class="comparison-metric missing">—</td>`;
    const playerStats = playerProfile?.metrics?.[metric];
    const opponentStats = opponentProfile?.metrics?.[metric];
    const headToHead = hasPlayer && hasOpponent ? signedMetric(metric, playerValue - opponentValue) : "—";
    const playerGap = hasPlayer && playerStats ? signedMetric(metric, playerValue - Number(playerStats.median)) : "—";
    const opponentGap = hasOpponent && opponentStats ? signedMetric(metric, opponentValue - Number(opponentStats.median)) : "—";
    const playerPercentile = hasPlayer && playerStats ? approximatePercentile(playerValue, playerStats) : null;
    const opponentPercentile = hasOpponent && opponentStats ? approximatePercentile(opponentValue, opponentStats) : null;
    return `<td class="comparison-metric"><b><span>你 ${hasPlayer ? fmtMetric(metric, playerValue) : "—"}</span><span>对 ${hasOpponent ? fmtMetric(metric, opponentValue) : "—"}</span></b><small>基准 · 你 ${playerStats ? fmtMetric(metric, playerStats.median) : "—"} · 对 ${opponentStats ? fmtMetric(metric, opponentStats.median) : "—"}</small><em><span>对位差 ${headToHead}</span><span>你/基准 ${playerGap} · ${playerPercentile == null ? "—" : `P${Math.round(playerPercentile)}`}</span><span>对/基准 ${opponentGap} · ${opponentPercentile == null ? "—" : `P${Math.round(opponentPercentile)}`}</span></em></td>`;
  }

  function renderMatchComparisons() {
    const phase = $("caseComparisonPhase").value;
    const metrics = metricsForPhase(phase, playerCase.meta?.primaryPosition);
    const matches = playerCase.matches || [];
    $("matchComparisonHead").innerHTML = `<tr><th>场次</th><th>你 / 对位</th><th>结果</th><th>补丁</th><th>双方英雄固定基准</th>${metrics.map((metric) => `<th title="${escapeHtml(metric)}">${escapeHtml(shortMetric(metric))}</th>`).join("")}</tr>`;
    let eligible = 0;
    let playerResolvedCount = 0;
    let opponentResolvedCount = 0;
    $("matchComparisonRows").innerHTML = matches.length ? matches.map((match) => {
      const reachedPhase = phase !== "LATE" || Number(match.durationMin) >= lateStartMinute;
      const playerResolved = reachedPhase ? resolveHeroBaseline(match, phase, "player") : null;
      const opponentResolved = reachedPhase ? resolveHeroBaseline(match, phase, "opponent") : null;
      if (reachedPhase) eligible += 1;
      if (playerResolved) playerResolvedCount += 1;
      if (opponentResolved) opponentResolvedCount += 1;
      const baselineLine = (label, champion, resolved) => resolved
        ? `<span><strong>${label} ${escapeHtml(champion)}</strong><small>n=${resolved.value.sampleSize} · ${escapeHtml(confidenceNames[resolved.value.confidence])} · ${escapeHtml(rankNames[resolved.value.rankBand] || resolved.value.rankBand)}</small></span>`
        : `<span class="no-baseline">${label} ${escapeHtml(champion || "未知")}：无基准</span>`;
      const baseline = !reachedPhase
        ? `<span class="no-baseline">未到 ${lateStartMinute} 分钟</span>`
        : `${baselineLine("你", match.champion, playerResolved)}${baselineLine("对", match.opponentChampion, opponentResolved)}`;
      return `<tr><td><b>${escapeHtml(match.matchRef)}</b><small>${fmt(match.durationMin)} 分钟</small></td><td><b>${escapeHtml(match.champion)} <i>vs</i> ${escapeHtml(match.opponentChampion || "未知")}</b><small>${escapeHtml(positionNames[match.position] || match.position)}</small></td><td class="${match.win ? "win" : "loss"}">${match.win ? "胜" : "负"}</td><td><b>${escapeHtml(match.patch)}</b></td><td class="baseline-cell">${baseline}</td>${metrics.map((metric) => matchMetricCell(match, metric, playerResolved?.value, opponentResolved?.value)).join("")}</tr>`;
    }).join("") : `<tr><td class="empty" colspan="${metrics.length + 5}">尚未载入逐局案例数据。</td></tr>`;
    const phaseEligible = phase === "LATE" ? `达到 ${lateStartMinute} 分钟 ${eligible}/${matches.length} 场` : `${eligible} 场`;
    $("matchComparisonSummary").textContent = `${phaseNames[phase]} · ${phaseEligible} · 你的英雄基准 ${playerResolvedCount}/${eligible || 0} 场 · 对手英雄基准 ${opponentResolvedCount}/${eligible || 0} 场 · 同英雄同位置、跨版本 · 段位口径 ${rankNames[$("rankFilter").value]} · 去重后最低样本 ${model.meta.parameters?.comparison_minimum_samples || 3}`;
  }

  function approximatePercentile(value, stats) {
    if (!Number.isFinite(Number(value)) || !stats) return null;
    const points = [[stats.p10, 10], [stats.p25, 25], [stats.median, 50], [stats.p75, 75], [stats.p90, 90]];
    const numeric = Number(value);
    if (numeric === points[0][0]) return points[0][1];
    if (numeric < points[0][0]) return Math.max(0, points[0][1] - points[0][1] * (points[0][0] - numeric) / (Math.abs(points[0][0]) || 1));
    if (numeric >= points[points.length - 1][0]) return Math.min(100, 90 + 10 * (numeric - points[4][0]) / (Math.abs(points[4][0]) + 1));
    for (let index = 1; index < points.length; index += 1) {
      if (numeric <= points[index][0]) {
        const [lowValue, lowPct] = points[index - 1];
        const [highValue, highPct] = points[index];
        const ratio = (numeric - lowValue) / (highValue - lowValue || 1);
        return lowPct + ratio * (highPct - lowPct);
      }
    }
    return null;
  }

  function renderResolution(resolved) {
    if (!resolved) {
      $("resolutionPanel").innerHTML = `<span class="scope">无可用模型</span><span class="path">当前条件及回退层级都不足 ${model.meta.parameters?.minimum_group_samples || 20} 条。</span><span class="confidence">—</span>`;
      return;
    }
    const profile = resolved.value;
    const requested = `${$("championFilter").value} · ${positionNames[$("positionFilter").value]} · ${$("patchFilter").value} · ${rankNames[$("rankFilter").value]}`;
    const actual = `${scopeNames[profile.scope]}${profile.rankBand === "ALL" ? " · D4+整体" : ` · ${rankNames[profile.rankBand]}`}`;
    $("resolutionPanel").innerHTML = `<span class="scope">${escapeHtml(scopeNames[profile.scope])}</span><span class="path">请求：${escapeHtml(requested)}<br>实际：${escapeHtml(actual)} · n=${profile.sampleSize}</span><span class="confidence">${escapeHtml(confidenceNames[profile.confidence])}</span>`;
  }

  function renderDistributions(profile) {
    if (!profile) {
      $("distributionRows").innerHTML = `<tr><td class="empty" colspan="11">当前条件没有达到最低样本要求。</td></tr>`;
      $("distributionCount").textContent = "0 个指标";
      return;
    }
    const summary = playerSummary(profile.phase);
    const rows = Object.entries(profile.metrics || {});
    $("distributionCount").textContent = `${rows.length} 个指标 · n=${profile.sampleSize}`;
    $("distributionRows").innerHTML = rows.map(([metric, stats]) => {
      const playerStats = summary?.metrics?.[metric];
      const playerValue = playerStats?.median;
      const percentile = approximatePercentile(playerValue, stats);
      const gap = playerStats ? Number(playerValue) - Number(stats.median) : null;
      const gapRate = playerStats ? relativeGap(playerValue, stats.median) : null;
      const gapDetail = gapRate == null ? "基线为 0，未算比例" : `${gapRate > 0 ? "+" : ""}${gapRate.toFixed(1)}%`;
      return `<tr><td class="metric-name"><b>${escapeHtml(metricNames[metric] || metric)}</b><code>${escapeHtml(metric)}</code></td><td>${stats.n}<br><small>${(stats.missingRate * 100).toFixed(0)}% 缺失</small></td><td>${fmtMetric(metric, stats.p10)}</td><td>${fmtMetric(metric, stats.p25)}</td><td>${fmtMetric(metric, stats.median)}</td><td>${fmtMetric(metric, stats.p75)}</td><td>${fmtMetric(metric, stats.p90)}</td><td>${fmtMetric(metric, stats.mad)}</td><td class="player-value">${playerStats ? `${fmtMetric(metric, playerValue)}<br><small>n=${summary.sampleSize}</small>` : "—"}</td><td class="gap-value">${playerStats ? `${signedMetric(metric, gap)}<br><small>${gapDetail}</small>` : "—"}</td><td class="percentile">${percentile == null ? "—" : `P${Math.round(percentile)}`}</td></tr>`;
    }).join("");
  }

  function correlationColor(value) {
    const alpha = Math.min(.72, .08 + Math.abs(value) * .62);
    return value >= 0 ? `rgba(99,230,226,${alpha})` : `rgba(239,125,112,${alpha})`;
  }

  function shortMetric(metric) {
    return (metricNames[metric] || metric).replace("15 分钟", "15分").replace("中期", "").replace("后期", "");
  }

  function renderCorrelation(profile) {
    const metrics = profile?.correlationMetrics || [];
    if (!metrics.length) {
      $("correlationMatrix").innerHTML = `<div class="empty">没有足够的成对数值。</div>`;
      return;
    }
    const columns = metrics.length + 1;
    let html = `<div class="correlation-grid" style="grid-template-columns:110px repeat(${metrics.length},minmax(58px,1fr))"><div></div>${metrics.map((metric) => `<div class="corr-label">${escapeHtml(shortMetric(metric))}</div>`).join("")}`;
    metrics.forEach((metric, rowIndex) => {
      html += `<div class="corr-label row">${escapeHtml(shortMetric(metric))}</div>`;
      profile.correlation[rowIndex].forEach((value, columnIndex) => {
        html += `<div class="corr-cell" style="background:${correlationColor(value)}" title="${escapeHtml(metric)} × ${escapeHtml(metrics[columnIndex])}">${Number(value).toFixed(2)}</div>`;
      });
    });
    html += "</div>";
    $("correlationMatrix").innerHTML = html;
  }

  function renderStability(profile) {
    const stability = profile?.stability;
    if (!stability?.available) {
      $("stabilityRate").textContent = "样本不足";
      $("stabilityList").innerHTML = `<div class="empty">无法完成前后时间切分。</div>`;
      return;
    }
    $("stabilityRate").textContent = `${(stability.stableMetricRate * 100).toFixed(0)}% 指标稳定`;
    $("stabilityList").innerHTML = stability.metrics.map((item) => `<div class="stability-row"><span>${escapeHtml(metricNames[item.metric] || item.metric)}</span><b>${fmtMetric(item.metric, item.earlierMedian)}</b><i></i><b>${fmtMetric(item.metric, item.recentMedian)}</b><span class="${item.stable ? "stable" : "shift"}">${item.stable ? "稳定" : `位移 ${item.normalizedShift.toFixed(2)} IQR`}</span></div>`).join("");
  }

  function renderCase() {
    renderReview();
    const meta = playerCase.meta || {};
    const riotId = String(meta.riotId || "Geolonwe#OC");
    const separator = riotId.lastIndexOf("#");
    const gameName = separator >= 0 ? riotId.slice(0, separator) : riotId;
    const tagLine = separator >= 0 ? riotId.slice(separator + 1) : "OC";
    const primaryPosition = meta.primaryPosition || "—";
    const primaryChampion = meta.primaryChampion || "—";
    $("casePlayerLink").textContent = `${riotId} ↗`;
    $("casePlayerLink").href = `https://op.gg/lol/summoners/oce/${encodeURIComponent(`${gameName}-${tagLine}`)}`;
    $("caseMatches").textContent = Number(meta.rankedSoloMatches || 0);
    $("casePrimaryPositionLabel").textContent = primaryPosition === "—" ? "主位置" : positionNames[primaryPosition] || primaryPosition;
    $("casePrimaryPositionMatches").textContent = Number(meta.primaryPositionMatches || 0);
    $("casePrimaryChampionLabel").textContent = primaryChampion === "—" ? "主英雄" : primaryChampion;
    $("casePrimaryChampionMatches").textContent = Number(meta.primaryChampionPositionMatches || 0);
    const ready = meta.status !== "WAITING_FOR_RIOT_KEY" && Number(meta.rankedSoloMatches) > 0;
    $("caseStatus").textContent = ready ? `Riot API 已载入 · ${meta.rankedSoloMatches} 场` : "等待有效 Riot Key";
    $("caseMessage").textContent = ready
      ? `${primaryChampion} ${positionNames[primaryPosition] || primaryPosition}共 ${meta.primaryChampionPositionMatches} 场。上表差值统一按“玩家样本中位数 − 当前高分段基线中位数”计算，不附加主观定性。`
      : "尚未载入案例数据；提供有效 Key 后可重新生成。";
    const matches = playerCase.matches || [];
    $("recentMatches").innerHTML = matches.length ? matches.map((match) => `<tr data-match-ref="${escapeHtml(match.matchRef)}"><td>${escapeHtml(match.matchRef)}</td><td><b>${escapeHtml(match.champion)}</b><small>vs ${escapeHtml(match.opponentChampion || "未知")}</small></td><td>${escapeHtml(positionNames[match.position] || match.position)}</td><td class="${match.win ? "win" : "loss"}">${match.win ? "胜" : "负"}</td><td>${fmt(match.early_cs_15)}</td><td>${fmt(match.mid_cs_gain)}</td><td>${fmt(match.mid_champion_damage)}</td><td>${fmt(match.late_first_target_deaths)}</td></tr>`).join("") : `<tr><td class="empty" colspan="8">尚未载入逐局案例数据。</td></tr>`;
    renderMatchComparisons();
  }

  function renderReview() {
    const report = playerCase.diagnosis || {};
    const findings = report.findings || [];
    const recurring = findings.filter((item) => item.recurring);
    const latest = Number(report.latestGameStartMs);
    $("reviewFreshness").textContent = Number.isFinite(latest) ? `最近样本 ${new Date(latest).toLocaleDateString("zh-CN")}` : "没有有效样本";
    $("reviewHeadline").textContent = recurring.length
      ? `发现 ${recurring.length} 项达到重复弱项规则。先处理反复出现、而且能回到具体比赛核对的差距。`
      : `最近 ${Number(report.games || 0)} 场没有指标达到重复弱项阈值；下面仍保留偶发差距，但不把它们包装成稳定问题。`;
    $("reviewBoundary").textContent = report.boundary || "这里只给出复盘提示，不证明输因，也不等于实际段位。";
    if (!findings.length) {
      $("reviewFindings").innerHTML = `<article class="review-empty">当前没有满足同英雄同位置和最低样本量要求的可比指标。</article>`;
      return;
    }
    $("reviewFindings").innerHTML = findings.map((finding, index) => {
      const ratio = finding.eligible ? finding.weakCount / finding.eligible * 100 : 0;
      const badge = finding.recurring ? "重复弱项" : finding.weakCount ? "偶发差距" : "未触及弱四分位";
      const rows = finding.evidence.map((row) => `<tr class="${row.weak ? "weak" : ""}"><td>${new Date(row.gameStartMs).toLocaleDateString("zh-CN")}</td><td>${escapeHtml(row.champion)} · ${row.win ? "胜" : "负"}</td><td>${fmtMetric(finding.metric, row.value)}</td><td>${fmtMetric(finding.metric, row.baseline)}</td><td>${signedMetric(finding.metric, row.gap)}</td><td>n=${row.n}</td></tr>`).join("");
      return `<details class="review-card ${finding.recurring ? "recurring" : ""}"${index === 0 ? " open" : ""}><summary><div><span class="review-badge">${badge}</span><h3>${escapeHtml(finding.label)}</h3><p>${finding.weakCount}/${finding.eligible} 场落入弱四分位 · ${finding.belowCount}/${finding.eligible} 场弱于中位数</p></div><strong>${ratio.toFixed(0)}%</strong></summary><div class="review-meter"><i style="width:${Math.max(0, Math.min(100, ratio))}%"></i></div><p class="review-action">下一步：${escapeHtml(finding.action)}</p><div class="table-wrap"><table class="metric-table review-table"><thead><tr><th>比赛</th><th>英雄 / 胜负</th><th>本局</th><th>基准中位数</th><th>差距</th><th>基准样本</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
    }).join("");
  }

  function replayEvents(replay) {
    return (replay?.frames || []).flatMap((frame) => frame.events || []).sort((a, b) => Number(a.timestamp || 0) - Number(b.timestamp || 0));
  }

  function replayClock(second) {
    const safe = Math.max(0, Math.floor(Number(second) || 0));
    return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
  }

  function frameAtSecond(replay, second) {
    const frames = replay?.frames || [];
    if (!frames.length) return null;
    let frame = frames[0];
    for (const candidate of frames) {
      if (Number(candidate.timestamp || 0) > second * 1000) break;
      frame = candidate;
    }
    return frame;
  }

  function estimatedRespawnSeconds(level, gameSecond) {
    const base = [10, 10, 12, 12, 14, 16, 20, 25, 28, 30, 32, 35, 37, 40, 42, 45, 48, 52];
    const safeLevel = Math.max(1, Math.min(18, Number(level) || 1));
    const progress = Math.min(1, Math.max(0, (gameSecond - 900) / 2400));
    return Math.max(1, Math.round(base[safeLevel - 1] * (1 + 0.5 * progress)));
  }

  function deathStatesAt(replay, second) {
    const states = {};
    replayEvents(replay).forEach((event) => {
      const eventSecond = Math.floor(Number(event.timestamp || 0) / 1000);
      if (eventSecond > second) return;
      if (event.type === "CHAMPION_RESPAWN") {
        delete states[Number(event.participantId || 0)];
        return;
      }
      if (event.type !== "CHAMPION_KILL") return;
      const participantId = Number(event.victimId || 0);
      const sampled = frameAtSecond(replay, eventSecond)?.players?.find((row) => Number(row.participantId) === participantId) || {};
      const respawnAt = eventSecond + estimatedRespawnSeconds(sampled.level, eventSecond);
      states[participantId] = { position: event.position || sampled, respawnAt, remaining: Math.max(0, respawnAt - second) };
    });
    Object.keys(states).forEach((id) => { if (states[id].respawnAt <= second) delete states[id]; });
    return states;
  }

  function replayItemState(replay, second) {
    const state = {};
    const remove = (participantId, itemId) => {
      const items = state[participantId] || [];
      const index = items.lastIndexOf(Number(itemId));
      if (index >= 0) items.splice(index, 1);
    };
    replayEvents(replay).forEach((event) => {
      if (Number(event.timestamp || 0) > second * 1000) return;
      const participantId = Number(event.participantId || 0);
      if (!participantId) return;
      state[participantId] ||= [];
      if (event.type === "ITEM_PURCHASED") state[participantId].push(Number(event.itemId));
      if (["ITEM_SOLD", "ITEM_DESTROYED"].includes(event.type)) remove(participantId, event.itemId);
      if (event.type === "ITEM_UNDO") {
        remove(participantId, event.beforeId);
        if (Number(event.afterId || 0)) state[participantId].push(Number(event.afterId));
      }
    });
    return state;
  }

  function combatState(replay, second) {
    const rows = Object.fromEntries((replay.players || []).map((player) => [player.participantId, { kills: 0, deaths: 0, assists: 0 }]));
    replayEvents(replay).forEach((event) => {
      if (event.type !== "CHAMPION_KILL" || Number(event.timestamp || 0) > second * 1000) return;
      if (rows[event.killerId]) rows[event.killerId].kills += 1;
      if (rows[event.victimId]) rows[event.victimId].deaths += 1;
      (event.assistingParticipantIds || []).forEach((id) => { if (rows[id]) rows[id].assists += 1; });
    });
    return rows;
  }

  function teamfights(replay) {
    const kills = replayEvents(replay).filter((event) => event.type === "CHAMPION_KILL");
    const groups = [];
    kills.forEach((event) => {
      const previous = groups.at(-1)?.at(-1);
      if (!previous || Number(event.timestamp) - Number(previous.timestamp) > 15000) groups.push([event]);
      else groups.at(-1).push(event);
    });
    return groups.filter((group) => group.length >= 3).map((group, index) => ({
      id: `tf-${index}`,
      start: Math.floor(Number(group[0].timestamp) / 1000),
      end: Math.floor(Number(group.at(-1).timestamp) / 1000),
      kills: group.length,
      events: group,
    }));
  }

  function eventLabel(event, replay) {
    const player = (id) => replay.players?.find((row) => Number(row.participantId) === Number(id))?.champion || `P${id}`;
    if (event.type === "CHAMPION_KILL") return `${player(event.killerId)} 击杀 ${player(event.victimId)}`;
    if (event.type === "ELITE_MONSTER_KILL") return `${player(event.killerId)} 取得 ${event.monsterSubType || event.monsterType || "史诗野怪"}`;
    if (event.type === "BUILDING_KILL") return `${event.laneType || "地图"} ${event.towerType || event.buildingType || "建筑"} 被摧毁`;
    if (event.type === "WARD_PLACED") return `${player(event.creatorId)} 插眼`;
    if (event.type === "WARD_KILL") return `${player(event.killerId)} 排眼`;
    if (event.type === "ITEM_PURCHASED") return `${player(event.participantId)} 购买装备`;
    return event.type || "事件";
  }

  function renderReplayMap(replay) {
    const frame = frameAtSecond(replay, replayUi.second);
    const deaths = deathStatesAt(replay, replayUi.second);
    const playerMap = Object.fromEntries((replay.players || []).map((player) => [player.participantId, player]));
    const match = (playerCase.matches || []).find((row) => row.matchRef === replayUi.matchRef) || {};
    const focusId = (replay.players || []).find((player) => player.champion === match.champion && player.position === match.position)?.participantId;
    $("replayClock").textContent = replayClock(replayUi.second);
    $("replaySample").textContent = frame ? `位置采样 ${replayClock(Number(frame.timestamp || 0) / 1000)} · 事件精确到秒` : "无位置样本";
    $("replayTimeline").value = replayUi.second;
    $("replayMarkers").innerHTML = (frame?.players || []).map((sample) => {
      const player = playerMap[sample.participantId] || {};
      const death = deaths[sample.participantId];
      const position = death?.position || sample;
      const left = Math.max(0, Math.min(100, Number(position.x || 0) / 15000 * 100));
      const top = Math.max(0, Math.min(100, 100 - Number(position.y || 0) / 15000 * 100));
      const title = `${player.champion || sample.participantId} · Lv${sample.level}${death ? ` · 已阵亡，预计 ${death.remaining}s 后复活` : ""}`;
      return `<button class="replay-marker team-${player.teamId}${Number(sample.participantId) === Number(focusId) ? " focus" : ""}${death ? " dead" : ""}" style="left:${left}%;top:${top}%" title="${escapeHtml(title)}"><img src="assets/ddragon/16.15.1/champion/${escapeHtml(player.champion)}.png" alt="${escapeHtml(player.champion)}"><span>${sample.level || ""}</span></button>`;
    }).join("");
    const nearby = replayEvents(replay).filter((event) => Math.abs(Number(event.timestamp || 0) / 1000 - replayUi.second) <= 2 && event.position?.x != null);
    $("replayEventMarkers").innerHTML = nearby.map((event) => `<span class="replay-map-event" style="left:${Number(event.position.x) / 15000 * 100}%;top:${100 - Number(event.position.y) / 15000 * 100}%" title="${escapeHtml(eventLabel(event, replay))}">◆</span>`).join("");
  }

  function itemIcon(itemId) {
    const item = replayUi.itemData[String(itemId)];
    if (!item?.image) return `<span class="replay-item unknown" title="物品 ${itemId}">${itemId}</span>`;
    const image = item.image;
    return `<span class="replay-item" title="${escapeHtml(item.name || itemId)}" style="background-image:url('assets/ddragon/16.15.1/sprite/${escapeHtml(image.sprite)}');background-position:-${Number(image.x) / 2}px -${Number(image.y) / 2}px"></span>`;
  }

  function renderReplayTeams(replay) {
    const frame = frameAtSecond(replay, replayUi.second);
    const samples = Object.fromEntries((frame?.players || []).map((row) => [row.participantId, row]));
    const combat = combatState(replay, replayUi.second);
    const items = replayItemState(replay, replayUi.second);
    const deaths = deathStatesAt(replay, replayUi.second);
    [100, 200].forEach((teamId) => {
      const target = teamId === 100 ? $("replayBlueTeam") : $("replayRedTeam");
      target.innerHTML = (replay.players || []).filter((player) => Number(player.teamId) === teamId).map((player) => {
        const sample = samples[player.participantId] || {};
        const kda = combat[player.participantId] || {};
        const death = deaths[player.participantId];
        return `<div class="replay-tab-row${death ? " dead" : ""}"><img src="assets/ddragon/16.15.1/champion/${escapeHtml(player.champion)}.png" alt=""><div><b>${escapeHtml(player.champion)}</b><small>${escapeHtml(positionNames[player.position] || player.position)} · Lv${sample.level || "—"}${death ? ` · ☠ 预计 ${death.remaining}s` : ""}</small></div><strong>${kda.kills || 0}/${kda.deaths || 0}/${kda.assists || 0}</strong><span>${Number(sample.minions || 0) + Number(sample.jungleMinions || 0)} CS</span><span>${Number(sample.totalGold || 0).toLocaleString("zh-CN")}g</span><div class="replay-items">${(items[player.participantId] || []).slice(-7).map(itemIcon).join("")}</div></div>`;
      }).join("");
    });
  }

  function renderReplayEvents(replay) {
    const events = replayEvents(replay).filter((event) => Math.abs(Number(event.timestamp || 0) / 1000 - replayUi.second) <= 12).slice(-8);
    $("replayEventFeed").innerHTML = events.length ? events.map((event) => `<button type="button" data-seek="${Math.floor(Number(event.timestamp || 0) / 1000)}"><time>${replayClock(Number(event.timestamp || 0) / 1000)}</time><span>${escapeHtml(eventLabel(event, replay))}</span></button>`).join("") : `<span>当前时间点前后 12 秒没有离散事件。</span>`;
    $("replayEventFeed").querySelectorAll("[data-seek]").forEach((button) => button.addEventListener("click", () => seekReplay(Number(button.dataset.seek))));
  }

  function renderReplayInsights(replay) {
    const cards = [];
    (replay.objectiveAnalyses || []).forEach((analysis) => {
      const hypothesis = (analysis.hypotheses || []).find((row) => row.id === analysis.primaryHypothesisId);
      const evidence = (analysis.facts || []).filter((fact) => (hypothesis?.evidenceIds || []).includes(fact.id));
      cards.push({ second: analysis.eventSecond, title: `${analysis.objectiveName}丢失 · 候选原因`, text: hypothesis?.title || "未找到足够证据", detail: evidence.map((fact) => `${fact.label}（${fact.source}）`).join("；"), confidence: hypothesis ? `${hypothesis.grade} · ${Math.round(Number(hypothesis.confidence || 0) * 100)}% 启发式置信` : "证据不足" });
    });
    teamfights(replay).forEach((fight) => cards.push({ second: fight.start, title: `派生团战 ${replayClock(fight.start)}–${replayClock(fight.end)}`, text: `${fight.kills} 次英雄击杀被规则聚类`, detail: "相邻击杀≤15秒且总击杀≥3；保留 CHAMPION_KILL 原始证据。", confidence: "规则事件，不是 Riot 官方标签" }));
    cards.sort((a, b) => a.second - b.second);
    $("replayInsights").innerHTML = cards.length ? cards.map((card) => `<button type="button" class="replay-insight" data-seek="${card.second}"><time>${replayClock(card.second)}</time><div><b>${escapeHtml(card.title)}</b><strong>${escapeHtml(card.text)}</strong><small>${escapeHtml(card.detail)}</small><em>${escapeHtml(card.confidence)}</em></div></button>`).join("") : `<div class="empty">本局没有符合规则的团战或目标丢失候选原因。</div>`;
    $("replayInsights").querySelectorAll("[data-seek]").forEach((button) => button.addEventListener("click", () => seekReplay(Number(button.dataset.seek))));
  }

  function renderReplay() {
    const replay = playerReplays[replayUi.matchRef];
    if (!replay) return;
    renderReplayMap(replay);
    renderReplayTeams(replay);
    renderReplayEvents(replay);
  }

  function seekReplay(second) {
    const replay = playerReplays[replayUi.matchRef];
    replayUi.second = Math.max(0, Math.min(Number(replay?.durationSeconds || 0), Math.round(Number(second) || 0)));
    renderReplay();
  }

  function selectReplay(matchRef) {
    const replay = playerReplays[matchRef];
    if (!replay) return;
    replayUi.matchRef = matchRef;
    $("replayMatchSelect").value = matchRef;
    $("replayTimeline").max = Number(replay.durationSeconds || 1);
    replayUi.second = Math.min(900, Number(replay.durationSeconds || 0));
    renderReplayInsights(replay);
    renderReplay();
  }

  function initReplay() {
    const refs = (playerCase.matches || []).map((match) => match.matchRef).filter((ref) => playerReplays[ref]);
    $("replayMatchSelect").innerHTML = refs.map((ref) => {
      const match = (playerCase.matches || []).find((row) => row.matchRef === ref) || {};
      return option(ref, `${ref} · ${match.champion || "未知"} · ${match.win ? "胜" : "负"}`);
    }).join("");
    if (!refs.length) {
      $("replayMatchSelect").innerHTML = option("", "没有可用回放");
      $("replayInsights").innerHTML = `<div class="empty">查询玩家后会生成赛后 Timeline 回放。</div>`;
      return;
    }
    $("replayMatchSelect").addEventListener("change", (event) => selectReplay(event.target.value));
    $("replayTimeline").addEventListener("input", (event) => seekReplay(event.target.value));
    $("replayStart").addEventListener("click", () => seekReplay(0));
    $("replayEnd").addEventListener("click", () => seekReplay(playerReplays[replayUi.matchRef]?.durationSeconds || 0));
    $("replayBack").addEventListener("click", () => seekReplay(replayUi.second - 10));
    $("replayForward").addEventListener("click", () => seekReplay(replayUi.second + 10));
    $("replayPlay").addEventListener("click", () => {
      if (replayUi.timer) {
        clearInterval(replayUi.timer); replayUi.timer = null; $("replayPlay").textContent = "播放"; return;
      }
      $("replayPlay").textContent = "暂停";
      replayUi.timer = window.setInterval(() => {
        const duration = Number(playerReplays[replayUi.matchRef]?.durationSeconds || 0);
        if (replayUi.second >= duration) { clearInterval(replayUi.timer); replayUi.timer = null; $("replayPlay").textContent = "播放"; return; }
        seekReplay(replayUi.second + 1);
      }, 250);
    });
    fetch("assets/item-data.json").then((response) => response.json()).then((payload) => { replayUi.itemData = payload.data || {}; renderReplay(); }).catch(() => {});
    selectReplay(refs[0]);
    $("recentMatches").querySelectorAll("tr[data-match-ref]").forEach((row) => row.addEventListener("click", () => { selectReplay(row.dataset.matchRef); $("webReplayTitle").scrollIntoView({ behavior: "smooth" }); }));
  }

  function setPlayerServiceState(message, state = "checking") {
    const target = $("playerServiceState");
    if (!target) return;
    target.dataset.state = state;
    target.querySelector("span").textContent = message;
  }

  function setPlayerControlsEnabled(enabled) {
    $("playerSwitchButton").disabled = !enabled;
    $("playerRefreshButton").disabled = !enabled;
  }

  function setPlayerServiceAvailable(available) {
    $("apiKeySaveButton").disabled = !available;
  }

  async function readPlayerServiceStatus() {
    try {
      const response = await fetch(`${playerServiceBase}/status?refresh=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const status = await response.json();
      setPlayerServiceAvailable(true);
      if (!$("playerRiotId").value && status.currentRiotId) $("playerRiotId").value = status.currentRiotId;
      const keyExpired = Boolean(status.lastError && /401|apikey/i.test(status.lastError));
      const usable = Boolean(status.canRefresh) && !status.busy && !keyExpired;
      setPlayerControlsEnabled(usable);
      if (status.busy) {
        setPlayerServiceState("正在拉取玩家数据或补建英雄基准…", "busy");
      } else if (!status.canRefresh) {
        setPlayerServiceState("本地服务在线，但服务端没有 RIOT_API_KEY。", "error");
      } else if (status.lastError) {
        setPlayerServiceState(keyExpired ? "安全服务在线，但 Riot API Key 已失效。" : `上次自动更新失败：${status.lastError}`, "error");
      } else {
        setPlayerServiceState(`安全更新服务在线 · 每 ${status.autoRefreshMinutes} 分钟自动检查`, "online");
      }
      if (status.revision && loadedRevision && status.revision !== loadedRevision) {
        setPlayerServiceState("检测到玩家数据更新，正在重新载入页面…", "busy");
        window.setTimeout(() => window.location.reload(), 350);
      }
      return true;
    } catch (error) {
      setPlayerControlsEnabled(false);
      setPlayerServiceAvailable(false);
      setPlayerServiceState("当前为静态只读站；从本地安全服务打开此页即可切换玩家。", "offline");
      return false;
    }
  }

  async function saveApiKey() {
    const input = $("playerApiKey");
    const apiKey = input.value.trim();
    if (!apiKey) throw new Error("请输入 RGAPI- 开头的 Riot API Key。");
    setPlayerServiceState("正在把 API Key 保存到本机…", "busy");
    const response = await fetch(`${playerServiceBase}/key`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apiKey }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    input.value = "";
    setPlayerControlsEnabled(true);
    setPlayerServiceState("API Key 已仅保存在本机，可以查询任意 Riot ID。", "online");
    return result;
  }

  async function updatePlayerCase(action, riotId = null) {
    setPlayerControlsEnabled(false);
    setPlayerServiceState(action === "switch" ? "正在切换玩家并检查英雄基准…" : "正在检查当前玩家的新对局…", "busy");
    try {
      const response = await fetch(`${playerServiceBase}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(riotId ? { riotId } : {}),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      if (result.changed) {
        setPlayerServiceState(`${result.riotId} 已更新，正在重新载入…`, "online");
        window.setTimeout(() => window.location.reload(), 350);
      } else {
        setPlayerServiceState(`${result.riotId} 已是最新数据，没有发现新对局。`, "online");
        setPlayerControlsEnabled(true);
      }
    } catch (error) {
      setPlayerServiceState(`更新失败：${error.message}`, "error");
      setPlayerControlsEnabled(true);
    }
  }

  function initPlayerControls() {
    $("playerSwitchForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const riotId = $("playerRiotId").value.trim();
      if (!riotId) {
        setPlayerServiceState("请输入玩家名#TAG。", "error");
        return;
      }
      try {
        if ($("playerApiKey").value.trim()) await saveApiKey();
        await updatePlayerCase("switch", riotId);
      } catch (error) {
        setPlayerServiceState(`查询失败：${error.message}`, "error");
        setPlayerControlsEnabled(true);
      }
    });
    $("apiKeySaveButton").addEventListener("click", async () => {
      try { await saveApiKey(); }
      catch (error) { setPlayerServiceState(`保存失败：${error.message}`, "error"); }
    });
    $("playerRefreshButton").addEventListener("click", () => updatePlayerCase("refresh"));
    readPlayerServiceStatus().then((available) => {
      if (available) window.setInterval(readPlayerServiceStatus, 30_000);
    });
  }

  function render() {
    const phase = $("phaseFilter").value;
    $("jungleMetricNote").hidden = $("positionFilter").value !== "JUNGLE";
    const resolved = resolve(model.profiles || {}, phase);
    renderResolution(resolved);
    renderDistributions(resolved?.value);
    renderCorrelation(resolved?.value);
    renderStability(resolved?.value);
    renderMatchComparisons();
  }

  function populate() {
    const dimensions = model.dimensions || {};
    const defaultChampion = playerCase.meta?.primaryChampion || "Ashe";
    const defaultPosition = playerCase.meta?.primaryPosition || "BOTTOM";
    const patchCounts = {};
    (playerCase.matches || []).forEach((match) => { patchCounts[match.patch] = (patchCounts[match.patch] || 0) + 1; });
    const defaultPatch = Object.entries(patchCounts)
      .filter(([patch]) => (dimensions.patches || []).includes(patch))
      .sort((left, right) => right[1] - left[1])[0]?.[0] || (dimensions.patches || [])[0];
    $("championFilter").innerHTML = (dimensions.champions || []).map((champion) => option(champion, champion, champion === defaultChampion)).join("");
    $("positionFilter").innerHTML = (dimensions.positions || []).map((position) => option(position, positionNames[position] || position, position === defaultPosition)).join("");
    $("patchFilter").innerHTML = (dimensions.patches || []).map((patch) => option(patch, patch, patch === defaultPatch)).join("");
    $("rankFilter").innerHTML = (dimensions.rankBands || []).map((band) => option(band, rankNames[band] || band, band === "ALL")).join("");
    $("phaseFilter").innerHTML = (dimensions.phases || []).map((phase) => option(phase, phaseNames[phase] || phase, phase === "EARLY")).join("");
    $("caseComparisonPhase").innerHTML = (dimensions.phases || []).map((phase) => option(phase, phaseNames[phase] || phase, phase === "EARLY")).join("");
    ["championFilter", "positionFilter", "patchFilter", "rankFilter", "phaseFilter"].forEach((id) => $(id).addEventListener("change", render));
    $("caseComparisonPhase").addEventListener("change", renderMatchComparisons);
  }

  $("sourceRows").textContent = Number(model.meta?.sourceRows || 0).toLocaleString("zh-CN");
  $("profileCount").textContent = Number(model.meta?.profileCount || 0).toLocaleString("zh-CN");
  $("comparisonProfileCount").textContent = Number(model.meta?.comparisonProfileCount || 0).toLocaleString("zh-CN");
  $("minimumSamples").textContent = Number(model.meta?.parameters?.minimum_group_samples || 0);
  $("modelLoadState").textContent = `模型已载入 · ${Number(model.meta?.profileCount || 0).toLocaleString("zh-CN")} 个条件分布`;
  populate();
  renderCase();
  render();
  initReplay();
  initPlayerControls();
})();
