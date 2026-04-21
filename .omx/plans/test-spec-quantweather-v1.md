# QuantWeather V1 Test Spec

## Verification Strategy

The repo currently uses `unittest` plus direct CLI command execution. New work should preserve that shape and add only targeted tests.

## Existing Green Baseline

- `env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
- `python3 -m compileall src tests`

## Required Tests for the Next Slice

### Dashboard generation

- command or function generates a dashboard artifact from saved run data
- output contains latest run summary, approved opportunities, blocked opportunities, and errors
- output includes references to saved run JSON and report artifacts when present

### CLI/dashboard integration

- after saving runs, generating the dashboard succeeds with exit code 0
- dashboard generation works when `run_dir` is sourced from CLI config
- missing run history fails cleanly with a concise error

### Regression expectations

- no existing CLI/profile/storage/report tests regress
- compile step remains green

## Quality Gates

- full test suite green
- compileall green
- architect verification approved
- deslop pass limited to changed files
- post-deslop regression green

## Failure Conditions

- tracebacks for expected operator errors
- dashboard artifact missing required sections
- config or run-dir resolution inconsistencies across commands
