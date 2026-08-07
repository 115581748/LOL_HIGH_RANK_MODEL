(() => {
  const model = window.CONDITIONAL_MODEL || { meta: {}, dimensions: {}, profiles: {}, comparisonProfiles: {} };
  const playerCase = window.PLAYER_CASE || { meta: {}, summaries: {}, matches: [] };
  const $ = (id) => document.getElementById(id);
  const lateStartMinute = Number(model.meta?.parameters?.late_phase_start_minute || 25);

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
    late_champion_damage: "后期英雄伤害", late_damage_taken: "后期承伤", late_kills: "后期击杀", late_deaths: "后期死亡",
    late_assists: "后期助攻", late_teamfight_participation_rate: "后期团战参与率", late_first_target_deaths: "后期首个阵亡",
  };

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
    (model.phaseMetrics?.[phase] || []).forEach((metric) => {
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

  function heroBaselineKeys(match, phase) {
    const selectedBand = $("rankFilter").value;
    const bands = selectedBand === "ALL" ? ["ALL"] : [selectedBand, "ALL"];
    const candidates = [];
    bands.forEach((band) => {
      candidates.push(key(["CHAMPION_ALL_PATCH", "ALL", match.champion, match.position, band, phase]));
    });
    return candidates;
  }

  function resolveHeroBaseline(match, phase) {
    for (const candidate of heroBaselineKeys(match, phase)) {
      const profile = model.comparisonProfiles?.[candidate] || model.profiles?.[candidate];
      if (profile) return { value: profile };
    }
    return null;
  }

  function matchMetricCell(match, metric, profile) {
    const rawValue = match[metric];
    if (rawValue === null || rawValue === undefined || rawValue === "") return `<td class="comparison-metric missing">—</td>`;
    const value = Number(rawValue);
    if (!Number.isFinite(value)) return `<td class="comparison-metric missing">—</td>`;
    const stats = profile?.metrics?.[metric];
    if (!stats) return `<td class="comparison-metric"><b>${fmtMetric(metric, value)}</b><small>无同英雄基准</small></td>`;
    const gap = value - Number(stats.median);
    const percentile = approximatePercentile(value, stats);
    return `<td class="comparison-metric"><b>${fmtMetric(metric, value)}</b><small>基准 ${fmtMetric(metric, stats.median)}</small><em>${signedMetric(metric, gap)} · ${signedRelativeGap(value, stats.median)} · ${percentile == null ? "—" : `P${Math.round(percentile)}`}</em></td>`;
  }

  function renderMatchComparisons() {
    const phase = $("caseComparisonPhase").value;
    const metrics = model.phaseMetrics?.[phase] || [];
    const matches = playerCase.matches || [];
    $("matchComparisonHead").innerHTML = `<tr><th>场次</th><th>英雄 / 位置</th><th>结果</th><th>补丁</th><th>同英雄固定基准</th>${metrics.map((metric) => `<th title="${escapeHtml(metric)}">${escapeHtml(shortMetric(metric))}</th>`).join("")}</tr>`;
    let eligible = 0;
    let resolvedCount = 0;
    $("matchComparisonRows").innerHTML = matches.length ? matches.map((match) => {
      const reachedPhase = phase !== "LATE" || Number(match.durationMin) >= lateStartMinute;
      const resolved = reachedPhase ? resolveHeroBaseline(match, phase) : null;
      if (reachedPhase) eligible += 1;
      if (resolved) resolvedCount += 1;
      const baseline = !reachedPhase
        ? `<span class="no-baseline">未到 ${lateStartMinute} 分钟</span>`
        : resolved
          ? `<b>${escapeHtml(match.champion)} · ${escapeHtml(scopeNames[resolved.value.scope])}</b><small>n=${resolved.value.sampleSize} · ${escapeHtml(confidenceNames[resolved.value.confidence])} · ${escapeHtml(rankNames[resolved.value.rankBand] || resolved.value.rankBand)}</small>`
          : `<span class="no-baseline">无同英雄基准</span>`;
      return `<tr><td><b>${escapeHtml(match.matchRef)}</b><small>${fmt(match.durationMin)} 分钟</small></td><td><b>${escapeHtml(match.champion)}</b><small>${escapeHtml(positionNames[match.position] || match.position)}</small></td><td class="${match.win ? "win" : "loss"}">${match.win ? "胜" : "负"}</td><td><b>${escapeHtml(match.patch)}</b></td><td class="baseline-cell">${baseline}</td>${metrics.map((metric) => matchMetricCell(match, metric, resolved?.value)).join("")}</tr>`;
    }).join("") : `<tr><td class="empty" colspan="${metrics.length + 5}">尚未载入逐局案例数据。</td></tr>`;
    const phaseEligible = phase === "LATE" ? `达到 ${lateStartMinute} 分钟 ${eligible}/${matches.length} 场` : `${eligible} 场`;
    $("matchComparisonSummary").textContent = `${phaseNames[phase]} · ${phaseEligible} · 找到同英雄固定基准 ${resolvedCount}/${eligible || 0} 场 · 英雄与位置相同、跨版本合并 · 段位口径 ${rankNames[$("rankFilter").value]} · 去重后最低样本 ${model.meta.parameters?.comparison_minimum_samples || 3}`;
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
    const meta = playerCase.meta || {};
    $("caseMatches").textContent = Number(meta.rankedSoloMatches || 0);
    $("caseBottom").textContent = Number(meta.bottomMatches || 0);
    $("caseAshe").textContent = Number(meta.asheBottomMatches || 0);
    const ready = meta.status !== "WAITING_FOR_RIOT_KEY" && Number(meta.rankedSoloMatches) > 0;
    $("caseStatus").textContent = ready ? `Riot API 已载入 · ${meta.rankedSoloMatches} 场` : "等待有效 Riot Key";
    $("caseMessage").textContent = ready
      ? `艾希下路共 ${meta.asheBottomMatches} 场。上表差值统一按“玩家样本中位数 − 当前高分段基线中位数”计算，不附加主观定性。`
      : "尚未载入案例数据；提供有效 Key 后可重新生成。";
    const matches = playerCase.matches || [];
    $("recentMatches").innerHTML = matches.length ? matches.map((match) => `<tr><td>${escapeHtml(match.matchRef)}</td><td>${escapeHtml(match.champion)}</td><td>${escapeHtml(positionNames[match.position] || match.position)}</td><td class="${match.win ? "win" : "loss"}">${match.win ? "胜" : "负"}</td><td>${fmt(match.early_cs_15)}</td><td>${fmt(match.mid_cs_gain)}</td><td>${fmt(match.mid_champion_damage)}</td><td>${fmt(match.late_first_target_deaths)}</td></tr>`).join("") : `<tr><td class="empty" colspan="8">尚未载入逐局案例数据。</td></tr>`;
    renderMatchComparisons();
  }

  function render() {
    const phase = $("phaseFilter").value;
    const resolved = resolve(model.profiles || {}, phase);
    renderResolution(resolved);
    renderDistributions(resolved?.value);
    renderCorrelation(resolved?.value);
    renderStability(resolved?.value);
    renderMatchComparisons();
  }

  function populate() {
    const dimensions = model.dimensions || {};
    $("championFilter").innerHTML = (dimensions.champions || []).map((champion) => option(champion, champion, champion === "Ashe")).join("");
    $("positionFilter").innerHTML = (dimensions.positions || []).map((position) => option(position, positionNames[position] || position, position === "BOTTOM")).join("");
    $("patchFilter").innerHTML = (dimensions.patches || []).map((patch, index) => option(patch, patch, index === 0)).join("");
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
})();
