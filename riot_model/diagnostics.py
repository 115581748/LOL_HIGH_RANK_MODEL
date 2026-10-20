"""Evidence-led review priorities shared by desktop and public exports."""
import math


METRICS = {
    "early_cs_15": ("EARLY", "15 分钟补刀", False, "回看 15 分钟前漏掉的兵线或空转时间，找一次可避免的资源损失。"),
    "early_gold_15": ("EARLY", "15 分钟经济", False, "对照补刀和死亡，确认经济差来自哪里，再选择一个可改变的环节。"),
    "early_deaths": ("EARLY", "前期死亡", True, "逐次检查死亡前的位置和已知敌人信息，记录一次可以提前撤退的时机。"),
    "early_gank_takedowns": ("EARLY", "前期有效 Gank", False, "回看前 15 分钟路线与队友交战时机；这里只统计参与击杀非打野目标。"),
    "mid_cs_gain": ("MID", "15–25 分钟补刀增长", False, "检查转线、回城和等待团战之间是否有可安全获取的资源。"),
    "mid_deaths": ("MID", "中期死亡", True, "回看死亡前是否缺少队友支援或敌人位置，记录可改变的进场条件。"),
    "late_champion_damage_per_min": ("LATE", "25+ 每分钟英雄伤害", False, "先检查到场、存活和可攻击时间，再判断是否存在输出机会浪费。"),
    "vision_per_min": ("FULL", "全场视野分/分钟", False, "辅助复盘下一次资源争夺前的视野布置；得分本身不代表眼位质量。"),
}


def finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def review_report(matches, profiles, minimum_samples=20, minimum_games=5, repeat_fraction=0.6):
    """Return transparent quartile review prompts, never causal conclusions."""
    unique, seen = [], set()
    for match in sorted(matches, key=lambda m: finite(m.get("gameStartMs")) or 0, reverse=True):
        identity = finite(match.get("gameStartMs"))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        unique.append(match)
    findings = []
    for metric, (phase, label, lower, action) in METRICS.items():
        evidence = []
        for match in unique:
            duration = finite(match.get("durationMin"))
            if duration is None or (phase == "EARLY" and duration < 15) or (phase == "MID" and duration < 25) or (phase == "LATE" and duration <= 25):
                continue
            if metric == "early_gank_takedowns" and match.get("position") != "JUNGLE":
                continue
            if phase == "FULL" and match.get("position") != "UTILITY":
                continue
            profile = profiles.get(f"{match.get('champion')}|{match.get('position')}|{'EARLY' if phase == 'FULL' else phase}", {})
            stats = profile.get("metrics", {}).get(metric, {})
            n = finite(stats.get("n"))
            value, median = finite(match.get(metric)), finite(stats.get("median"))
            p25, p75 = finite(stats.get("p25")), finite(stats.get("p75"))
            boundary = p75 if lower else p25
            if n is None or n < minimum_samples or value is None or median is None or boundary is None:
                continue
            if p25 is None or p75 is None or not p25 <= median <= p75:
                continue
            weak = value > boundary if lower else value < boundary
            below = value > median if lower else value < median
            evidence.append({
                "matchRef": match.get("matchRef"), "gameStartMs": match["gameStartMs"],
                "champion": match.get("champion"), "position": match.get("position"),
                "win": bool(match.get("win")), "value": value, "baseline": median,
                "gap": value - median, "n": int(n), "weak": weak, "below": below,
                "boundary": boundary, "patch": match.get("patch"),
            })
        if not evidence:
            continue
        weak_count = sum(e["weak"] for e in evidence)
        below_count = sum(e["below"] for e in evidence)
        recurring = len(evidence) >= minimum_games and weak_count >= 3 and weak_count / len(evidence) >= repeat_fraction
        findings.append({
            "metric": metric, "phase": phase, "label": label, "lowerIsBetter": lower,
            "eligible": len(evidence), "weakCount": weak_count, "belowCount": below_count,
            "recurring": recurring, "action": action, "evidence": evidence,
        })
    findings.sort(key=lambda f: (f["recurring"], f["weakCount"] / f["eligible"], f["belowCount"] / f["eligible"]), reverse=True)
    return {
        "version": 1, "games": len(unique),
        "latestGameStartMs": unique[0].get("gameStartMs") if unique else None,
        "minimumSamples": minimum_samples, "minimumGames": minimum_games,
        "repeatFraction": repeat_fraction, "findings": findings,
        "boundary": "同英雄同位置 D4+ 跨版本参考；差距提示复盘方向，不证明输因，也不等于实际段位。",
    }
