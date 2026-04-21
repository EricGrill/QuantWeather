from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .domain import ForecastSnapshot, Market, RiskLimits, SizingMethod, WeatherMetric
from .engine import evaluate_market, screen_markets
from .ingest import load_forecasts_from_fixture, load_markets_from_fixture
from .report import render_run_comparison_report, render_screen_run_report
from .serialize import recommendations_to_json, write_recommendations_json
from .storage import (
    compare_latest_two_runs,
    list_screen_runs,
    load_latest_screen_run,
    persist_screen_run,
    save_latest_dashboard,
    save_latest_comparison_report,
    save_latest_screen_report,
    summarize_latest_screen_run,
)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        _print_demo_evaluation()
        return 0

    parser = _build_parser()
    args = parser.parse_args(list(argv))

    try:
        profile = _load_profile(getattr(args, "config", None))
        if args.command == "demo":
            _print_demo_evaluation()
        elif args.command == "screen":
            recommendations = _screen_records_from_args(args, profile)
            if _screen_format_from_args(args, profile) == "json":
                print(recommendations_to_json(recommendations))
            else:
                print(_render_screen_text(recommendations))
        elif args.command == "save-run":
            print(
                save_screen_run(
                    markets_path=_markets_path_from_args(args, profile),
                    forecasts_path=_forecasts_path_from_args(args, profile),
                    directory=_run_dir_from_args(args, profile),
                    label=_label_from_args(args, profile),
                    risk_limits=_risk_limits_from_args(args, profile),
                    account_balance=_account_balance_from_args(args, profile),
                    sizing_method=_sizing_method_from_args(args, profile),
                    extra_metadata=_config_metadata(profile),
                )
            )
        elif args.command == "list-runs":
            _print_json(list_screen_runs(_run_dir_from_args(args, profile)))
        elif args.command == "summary":
            _print_json(summarize_latest_screen_run(_run_dir_from_args(args, profile)))
        elif args.command == "compare":
            _print_json(compare_latest_two_runs(_run_dir_from_args(args, profile)))
        elif args.command == "report":
            demo_latest_screen_report(_run_dir_from_args(args, profile))
        elif args.command == "report-save":
            print(save_latest_screen_report_file(_run_dir_from_args(args, profile)))
        elif args.command == "comparison-report":
            demo_latest_comparison_report(_run_dir_from_args(args, profile))
        elif args.command == "comparison-report-save":
            print(save_latest_comparison_report_file(_run_dir_from_args(args, profile)))
        elif args.command == "dashboard-save":
            print(save_latest_dashboard_file(_run_dir_from_args(args, profile)))
        else:
            parser.error(f"Unsupported command: {args.command}")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


def _print_demo_evaluation() -> None:
    market = Market(
        market_id="demo-nyc-high-80",
        title="New York City high at or above 80F?",
        yes_price=0.41,
        no_price=0.62,
        liquidity=25000.0,
        spread=0.03,
        expires_at="2026-04-21T23:59:59Z",
    )
    forecast = ForecastSnapshot(
        source="demo-noaa",
        observed_at="2026-04-20T12:00:00Z",
        location="New York City",
        metrics={
            WeatherMetric.TEMPERATURE_HIGH_F: 83.0,
            WeatherMetric.PRECIPITATION_IN: 0.1,
            WeatherMetric.PRECIPITATION_PROBABILITY: 0.2,
        },
        uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
    )

    result = evaluate_market(
        market=market,
        forecast=forecast,
        risk_limits=_default_risk_limits(),
        account_balance=5000.0,
    )

    print(f"Market: {result.market.title}")
    print(f"Rule: {result.rule.metric.value} {result.rule.comparator.value} {result.rule.threshold}")
    print(f"Model YES probability: {result.estimate.probability_yes:.2f}")
    if result.signal:
        print(f"Signal: {result.signal.side.value} with edge {result.signal.edge:.2%}")
    else:
        print("Signal: none")
    if result.proposal.approved:
        print(f"Proposed position: {result.proposal.side.value} ${result.proposal.notional:.2f}")
    else:
        print("Proposal blocked:")
        for reason in result.proposal.blocked_reasons:
            print(f"- {reason}")
    print(f"Recommendation state: {result.recommendation.approval_state.value}")
    print(f"Final status: {result.recommendation.final_status.value}")
    print(f"Reason codes: {', '.join(result.recommendation.reason_codes)}")


def demo_fixture_screen() -> None:
    print(_render_screen_text(_screen_fixture_file("markets.json")))


def demo_fixture_screen_json() -> None:
    print(recommendations_to_json(_screen_fixture_file("markets_mixed.json")))


def export_fixture_screen_json(
    output_path: str | Path | None = None,
) -> Path:
    recommendations = _screen_fixture_file("markets_mixed.json")
    if output_path is None:
        output_path = Path(__file__).resolve().parents[2] / "artifacts" / "fixture-screen.json"
    return write_recommendations_json(recommendations, output_path)


def save_fixture_screen_run(
    directory: str | Path | None = None,
) -> Path:
    return save_screen_run(
        markets_path=_default_fixtures_dir() / "markets_mixed.json",
        forecasts_path=_default_fixtures_dir() / "forecasts.json",
        directory=directory,
        label="fixture-screen",
    )


def demo_saved_screen_runs(
    directory: str | Path | None = None,
) -> None:
    directory = _resolve_run_dir(directory)
    runs = list_screen_runs(directory)
    latest = load_latest_screen_run(directory) if runs else []
    print(f"Saved runs: {len(runs)}")
    if runs:
        print(f"Latest run: {runs[-1]['run_id']}")
        _print_json(latest)


def demo_saved_screen_summary(
    directory: str | Path | None = None,
) -> None:
    _print_json(summarize_latest_screen_run(_resolve_run_dir(directory)))


def demo_compare_latest_runs(
    directory: str | Path | None = None,
) -> None:
    _print_json(compare_latest_two_runs(_resolve_run_dir(directory)))


def demo_latest_screen_report(
    directory: str | Path | None = None,
) -> None:
    directory = _resolve_run_dir(directory)
    runs = list_screen_runs(directory)
    records = load_latest_screen_run(directory)
    summary = summarize_latest_screen_run(directory)
    metadata = runs[-1] if runs else None
    print(render_screen_run_report(records, summary, metadata))


def demo_latest_comparison_report(
    directory: str | Path | None = None,
) -> None:
    directory = _resolve_run_dir(directory)
    runs = list_screen_runs(directory)
    comparison = compare_latest_two_runs(directory)
    older_metadata = runs[-2] if len(runs) >= 2 else None
    newer_metadata = runs[-1] if len(runs) >= 2 else None
    print(render_run_comparison_report(comparison, older_metadata, newer_metadata))


def save_latest_screen_report_file(
    directory: str | Path | None = None,
) -> Path:
    return save_latest_screen_report(_resolve_run_dir(directory))


def save_latest_comparison_report_file(
    directory: str | Path | None = None,
) -> Path:
    return save_latest_comparison_report(_resolve_run_dir(directory))


def save_latest_dashboard_file(
    directory: str | Path | None = None,
) -> Path:
    return save_latest_dashboard(_resolve_run_dir(directory))


def save_screen_run(
    markets_path: str | Path,
    forecasts_path: str | Path,
    directory: str | Path | None = None,
    label: str = "screen",
    risk_limits: RiskLimits | None = None,
    account_balance: float = 5000.0,
    sizing_method: str = "proportional",
    extra_metadata: dict[str, Any] | None = None,
) -> Path:
    directory = _resolve_run_dir(directory)
    risk_limits = risk_limits or _default_risk_limits()
    recommendations = _screen_records(
        markets_path=markets_path,
        forecasts_path=forecasts_path,
        risk_limits=risk_limits,
        account_balance=account_balance,
        sizing_method=sizing_method,
    )
    metadata = {
        "markets_path": str(Path(markets_path).expanduser().resolve()),
        "forecasts_path": str(Path(forecasts_path).expanduser().resolve()),
        "account_balance": account_balance,
        "sizing_method": sizing_method,
        "risk_limits": {
            "max_trade_notional": risk_limits.max_trade_notional,
            "max_market_exposure": risk_limits.max_market_exposure,
            "max_daily_risk": risk_limits.max_daily_risk,
            "min_confidence": risk_limits.min_confidence,
            "min_edge": risk_limits.min_edge,
            "max_spread": risk_limits.max_spread,
            "min_liquidity": risk_limits.min_liquidity,
        },
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return persist_screen_run(recommendations, directory, label=label, metadata=metadata)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QuantWeather operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("demo", help="Run the single-market demo evaluation")

    screen_parser = subparsers.add_parser("screen", help="Screen markets against forecasts")
    _add_config_argument(screen_parser)
    _add_screen_arguments(screen_parser)

    save_parser = subparsers.add_parser("save-run", help="Persist a screening run to disk")
    _add_config_argument(save_parser)
    _add_screen_arguments(save_parser)
    save_parser.add_argument("--run-dir", type=Path)
    save_parser.add_argument("--label")

    list_parser = subparsers.add_parser("list-runs", help="List saved runs")
    _add_config_argument(list_parser)
    list_parser.add_argument("--run-dir", type=Path)

    summary_parser = subparsers.add_parser("summary", help="Summarize the latest saved run")
    _add_config_argument(summary_parser)
    summary_parser.add_argument("--run-dir", type=Path)

    compare_parser = subparsers.add_parser("compare", help="Compare the latest two saved runs")
    _add_config_argument(compare_parser)
    compare_parser.add_argument("--run-dir", type=Path)

    report_parser = subparsers.add_parser("report", help="Render the latest run report")
    _add_config_argument(report_parser)
    report_parser.add_argument("--run-dir", type=Path)

    report_save_parser = subparsers.add_parser("report-save", help="Write the latest run report")
    _add_config_argument(report_save_parser)
    report_save_parser.add_argument("--run-dir", type=Path)

    comparison_report_parser = subparsers.add_parser(
        "comparison-report",
        help="Render the latest comparison report",
    )
    _add_config_argument(comparison_report_parser)
    comparison_report_parser.add_argument("--run-dir", type=Path)

    comparison_report_save_parser = subparsers.add_parser(
        "comparison-report-save",
        help="Write the latest comparison report",
    )
    _add_config_argument(comparison_report_save_parser)
    comparison_report_save_parser.add_argument("--run-dir", type=Path)

    dashboard_save_parser = subparsers.add_parser(
        "dashboard-save",
        help="Write the latest dashboard artifact",
    )
    _add_config_argument(dashboard_save_parser)
    dashboard_save_parser.add_argument("--run-dir", type=Path)

    return parser


def _add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path)


def _add_screen_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--markets", type=Path)
    parser.add_argument("--forecasts", type=Path)
    parser.add_argument("--account-balance", type=_positive_float)
    parser.add_argument(
        "--sizing-method",
        choices=("fixed", "proportional", "fractional_kelly"),
    )
    parser.add_argument("--max-trade-notional", type=_nonnegative_float)
    parser.add_argument("--max-market-exposure", type=_nonnegative_float)
    parser.add_argument("--max-daily-risk", type=_nonnegative_float)
    parser.add_argument("--min-confidence", type=_probability_float)
    parser.add_argument("--min-edge", type=_nonnegative_float)
    parser.add_argument("--max-spread", type=_probability_float)
    parser.add_argument("--min-liquidity", type=_nonnegative_float)
    parser.add_argument("--format", choices=("text", "json"))


def _screen_records_from_args(args: argparse.Namespace, profile: dict[str, Any]):
    return _screen_records(
        markets_path=_markets_path_from_args(args, profile),
        forecasts_path=_forecasts_path_from_args(args, profile),
        risk_limits=_risk_limits_from_args(args, profile),
        account_balance=_account_balance_from_args(args, profile),
        sizing_method=_sizing_method_from_args(args, profile),
    )


def _screen_records(
    markets_path: str | Path,
    forecasts_path: str | Path,
    risk_limits: RiskLimits,
    account_balance: float,
    sizing_method: str,
):
    markets = load_markets_from_fixture(markets_path)
    forecasts = load_forecasts_from_fixture(forecasts_path)
    return screen_markets(
        markets=markets,
        forecasts=forecasts,
        risk_limits=risk_limits,
        account_balance=account_balance,
        sizing_method=SizingMethod(sizing_method),
    )


def _render_screen_text(records: list) -> str:
    lines = ["QuantWeather Screen", ""]
    for record in records:
        edge = f"{record.edge:.4f}" if record.edge is not None else "n/a"
        lines.append(
            f"- {record.market_id}: {record.final_status.value} edge={edge} "
            f"reasons={','.join(record.reason_codes)}"
        )
    return "\n".join(lines)


def _load_profile(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read config file: {path}") from exc

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("CLI profile must be a JSON object")

    allowed_top_level = {"version", "name", "run_dir", "screen", "save_run"}
    unknown_top_level = set(payload) - allowed_top_level
    if unknown_top_level:
        raise ValueError(f"Unknown CLI profile keys: {', '.join(sorted(unknown_top_level))}")

    screen = payload.get("screen", {})
    if screen in (None, {}):
        screen = {}
    if not isinstance(screen, dict):
        raise ValueError("screen in CLI profile must be an object")
    allowed_screen = {
        "markets",
        "forecasts",
        "account_balance",
        "sizing_method",
        "format",
        "risk_limits",
    }
    unknown_screen = set(screen) - allowed_screen
    if unknown_screen:
        raise ValueError(f"Unknown screen profile keys: {', '.join(sorted(unknown_screen))}")

    save_run = payload.get("save_run", {})
    if save_run in (None, {}):
        save_run = {}
    if not isinstance(save_run, dict):
        raise ValueError("save_run in CLI profile must be an object")
    allowed_save_run = {"label"}
    unknown_save_run = set(save_run) - allowed_save_run
    if unknown_save_run:
        raise ValueError(f"Unknown save_run profile keys: {', '.join(sorted(unknown_save_run))}")

    payload["screen"] = screen
    payload["save_run"] = save_run
    payload["_path"] = path.resolve()
    payload["_base_dir"] = path.parent
    return payload


def _path_from_profile(value: Any, profile: dict[str, Any]) -> Path | None:
    if value is None:
        return None
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()
    base_dir = Path(profile.get("_base_dir", Path.cwd()))
    return (base_dir / path).resolve()


def _markets_path_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> Path:
    if args.markets is not None:
        return Path(args.markets).resolve()
    return _path_from_profile(profile.get("screen", {}).get("markets"), profile) or (
        _default_fixtures_dir() / "markets_mixed.json"
    )


def _forecasts_path_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> Path:
    if args.forecasts is not None:
        return Path(args.forecasts).resolve()
    return _path_from_profile(profile.get("screen", {}).get("forecasts"), profile) or (
        _default_fixtures_dir() / "forecasts.json"
    )


def _account_balance_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> float:
    screen = profile.get("screen", {})
    return _coalesce(args.account_balance, _validated_optional_positive(screen.get("account_balance")), 5000.0)


def _sizing_method_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    value = _coalesce(args.sizing_method, profile.get("screen", {}).get("sizing_method"), "proportional")
    if value not in {"fixed", "proportional", "fractional_kelly"}:
        raise ValueError("sizing_method must be one of fixed, proportional, fractional_kelly")
    return str(value)


def _screen_format_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    value = _coalesce(args.format, profile.get("screen", {}).get("format"), "text")
    if value not in {"text", "json"}:
        raise ValueError("format must be one of text, json")
    return str(value)


def _run_dir_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> Path:
    if getattr(args, "run_dir", None) is not None:
        return Path(args.run_dir).resolve()
    return _path_from_profile(profile.get("run_dir"), profile) or _default_run_dir()


def _label_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    return str(_coalesce(getattr(args, "label", None), profile.get("save_run", {}).get("label"), "screen"))


def _config_metadata(profile: dict[str, Any]) -> dict[str, Any] | None:
    if not profile:
        return None
    return {
        "config_path": str(profile["_path"]),
        "profile_name": profile.get("name"),
        "profile_version": profile.get("version"),
    }


def _risk_limits_from_args(args: argparse.Namespace, profile: dict[str, Any]) -> RiskLimits:
    profile_limits = _risk_limits_from_profile(profile)
    defaults = _default_risk_limits()
    return RiskLimits(
        max_trade_notional=_coalesce(args.max_trade_notional, profile_limits.get("max_trade_notional"), defaults.max_trade_notional),
        max_market_exposure=_coalesce(args.max_market_exposure, profile_limits.get("max_market_exposure"), defaults.max_market_exposure),
        max_daily_risk=_coalesce(args.max_daily_risk, profile_limits.get("max_daily_risk"), defaults.max_daily_risk),
        min_confidence=_coalesce(args.min_confidence, profile_limits.get("min_confidence"), defaults.min_confidence),
        min_edge=_coalesce(args.min_edge, profile_limits.get("min_edge"), defaults.min_edge),
        max_spread=_coalesce(args.max_spread, profile_limits.get("max_spread"), defaults.max_spread),
        min_liquidity=_coalesce(args.min_liquidity, profile_limits.get("min_liquidity"), defaults.min_liquidity),
    )


def _risk_limits_from_profile(profile: dict[str, Any]) -> dict[str, float]:
    payload = profile.get("screen", {}).get("risk_limits", {})
    if payload in (None, {}):
        return {}
    if not isinstance(payload, dict):
        raise ValueError("screen.risk_limits in CLI profile must be an object")

    allowed_keys = {
        "max_trade_notional": _validated_nonnegative,
        "max_market_exposure": _validated_nonnegative,
        "max_daily_risk": _validated_nonnegative,
        "min_confidence": _validated_probability,
        "min_edge": _validated_nonnegative,
        "max_spread": _validated_probability,
        "min_liquidity": _validated_nonnegative,
    }
    unknown_keys = set(payload) - set(allowed_keys)
    if unknown_keys:
        raise ValueError(f"Unknown screen.risk_limits keys: {', '.join(sorted(unknown_keys))}")

    return {key: validator(payload[key]) for key, validator in allowed_keys.items() if key in payload}


def _default_risk_limits() -> RiskLimits:
    return RiskLimits(
        max_trade_notional=250.0,
        max_market_exposure=400.0,
        max_daily_risk=500.0,
        min_confidence=0.45,
        min_edge=0.05,
        max_spread=0.05,
        min_liquidity=5000.0,
    )


def _default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def _default_run_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "artifacts" / "screen-runs"


def _nonnegative_float(value: str) -> float:
    try:
        return _validated_nonnegative(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _positive_float(value: str) -> float:
    try:
        return _validated_positive(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _probability_float(value: str) -> float:
    try:
        return _validated_probability(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validated_nonnegative(value: Any) -> float:
    parsed = float(value)
    if parsed < 0.0:
        raise ValueError("value must be non-negative")
    return parsed


def _validated_positive(value: Any) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise ValueError("value must be positive")
    return parsed


def _validated_optional_positive(value: Any) -> float | None:
    return None if value is None else _validated_positive(value)


def _validated_probability(value: Any) -> float:
    parsed = float(value)
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError("value must be between 0 and 1")
    return parsed


def _resolve_run_dir(directory: str | Path | None) -> Path:
    return _default_run_dir() if directory is None else Path(directory)


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _screen_fixture_file(market_fixture_name: str):
    return _screen_records(
        markets_path=_default_fixtures_dir() / market_fixture_name,
        forecasts_path=_default_fixtures_dir() / "forecasts.json",
        risk_limits=_default_risk_limits(),
        account_balance=5000.0,
        sizing_method="proportional",
    )


if __name__ == "__main__":
    raise SystemExit(main())
