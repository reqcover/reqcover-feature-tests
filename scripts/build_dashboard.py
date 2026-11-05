"""Builds dashboard/index.html and results/summary.md from results/results.json."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "results" / "results.json").read_text())
OUT = ROOT / "dashboard" / "index.html"
SCENARIOS = DATA["scenarios"]

EXPLANATIONS = {
    "parameterized-all-fail": "The @ParameterizedTest container finishes SUCCESSFUL even when every invocation fails; "
                              "the listener counts any SUCCESSFUL MethodSource execution, so the container alone "
                              "verifies the requirement.",
    "repeated-all-fail": "Same cause as @ParameterizedTest: the @RepeatedTest container is SUCCESSFUL although every "
                         "repetition failed.",
    "dynamic-all-fail": "Same cause: the @TestFactory method is SUCCESSFUL although every dynamic test failed "
                        "(dynamic tests have no MethodSource, so only the factory counts).",
    "below-minimum": "failBuild() calls exitProcess(1) before the reporters run, so no report is written exactly "
                     "when the coverage gate fails.",
    "no-config": "With no spec loaded, every annotated requirement is reported as not defined in the specification "
                 "right after the missing-configuration warning.",
}
SEVERITY = {"parameterized-all-fail": "critical", "repeated-all-fail": "critical", "dynamic-all-fail": "critical",
            "below-minimum": "serious", "no-config": "warning"}
ICON = {"good": "✔", "warning": "▲", "serious": "◆", "critical": "✖"}
LABEL = {"good": "Pass", "warning": "Warning", "serious": "Serious", "critical": "Critical"}

e = html.escape


def checks(s):
    return s["run"]["checks"]


def badge(status, text=None):
    return (f'<span class="badge {status}"><span aria-hidden="true">{ICON[status]}</span> '
            f'{e(text or LABEL[status])}</span>')


def pass_badge(ok):
    return badge("good", "Pass") if ok else badge("critical", "Fail")


def tiles():
    all_checks = [c for s in SCENARIOS for c in checks(s)]
    passed = sum(c["ok"] for c in all_checks)
    failing = [s for s in SCENARIOS if not all(c["ok"] for c in checks(s))]
    features = {f for s in SCENARIOS for f in s["features"]}
    seconds = sum(s["run"]["durationSeconds"] for s in SCENARIOS)
    items = [(f"{passed}/{len(all_checks)}", "checks passed", f"{passed / len(all_checks):.0%}"),
             (f"{len(SCENARIOS) - len(failing)}/{len(SCENARIOS)}", "scenarios fully passing",
              f"{len(failing)} with findings"),
             (str(len(features)), "features exercised", "JUnit Jupiter 6.1.3"),
             (f"{seconds:.0f}s", "total run time", f"{seconds / len(SCENARIOS):.1f}s per scenario")]
    return "".join(f'<div class="tile"><div class="tile-value">{e(v)}</div><div class="tile-label">{e(l)}</div>'
                   f'<div class="tile-sub">{e(s)}</div></div>' for v, l, s in items)


def findings():
    cards = []
    order = {"critical": 0, "serious": 1, "warning": 2}
    failing = [s for s in SCENARIOS if not all(c["ok"] for c in checks(s))]
    for s in sorted(failing, key=lambda s: order.get(SEVERITY.get(s["id"], "serious"), 1)):
        severity = SEVERITY.get(s["id"], "serious")
        failed = "".join(f'<li>{e(c["name"])}: expected <code>{e(str(c["expected"]))}</code>, got '
                         f'<code>{e(str(c["actual"]))[:160]}</code></li>' for c in checks(s) if not c["ok"])
        why = EXPLANATIONS.get(s["id"], "")
        cards.append(f'<article class="finding {severity}"><div class="finding-head">{badge(severity)}'
                     f'<h3>{e(s["title"])}</h3></div>{f"<p>{e(why)}</p>" if why else ""}<ul>{failed}</ul>'
                     f'<a href="#scenario-{s["id"]}">Scenario “{e(s["id"])}”</a></article>')
    return "".join(cards) or "<p>No findings: every check passed.</p>"


REPORT_CHECKS = {"XML report written": "XML report", "XML report: covered requirements": "XML report",
                 "XML report matches log": "XML report", "HTML report written": "HTML report",
                 "HTML report: lists every requirement": "HTML report"}


def feature_checks(feature):
    found, related = [], []
    for s in SCENARIOS:
        for c in checks(s):
            owner = REPORT_CHECKS.get(c["name"])
            if owner == feature or (owner is None and feature in s["features"]):
                found.append(c)
                if s not in related:
                    related.append(s)
    return found, related


def feature_matrix():
    features = sorted({f for s in SCENARIOS for f in s["features"]} | set(REPORT_CHECKS.values()))
    rows = []
    for feature in features:
        cs, related = feature_checks(feature)
        passed = sum(c["ok"] for c in cs)
        names = ", ".join(s["id"] for s in related)
        rows.append(f'<tr><th scope="row">{e(feature)}</th><td class="nowrap">{pass_badge(passed == len(cs))} '
                    f'<span class="muted">{passed}/{len(cs)}</span></td><td class="muted small">{e(names)}</td></tr>')
    return (f'<table class="grid"><thead><tr><th>Feature</th><th>Result</th><th>Scenarios</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def coverage_chart():
    data = [s for s in SCENARIOS if s["run"]["observed"]["coverage"] is not None]
    width, height = 860, 320
    left, right, top, bottom = 44, 12, 16, 104
    plot_w, plot_h = width - left - right, height - top - bottom
    step = plot_w / len(data)
    bar_w = min(26, step - 10)

    def y(v):
        return top + plot_h * (1 - v / 100)

    parts = []
    for tick in (0, 25, 50, 75, 100):
        parts.append(f'<line class="gridline" x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>'
                     f'<text class="axis" x="{left - 8}" y="{y(tick) + 4:.1f}" text-anchor="end">{tick}%</text>')
    for i, s in enumerate(data):
        obs = s["run"]["observed"]
        x = left + step * i + (step - bar_w) / 2
        h = max(plot_h * obs["coverage"] / 100, 0.5)
        r = min(4, bar_w / 2, h)
        y0 = top + plot_h
        path = (f"M{x:.1f},{y0:.1f} V{y0 - h + r:.1f} Q{x:.1f},{y0 - h:.1f} {x + r:.1f},{y0 - h:.1f} "
                f"H{x + bar_w - r:.1f} Q{x + bar_w:.1f},{y0 - h:.1f} {x + bar_w:.1f},{y0 - h + r:.1f} V{y0:.1f} Z")
        tip = f'{s["title"]}: {obs["covered"]}/{obs["total"]} = {obs["coverage"]:.1f}% · build {obs["build"]}'
        parts.append(f'<g class="bar" tabindex="0" data-tip="{e(tip)}"><rect class="hit" x="{x - 4:.1f}" y="{top}" '
                     f'width="{bar_w + 8:.1f}" height="{plot_h}"/><path class="s1" d="{path}"/></g>'
                     f'<text class="axis" transform="translate({x + bar_w / 2:.1f},{y0 + 12}) rotate(-40)" '
                     f'text-anchor="end">{e(s["id"])}</text>')
    parts.append(f'<line class="baseline" x1="{left}" x2="{width - right}" y1="{top + plot_h}" y2="{top + plot_h}"/>')
    return (f'<div class="chart-wrap"><svg viewBox="0 0 {width} {height}" role="img" aria-label="Requirements coverage '
            f'per scenario">{"".join(parts)}</svg><div class="tooltip" role="status" hidden></div></div>')


def heatmap():
    cols = [s for s in SCENARIOS if s["run"]["observed"]["xml"]]
    head = "".join(f'<th scope="col"><span class="vert">{e(s["id"])}</span></th>' for s in cols)
    rows = []
    for req in DATA["allRequirements"]:
        cells = []
        for s in cols:
            reqs = s["run"]["observed"]["xml"]["requirements"]
            if req not in reqs:
                cells.append('<td class="cell na" title="not in loaded spec">–</td>')
            elif reqs[req]:
                cells.append('<td class="cell good" title="covered"><span aria-hidden="true">✔</span>'
                             '<span class="sr">covered</span></td>')
            else:
                cells.append('<td class="cell critical" title="not covered"><span aria-hidden="true">✖</span>'
                             '<span class="sr">not covered</span></td>')
        rows.append(f'<tr><th scope="row"><code>{e(req)}</code></th>{"".join(cells)}</tr>')
    return (f'<div class="scroll"><table class="heat"><thead><tr><th>Requirement</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def details():
    groups = []
    for group in dict.fromkeys(s["group"] for s in SCENARIOS):
        blocks = []
        for s in [s for s in SCENARIOS if s["group"] == group]:
            run = s["run"]
            base = f'../results/{s["id"]}'
            links = [f'<a href="{base}/gradle.log">Gradle log</a>'] + [
                f'<a href="{base}/reports/requirements-coverage.{k}">{k.upper()} report</a>'
                for k in run["observed"]["reports"]]
            rows = "".join(f'<tr><td>{pass_badge(c["ok"])}</td><td>{e(c["name"])}</td>'
                           f'<td>{e(str(c["expected"]))}</td><td>{e(str(c["actual"]))}</td></tr>' for c in checks(s))
            passed = sum(c["ok"] for c in checks(s))
            blocks.append(f'<div class="run" id="scenario-{s["id"]}"><h4>{e(s["title"])} '
                          f'<span class="muted">· {e(s["id"])} · {passed}/{len(checks(s))} checks · '
                          f'{run["durationSeconds"]:.1f}s</span></h4><code class="cmd">{e(run["command"])}</code>'
                          f'<table class="checks"><thead><tr><th>Result</th><th>Check</th><th>Expected</th>'
                          f'<th>Actual</th></tr></thead><tbody>{rows}</tbody></table>'
                          f'<p class="links">{" · ".join(links)}</p></div>')
        groups.append(f'<h3 class="group">{e(group)}</h3><div class="runs">{"".join(blocks)}</div>')
    return "".join(groups)


CSS = """
.viz-root{color-scheme:light;--surface-0:#f4f3f0;--surface-1:#fcfcfb;--border:#e2e1dc;--grid:#ecebe7;
--text-primary:#0b0b0b;--text-secondary:#52514e;--text-muted:#76756f;--series-1:#2a78d6;
--good:#0ca30c;--warning:#fab219;--serious:#ec835a;--critical:#d03b3b;--na:#ecebe7}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;
--surface-0:#121211;--surface-1:#1a1a19;--border:#2e2e2b;--grid:#2a2a27;--text-primary:#f0efec;--text-secondary:#c3c2b7;
--text-muted:#9a998f;--series-1:#3987e5;--na:#262624}}
*{box-sizing:border-box}body{margin:0}
.viz-root{background:var(--surface-0);color:var(--text-primary);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
min-height:100vh;padding:28px clamp(16px,4vw,48px)}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}h3{font-size:15px;margin:0}h4{font-size:14px;margin:0 0 6px}
h3.group{margin:18px 0 8px}.muted{color:var(--text-muted);font-weight:400}.small{font-size:12px}
.sub{color:var(--text-secondary);margin:0 0 24px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:16px 18px}
.tile-value{font-size:30px;font-weight:650;font-variant-numeric:tabular-nums}.tile-label{color:var(--text-secondary)}
.tile-sub{color:var(--text-muted);font-size:12px}
.badge{display:inline-flex;gap:4px;align-items:center;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:600;
border:1.5px solid;white-space:nowrap;color:var(--text-primary)}.badge span{font-size:11px}
.badge.good{border-color:var(--good)}.badge.good span{color:var(--good)}
.badge.critical{border-color:var(--critical)}.badge.critical span{color:var(--critical)}
.badge.warning{border-color:var(--warning)}.badge.warning span{color:var(--warning)}
.badge.serious{border-color:var(--serious)}.badge.serious span{color:var(--serious)}
.findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.finding{border:1px solid var(--border);border-left:4px solid var(--border);border-radius:8px;padding:12px 14px}
.finding.critical{border-left-color:var(--critical)}.finding.serious{border-left-color:var(--serious)}
.finding.warning{border-left-color:var(--warning)}
.finding-head{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.finding p,.finding li{color:var(--text-secondary)}
.finding p{margin:8px 0}.finding ul{margin:6px 0;padding-left:18px;font-size:13px;overflow-wrap:anywhere}
a{color:var(--series-1)}code{font-size:12px}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
thead th{color:var(--text-secondary);font-weight:600;font-size:12px}
.cols{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:20px}@media (max-width:1100px){.cols{grid-template-columns:1fr}}
.chart-wrap{position:relative}svg{width:100%;height:auto;display:block}
.gridline{stroke:var(--grid);stroke-width:1}.baseline{stroke:var(--text-muted);stroke-width:1}
.axis{fill:var(--text-muted);font-size:11px}.s1{fill:var(--series-1)}.hit{fill:transparent}.bar{outline:none}
.bar:hover path,.bar:focus path{opacity:.8}
.tooltip{position:absolute;pointer-events:none;background:var(--surface-1);border:1px solid var(--border);border-radius:6px;
padding:6px 10px;font-size:12px;box-shadow:0 4px 14px rgb(0 0 0/.12);max-width:320px;color:var(--text-primary)}
.scroll{overflow-x:auto}.heat th,.heat td{border:2px solid var(--surface-1);padding:4px 6px;text-align:center}
.heat tbody th{text-align:left;white-space:nowrap}.heat thead th{vertical-align:bottom;font-size:11px}
.vert{writing-mode:vertical-rl;transform:rotate(180deg);display:inline-block;white-space:nowrap}
.cell{font-size:12px}.cell.good{background:color-mix(in srgb,var(--good) 22%,var(--surface-1))}
.cell.critical{background:color-mix(in srgb,var(--critical) 25%,var(--surface-1))}.cell.na{background:var(--na);color:var(--text-muted)}
.cell.good span[aria-hidden]{color:var(--good)}.cell.critical span[aria-hidden]{color:var(--critical)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.runs{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}
.run{border:1px solid var(--border);border-radius:8px;padding:12px}.cmd{display:block;color:var(--text-secondary);
margin-bottom:8px;overflow-wrap:anywhere}.checks td,.checks th{font-size:12px;padding:4px 6px;overflow-wrap:anywhere}
.links{margin:8px 0 0;font-size:12px}.nowrap{white-space:nowrap}
"""

JS = """
const wrap=document.querySelector('.chart-wrap'),tip=wrap.querySelector('.tooltip');
function show(el,x,y){tip.textContent=el.dataset.tip;tip.hidden=false;const r=wrap.getBoundingClientRect();
let left=Math.min(x-r.left+12,r.width-tip.offsetWidth-4);tip.style.left=Math.max(4,left)+'px';
tip.style.top=Math.max(0,y-r.top-40)+'px'}
wrap.querySelectorAll('.bar').forEach(b=>{b.addEventListener('pointermove',ev=>show(b,ev.clientX,ev.clientY));
b.addEventListener('pointerleave',()=>tip.hidden=true);b.addEventListener('focus',()=>{const r=b.getBoundingClientRect();
show(b,r.left+r.width/2,r.top)});b.addEventListener('blur',()=>tip.hidden=true)});
"""


def page():
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReqCover trunk feature tests</title><style>{CSS}</style></head>
<body><main class="viz-root">
<h1>ReqCover trunk feature tests</h1>
<p class="sub">reqcover {e(DATA["reqcoverVersion"])} · {e(DATA["reqcoverCommit"])} · JUnit Jupiter 6.1.3 ·
generated {e(DATA["generatedAt"])}</p>
<div class="tiles">{tiles()}</div>
<section class="card"><h2>Findings</h2><div class="findings">{findings()}</div></section>
<div class="cols">
<section class="card"><h2>Features</h2>{feature_matrix()}</section>
<section class="card"><h2>Requirements coverage per scenario</h2>{coverage_chart()}
<p class="muted">Hover or focus a bar for details. Scenarios without a coverage line (build aborted) are omitted.</p></section>
</div>
<section class="card"><h2>Requirement coverage from the XML reports</h2>
<p class="muted">One column per scenario that produced a report. ✔ covered · ✖ not covered · – not in the loaded spec.</p>
{heatmap()}</section>
<section class="card"><h2>Scenario details</h2>{details()}</section>
</main><script>{JS}</script></body></html>
"""


def summary():
    lines = [f"## ReqCover trunk feature tests — {DATA['reqcoverCommit']}", "",
             "| Group | Scenario | Checks | Build | Coverage |", "|---|---|---|---|---|"]
    for s in SCENARIOS:
        cs = checks(s)
        passed = sum(c["ok"] for c in cs)
        obs = s["run"]["observed"]
        cov = f'{obs["covered"]}/{obs["total"]}' if obs["total"] is not None else "–"
        lines.append(f'| {s["group"]} | {s["id"]} | {"✅" if passed == len(cs) else "❌"} {passed}/{len(cs)} '
                     f'| {obs["build"]} | {cov} |')
    failed = [(s, c) for s in SCENARIOS for c in checks(s) if not c["ok"]]
    if failed:
        lines += ["", "### Failed checks", ""] + [
            f'- **{s["id"]}**: {c["name"]} — expected `{c["expected"]}`, got `{str(c["actual"])[:120]}`'
            for s, c in failed]
    return "\n".join(lines) + "\n"


OUT.parent.mkdir(exist_ok=True)
OUT.write_text(page())
(ROOT / "results" / "summary.md").write_text(summary())
print(OUT)
