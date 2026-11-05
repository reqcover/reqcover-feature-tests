"""Runs every ReqCover (trunk) feature scenario with JUnit Jupiter and records the results.

Each scenario states the behaviour ReqCover *should* have. A failed check is either a bug or a gap.
Writes results/results.json, consumed by build_dashboard.py.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
REPORT_DIR = ROOT / "build" / "reports" / "tests" / "reqcover"
VERSION = os.environ.get("REQCOVER_VERSION") or ""
VERSION_ARGS = [f"-PreqcoverVersion={VERSION}"] if VERSION else []

ALL = [
    "#listBooks/200", "#getBook/200", "#getBook/404", "#ping",
    "#addBook/201/validIsbn", "#addBook/201/trimsTitle",
    "#addBook/400/blankTitle", "#addBook/400/invalidIsbn", "#addBook/409",
    "#deleteBook/204", "#deleteBook/404",
]
READ = ["#listBooks/200", "#getBook/200", "#getBook/404", "#ping"]
UNEXPECTED = ["#listBooks/500"]
MIN0 = "-PreqCoverMin=0"

SCENARIOS = [
    {"id": "baseline", "group": "Configuration",
     "title": "junit-platform.properties config, all requirements covered",
     "features": ["junit-platform.properties config", "OpenAPI operationId/response ids", "OpenAPI x-requirements ids",
                  "Operation without responses", "Operation without operationId skipped", "Multiple spec URIs",
                  "Repeated @ForRequirement", "Inherited test method", "@Nested test", "Auto-registration",
                  "XML report", "HTML report", "Unexpected requirements warning"],
     "args": [],
     "expect": {"build": "pass", "covered": 11, "total": 11, "uncovered": [], "unexpected": UNEXPECTED,
                "log": ["Operation ID not found for path '/legacy' and method 'get'"],
                "reports": ["xml", "html"], "xmlCovered": ALL, "htmlLists": ALL + UNEXPECTED}},
    {"id": "uri-list-format", "group": "Configuration",
     "title": "URI list with extra whitespace and blank entries",
     "features": ["Multiple spec URIs"],
     "args": ["-PrequirementsUris= books-read.yaml ,, books-write.yaml , "],
     "expect": {"build": "pass", "covered": 11, "total": 11}},
    {"id": "system-property-config", "group": "Configuration",
     "title": "Configuration through system properties only (no junit-platform.properties)",
     "features": ["System property config"],
     "args": ["-PnoConfigFile=true", "-PrequirementsUris=books-read.yaml,books-write.yaml", "-PreqCoverMin=100"],
     "expect": {"build": "pass", "covered": 11, "total": 11}},
    {"id": "single-spec", "group": "Configuration",
     "title": "Only one of the two specs configured",
     "features": ["Multiple spec URIs", "Unexpected requirements warning"],
     "args": ["-PrequirementsUris=books-read.yaml"],
     "expect": {"build": "pass", "covered": 4, "total": 4,
                "unexpected": [r for r in ALL if r not in READ] + UNEXPECTED, "xmlCovered": READ}},
    {"id": "classpath-merge", "group": "Configuration",
     "title": "Same spec name in main and test resources is merged",
     "features": ["Classpath spec merging"],
     "args": ["-PrequirementsUris=shared.yaml", MIN0],
     "expect": {"build": "pass", "covered": 0, "total": 2, "uncovered": ["#healthCheck/200", "#metrics/200"]}},
    {"id": "no-config", "group": "Configuration",
     "title": "No requirements spec configured",
     "features": ["Missing configuration warning"],
     "args": ["-PnoConfigFile=true"],
     "expect": {"build": "pass", "total": 0, "log": ["no requirements specification has been provided"],
                "unexpected": []}},
    {"id": "missing-spec", "group": "Configuration",
     "title": "Configured spec file does not exist",
     "features": ["Missing spec file fails build"],
     "args": ["-PrequirementsUris=does-not-exist.yaml"],
     "expect": {"build": "fail", "log": ["Requirements file not found at URI: does-not-exist.yaml"]}},
    {"id": "legacy-property", "group": "Configuration",
     "title": "Removed reqCover.requirementsUri property",
     "features": ["Legacy property rejection"],
     "args": ["-PlegacyRequirementsUri=books-read.yaml"],
     "expect": {"build": "fail", "log": ["reqCover.requirementsUri configuration parameter has been removed"]}},

    {"id": "below-minimum", "group": "Coverage gate",
     "title": "Coverage below the minimum fails the build",
     "features": ["Minimum coverage threshold", "Uncovered requirements warning"],
     "args": ["-PexcludeTags=deletion"],
     "expect": {"build": "fail", "covered": 9, "total": 11, "uncovered": ["#deleteBook/204", "#deleteBook/404"],
                "log": ["below the minimum required coverage of 100.0%"], "reports": ["xml", "html"]}},
    {"id": "fail-disabled", "group": "Coverage gate",
     "title": "failIfBelowMinimum=false keeps the build green",
     "features": ["failIfBelowMinimum"],
     "args": ["-PexcludeTags=deletion", "-PfailIfBelowMinimum=false"],
     "expect": {"build": "pass", "covered": 9, "total": 11, "log": ["below the minimum required coverage"]}},
    {"id": "lower-minimum", "group": "Coverage gate",
     "title": "Coverage just above a lowered minimum (81.8%)",
     "features": ["Minimum coverage threshold"],
     "args": ["-PexcludeTags=deletion", "-PreqCoverMin=81.8"],
     "expect": {"build": "pass", "covered": 9, "total": 11, "log": ["meets the minimum required coverage of 81.8%"]}},
    {"id": "unparseable-minimum", "group": "Coverage gate",
     "title": "Unparseable minimum is treated as 0%",
     "features": ["Minimum coverage threshold"],
     "args": ["-PexcludeTags=deletion", "-PreqCoverMin=lots"],
     "expect": {"build": "pass", "covered": 9, "total": 11, "log": ["meets the minimum required coverage of 0.0%"]}},

    {"id": "failing-test", "group": "Which tests count",
     "title": "A failing test does not verify its requirement",
     "features": ["Failed test not counted"],
     "args": ["-PbreakListBooks=true", MIN0],
     "expect": {"build": "fail", "covered": 10, "total": 11, "uncovered": ["#listBooks/200"]}},
    {"id": "aborted-test", "group": "Which tests count",
     "title": "An aborted test (failed assumption) does not verify its requirement",
     "features": ["Aborted test not counted", "Inherited test method"],
     "args": ["-PabortGetBook=true", MIN0],
     "expect": {"build": "pass", "covered": 10, "total": 11, "uncovered": ["#getBook/404"]}},
    {"id": "disabled-test", "group": "Which tests count",
     "title": "A disabled test does not verify its requirement",
     "features": ["Disabled test not counted"],
     "args": ["-PdisableBlankTitle=true", MIN0],
     "expect": {"build": "pass", "covered": 10, "total": 11, "uncovered": ["#addBook/400/blankTitle"]}},
    {"id": "parameterized-all-fail", "group": "Which tests count",
     "title": "@ParameterizedTest where every invocation fails",
     "features": ["@ParameterizedTest"],
     "args": ["-PbreakAllInvalidIsbn=true", MIN0],
     "expect": {"build": "fail", "covered": 10, "total": 11, "uncovered": ["#addBook/400/invalidIsbn"]}},
    {"id": "repeated-all-fail", "group": "Which tests count",
     "title": "@RepeatedTest where every repetition fails",
     "features": ["@RepeatedTest"],
     "args": ["-PbreakRepeated=true", MIN0],
     "expect": {"build": "fail", "covered": 10, "total": 11, "uncovered": ["#addBook/409"]}},
    {"id": "dynamic-all-fail", "group": "Which tests count",
     "title": "@TestFactory where every dynamic test fails",
     "features": ["@TestFactory"],
     "args": ["-PbreakDynamic=true", MIN0],
     "expect": {"build": "fail", "covered": 10, "total": 11, "uncovered": ["#addBook/201/validIsbn"]}},

    {"id": "no-reporters", "group": "Reports",
     "title": "No reporter on the classpath",
     "features": ["Missing reporter message"],
     "args": ["-PnoReporters=true"],
     "expect": {"build": "pass", "covered": 11, "total": 11,
                "log": ["No reporter configured"], "noReports": True}},
]

COVERAGE_LINE = re.compile(r"Requirements coverage: (\d+) out of (\d+) = ([\d.]+)%")
UNCOVERED_LINE = re.compile(r"not covered by any test: \[(.*?)\]")
UNEXPECTED_LINE = re.compile(r"not defined in the requirements specification: \[(.*?)\]")


def id_list(match):
    return sorted(x.strip() for x in match.group(1).split(",") if x.strip()) if match else []


def read_xml(path):
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    expected = root.find("expected")
    unexpected = root.find("unexpected")
    return {
        "coverage": float(root.get("coverage")),
        "covered": int(root.get("covered")),
        "total": int(root.get("total")),
        "requirements": {r.get("id"): r.get("covered") == "true" for r in (expected if expected is not None else [])},
        "unexpected": sorted(r.get("id") for r in (unexpected if unexpected is not None else [])),
    }


def observe(log, exit_code):
    coverage = COVERAGE_LINE.search(log)
    html = REPORT_DIR / "requirements-coverage.html"
    return {
        "build": "pass" if exit_code == 0 else "fail",
        "covered": int(coverage.group(1)) if coverage else None,
        "total": int(coverage.group(2)) if coverage else None,
        "coverage": float(coverage.group(3)) if coverage else None,
        "uncovered": id_list(UNCOVERED_LINE.search(log)),
        "unexpected": id_list(UNEXPECTED_LINE.search(log)),
        "reports": [k for k in ("xml", "html") if (REPORT_DIR / f"requirements-coverage.{k}").exists()],
        "xml": read_xml(REPORT_DIR / "requirements-coverage.xml"),
        "html": html.read_text() if html.exists() else None,
    }


def evaluate(expect, obs, log):
    checks = []

    def check(name, ok, expected, actual):
        checks.append({"name": name, "ok": bool(ok), "expected": expected, "actual": actual})

    def ids(values):
        return ", ".join(sorted(values)) or "none"

    check("Build outcome", obs["build"] == expect["build"], expect["build"], obs["build"])
    if "covered" in expect or "total" in expect:
        exp = f'{expect.get("covered", "*")}/{expect["total"]}'
        ok = obs["total"] == expect["total"] and ("covered" not in expect or obs["covered"] == expect["covered"])
        check("Coverage", ok, exp, f'{obs["covered"]}/{obs["total"]}' if obs["total"] is not None else "no coverage line")
    if "uncovered" in expect:
        check("Uncovered requirements", obs["uncovered"] == sorted(expect["uncovered"]),
              ids(expect["uncovered"]), ids(obs["uncovered"]))
    if "unexpected" in expect:
        check("Unexpected requirements", obs["unexpected"] == sorted(expect["unexpected"]),
              ids(expect["unexpected"]), ids(obs["unexpected"]))
    for needle in expect.get("log", []):
        check("Log message", needle in log, needle, "found" if needle in log else "not found")
    for kind in expect.get("reports", []):
        check(f"{kind.upper()} report written", kind in obs["reports"], "written",
              "written" if kind in obs["reports"] else "missing")
    if expect.get("noReports"):
        check("No report files", not obs["reports"], "none", ids(obs["reports"]))
    if "xmlCovered" in expect:
        xml_covered = sorted(r for r, c in (obs["xml"] or {}).get("requirements", {}).items() if c)
        check("XML report: covered requirements", xml_covered == sorted(expect["xmlCovered"]),
              ids(expect["xmlCovered"]), ids(xml_covered) if obs["xml"] else "no XML report")
    if "htmlLists" in expect:
        missing = [r for r in expect["htmlLists"] if not obs["html"] or r not in obs["html"]]
        check("HTML report: lists every requirement", not missing, "all listed",
              "all listed" if not missing else "missing " + ids(missing))
    if obs["xml"] and obs["total"] is not None:
        check("XML report matches log", (obs["xml"]["covered"], obs["xml"]["total"]) == (obs["covered"], obs["total"]),
              f'{obs["covered"]}/{obs["total"]}', f'{obs["xml"]["covered"]}/{obs["xml"]["total"]}')
    return checks


def run(scenario):
    shutil.rmtree(REPORT_DIR, ignore_errors=True)
    command = ["./gradlew", "test", "--console=plain", *VERSION_ARGS, *scenario["args"]]
    started = time.monotonic()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    duration = time.monotonic() - started
    log = process.stdout + process.stderr
    target = RESULTS / scenario["id"]
    target.mkdir(parents=True, exist_ok=True)
    (target / "gradle.log").write_text(log)
    if REPORT_DIR.exists():
        shutil.copytree(REPORT_DIR, target / "reports", dirs_exist_ok=True)
    obs = observe(log, process.returncode)
    checks = evaluate(scenario["expect"], obs, log)
    passed = sum(c["ok"] for c in checks)
    print(f'{scenario["id"]:24} {passed}/{len(checks)} checks  {duration:5.1f}s', flush=True)
    obs.pop("html")
    return {"command": " ".join(command), "exitCode": process.returncode,
            "durationSeconds": round(duration, 2), "observed": obs, "checks": checks}


def main():
    shutil.rmtree(RESULTS, ignore_errors=True)
    RESULTS.mkdir()
    subprocess.run(["./gradlew", "testClasses", "-q", *VERSION_ARGS], cwd=ROOT, check=True, stdin=subprocess.DEVNULL)
    results = [{**s, "run": run(s)} for s in SCENARIOS]
    commit_file = ROOT / ".reqcover-commit"
    (RESULTS / "results.json").write_text(json.dumps({
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reqcoverVersion": VERSION or "(gradle.properties default)",
        "reqcoverCommit": commit_file.read_text().strip() if commit_file.exists() else "unknown",
        "allRequirements": ALL,
        "scenarios": results,
    }, indent=2))
    checks = [c for s in results for c in s["run"]["checks"]]
    print(f'\n{sum(c["ok"] for c in checks)}/{len(checks)} checks passed')
    return 0


if __name__ == "__main__":
    sys.exit(main())
