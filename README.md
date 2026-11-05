# ReqCover feature tests (trunk, JUnit Jupiter)

Fresh Gradle project that tests every feature of ReqCover's `trunk` branch with JUnit Jupiter, using a local
`publishToMavenLocal` build (the HTML reporter fix `805bb09` and the missing-spec fix `7ee94d2` are not released yet).

## Run

Requires JDK 21+, Python 3 and `make`. Run `make help` for all targets.

```bash
make all       # build ReqCover trunk into ~/.m2, run every scenario, build the dashboard
make open      # open dashboard/index.html
```

```bash
make publish-reqcover                       # REQCOVER_REF=trunk by default; any branch, tag or commit works
make test                                   # one run with the default config (junit-platform.properties)
make test ARGS="-PexcludeTags=deletion"     # one run with switches
make report                                 # open build/reports/tests/reqcover/requirements-coverage.html
make scenarios dashboard open               # all scenarios + dashboard
```

`make publish-reqcover` clones ReqCover into `.reqcover/` (or uses `REQCOVER_DIR=...`), builds the ref in a temporary
worktree and records the version in `.reqcover-version`; the other targets pass it to Gradle.

## What is tested

Requirements: `src/test/resources/books-read.yaml` and `books-write.yaml` (11 requirements), `shared.yaml` in both
`src/main/resources` and `src/test/resources` (classpath merging). Default config: `src/test/config/junit-platform.properties`.
Tests: `src/test/java/featuretest/` — one JUnit style per requirement (plain, repeated annotation, inherited, `@Nested`,
`@ParameterizedTest`, `@RepeatedTest`, `@TestFactory`, conditionally disabled, assumption-aborted).

| Group | Scenarios |
|---|---|
| Configuration | `junit-platform.properties`, system properties only, URI list formatting, single spec, classpath merging, no config, missing spec file, removed `reqCover.requirementsUri` |
| Coverage gate | below minimum, `failIfBelowMinimum=false`, lowered minimum, unparseable minimum |
| Which tests count | failing, aborted, disabled, all-failing `@ParameterizedTest` / `@RepeatedTest` / `@TestFactory` |
| Reports | XML and HTML content, no reporter on the classpath |

Each scenario states the behaviour ReqCover *should* have; failed checks are listed as findings on the dashboard.
`results/<scenario>/` holds each run's Gradle log and reports.

## Switches (Gradle properties)

| Property | Effect |
|---|---|
| `-PrequirementsUris=...` | `reqCover.requirementsUris` system property (overrides the properties file) |
| `-PreqCoverMin=...` / `-PfailIfBelowMinimum=...` | coverage gate |
| `-PlegacyRequirementsUri=...` | removed `reqCover.requirementsUri` |
| `-PnoConfigFile=true` | drop `junit-platform.properties` |
| `-PnoReporters=true` | drop the HTML and XML reporters |
| `-PexcludeTags=deletion` | skip the `@Nested` deletion tests |
| `-PbreakListBooks` `-PabortGetBook` `-PdisableBlankTitle` `-PbreakAllInvalidIsbn` `-PbreakRepeated` `-PbreakDynamic` `=true` | make one test fail / abort / disable |

## CI

`.github/workflows/ci.yml` runs the same `make` targets on push and pull requests to `trunk`, weekly, and on demand
(*Run workflow* lets you pick any `reqcover/reqcover` branch, tag or commit; default `trunk`). It publishes ReqCover,
runs the baseline (`make test`, must pass), runs every scenario, writes the summary to the job page and uploads the
dashboard as the `reqcover-dashboard` artifact. Scenario check failures are reported as findings, not as CI failures.
