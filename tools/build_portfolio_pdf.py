"""Build the frozen RiftScale case study as a self-contained PDF."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "RiftScale_Case_Study.pdf"
BG, PANEL, LINE = colors.HexColor("#06131B"), colors.HexColor("#102630"), colors.HexColor("#29434D")
TEXT, MUTED, TEAL, GOLD, RED = colors.HexColor("#EDF6F7"), colors.HexColor("#9FB4BC"), colors.HexColor("#62DDD5"), colors.HexColor("#E8BB58"), colors.HexColor("#EF7B70")


def setup_fonts():
    pdfmetrics.registerFont(TTFont("Rift", "C:/Windows/Fonts/msyh.ttc", subfontIndex=0))
    pdfmetrics.registerFont(TTFont("RiftBold", "C:/Windows/Fonts/msyhbd.ttc", subfontIndex=0))


def stylebook():
    base = getSampleStyleSheet()
    return {
        "eye": ParagraphStyle("eye", parent=base["BodyText"], fontName="RiftBold", fontSize=8, leading=10, textColor=TEAL, spaceAfter=4),
        "title": ParagraphStyle("title", parent=base["Title"], fontName="RiftBold", fontSize=28, leading=35, textColor=TEXT, spaceAfter=8),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="RiftBold", fontSize=20, leading=25, textColor=TEXT, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="RiftBold", fontSize=11, leading=15, textColor=GOLD, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Rift", fontSize=9, leading=14, textColor=TEXT, spaceAfter=6),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Rift", fontSize=7.5, leading=11, textColor=MUTED),
        "number": ParagraphStyle("number", parent=base["BodyText"], fontName="RiftBold", fontSize=18, leading=22, textColor=GOLD, alignment=1),
    }


def box(rows, widths, padding=8):
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), .7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), .35, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding), ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding), ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return table


def chrome(canvas, doc):
    width, height = A4
    canvas.saveState(); canvas.setFillColor(BG); canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setStrokeColor(LINE); canvas.line(18*mm, 14*mm, width-18*mm, 14*mm)
    canvas.setFont("Rift", 7); canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 9*mm, "RIFTSCALE / 峡谷天平 · FROZEN CASE STUDY")
    canvas.drawRightString(width-18*mm, 9*mm, str(doc.page)); canvas.restoreState()


def clock(seconds):
    return f"{int(seconds)//60:02}:{int(seconds)%60:02}"


def fmt(value):
    value = float(value)
    return f"{value:,.0f}" if abs(value-round(value)) < .001 else f"{value:,.1f}"


def build():
    setup_fonts(); s = stylebook(); p = lambda text, key="body": Paragraph(text, s[key])
    data = json.loads((ROOT / "portfolio" / "demo.json").read_text(encoding="utf-8"))
    match, episode = data["match"], data["episode"]
    primary = next(item for item in episode["hypotheses"] if item["id"] == episode["primaryHypothesisId"])
    fact_map = {item["id"]: item for item in episode["facts"]}
    evidence = [fact_map[item] for item in primary["evidenceIds"] if item in fact_map]
    story = [Spacer(1,18*mm), p("LEAGUE OF LEGENDS · OCE · POST-GAME ANALYSIS","eye"),
             p("A result tells you who won.<br/><font color='#E8BB58'>Evidence tells you what to review.</font>","title"),
             p("RiftScale compares every performance with high-rank players on the same champion and role, then links review prompts to timestamped match observations."), Spacer(1,7*mm),
             box([[p(f"{int(data['sourceRows']):,}","number"),p("1 REAL MATCH","number"),p("60 SEC","number")],
                  [p("player-match benchmark records","small"),p("anonymous frozen case","small"),p("generated replay guide","small")]], [55*mm]*3),
             Spacer(1,12*mm),p("THE PRODUCT QUESTION","eye"),p("How good was this game, really?","h1"),
             box([[p("Traditional history","h2"),p("RiftScale review","h2")],[p("Win/loss, KDA and a long metric table. The player still has to guess what mattered."),p("Matched gaps, explicit rules and evidence that jumps back to the original moment.")]], [82.5*mm]*2),
             Spacer(1,12*mm),p("Your rank is one number. Your gameplay isn't.","h1"),p("This artifact demonstrates an evidence pipeline, not a validated causal model or an estimate of true rank.","small"),PageBreak()]

    story += [p("FIXED MATCH · CONCLUSION → EVIDENCE → REPLAY","eye"),p("What happened around this objective?","h1"),
              p(f"{match['champion']} vs {match['opponentChampion']} · {match['position']} · Patch {match['patch']} · {'Win' if match['win'] else 'Loss'} · {match['durationMin']:.1f} min"),
              box([[p("REVIEW PROMPT / 候选原因","eye")],[p(primary["title"],"h1")],[p("Rule-based hypothesis. Time order and correlation do not prove causation.","small")]], [165*mm]),Spacer(1,5*mm)]
    rows = [[p("Time","h2"),p("Observed evidence","h2"),p("Source","h2")]]
    for fact in evidence or episode["facts"][:3]:
        stamp = fact.get("timestamp", fact.get("sampleTimestamp", episode["eventSecond"]*1000))
        rows.append([p(clock(stamp/1000)),p(fact["label"]),p(fact.get("source","derived observation"),"small")])
    story += [box(rows,[20*mm,100*mm,45*mm],6),Spacer(1,5*mm),box([[Image(str(ROOT/"portfolio"/"replay-still.png"),92*mm,99*mm),p("<br/>".join(f"• {item['label']}" for item in episode["facts"]))]], [99*mm,66*mm]),
              Spacer(1,4*mm),p("Map markers are approximately one-minute position samples. Objective and kill events can have millisecond timestamps. Exact movement, alive state and wave state are not reconstructed.","small"),PageBreak()]

    story += [p("MATCHED BENCHMARKS","eye"),p("The match is compared with the right reference.","h1"),p("Every row uses the same champion and role. No other champion is used as fallback. n is the available D4+ player-match observation count."),]
    rows = [[p("Metric","h2"),p("This match","h2"),p("Median","h2"),p("Gap","h2"),p("n","h2"),p("Flag","h2")]]
    for metric in data["metrics"]:
        gap = metric["gap"]; flag = "Weak quartile" if metric["weak"] else "Within boundary"; color = "#EF7B70" if metric["weak"] else "#62DDD5"
        rows.append([p(metric["label"]),p(fmt(metric["value"])),p(fmt(metric["baseline"])),p(("+" if gap>0 else "")+fmt(gap)),p(str(metric["n"])),Paragraph(f"<font color='{color}'>{flag}</font>",s["small"])])
    story += [box(rows,[48*mm,25*mm,26*mm,23*mm,15*mm,28*mm],5),Spacer(1,8*mm),
              box([[p("How to read this","h2"),p("A weak-quartile flag identifies a match worth reviewing. It is not a grade, actual rank or proof that the metric caused the loss.")],
                   [p("Persistent weakness","h2"),p("Requires at least 5 eligible games, 3 weak-quartile observations and a weak fraction of at least 60%.")]], [43*mm,122*mm]),
              Spacer(1,10*mm),p("The player can challenge a specific claim.","h1"),p("Raw value, reference median, gap, sample count and original event replace a vague score. A strong farming result and weak survival result can coexist."),PageBreak()]

    stages=[("01","Riot Match + Timeline","Private collection and cache"),("02","Feature extraction","Phase metrics and event windows"),("03","Matched benchmarks","Champion × role distributions"),("04","Review engine","Explicit quartile and repetition rules"),("05","Frozen public export","Allowlisted anonymous fields"),("06","Evidence interface","Prompt → observation → replay")]
    story += [p("SYSTEM DESIGN","eye"),p("From private collection to a public, reproducible case.","h1"),p("The public artifact stays separate from credentials, raw identifiers and the complete dataset.")]
    for number,title,body in stages: story += [box([[p(number,"number"),[p(title,"h2"),p(body)]]],[24*mm,141*mm]),Spacer(1,3*mm)]
    story += [Spacer(1,4*mm),box([[p("FACT","eye"),p("ESTIMATE","eye"),p("DERIVED","eye")],[p("Objective, kill, item and ward event timestamps."),p("Position between snapshots and respawn timing."),p("Teamfight clusters and review hypotheses.")]], [55*mm]*3),PageBreak()]

    definitions=[("Exact matching","Same champion and role; at least 20 observations."),("Incomplete phases","Early needs 15 minutes, mid 25, late actual time after 25."),("Late rate","25+ damage and damage taken are divided by actual minutes after 25."),("Teamfight rule","At least 3 champion kills, consecutive gap no longer than 15 seconds."),("Cause language","Candidate reason or possible relationship, never proof from time order."),("Unavailable state","Riot does not provide real wave or jungle-camp state.")]
    story += [p("METHOD & LIMITS","eye"),p("Definitions that keep the result honest.","h1")]
    for title,body in definitions: story += [box([[p(title,"h2"),p(body)]],[45*mm,120*mm],7),Spacer(1,3*mm)]
    story += [Spacer(1,5*mm),p("NEXT VALIDATION","eye"),p("Have independent reviewers label the same frozen episodes, record agreement and disagreement, and test whether evidence-linked prompts improve later review accuracy."),Spacer(1,8*mm),
              box([[p("PUBLIC CASE STUDY","h2")],[Paragraph("<link href='https://115581748.github.io/LOL_HIGH_RANK_MODEL/portfolio/' color='#62DDD5'>115581748.github.io/LOL_HIGH_RANK_MODEL/portfolio/</link>",s["body"])],[p("GitHub: github.com/115581748/LOL_HIGH_RANK_MODEL","small")]], [165*mm]),Spacer(1,10*mm),p("Independent project. Not affiliated with Riot Games.","small")]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=19*mm, title="RiftScale / 峡谷天平 - Case Study", author="RiftScale")
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    print(OUTPUT)


if __name__ == "__main__":
    build()
