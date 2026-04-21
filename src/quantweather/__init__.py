"""QuantWeather package."""

from .engine import evaluate_market, screen_markets
from .analytics import analyze_run_history, analyze_screen_run
from .dashboard import render_dashboard_html, write_dashboard_html
from .discovery import discover_weather_markets
from .execution import build_execution_orders
from .ingest import load_forecasts_from_fixture, load_markets_from_fixture
from .monitoring import monitor_execution_orders, monitor_screen_run
from .noaa import fetch_noaa_forecast, load_noaa_forecasts_from_fixture
from .report import render_run_comparison_report, render_screen_run_report
from .serialize import recommendation_to_dict, recommendations_to_json, write_recommendations_json
from .storage import (
    compare_latest_two_runs,
    compare_screen_runs,
    list_screen_runs,
    load_latest_screen_run,
    load_latest_run_metadata,
    load_screen_run,
    persist_screen_run,
    save_latest_dashboard,
    save_latest_comparison_report,
    save_latest_execution,
    save_latest_screen_report,
    summarize_latest_screen_run,
    summarize_screen_run,
)

__all__ = [
    "evaluate_market",
    "screen_markets",
    "analyze_screen_run",
    "analyze_run_history",
    "render_dashboard_html",
    "write_dashboard_html",
    "discover_weather_markets",
    "build_execution_orders",
    "monitor_screen_run",
    "monitor_execution_orders",
    "fetch_noaa_forecast",
    "load_noaa_forecasts_from_fixture",
    "load_markets_from_fixture",
    "load_forecasts_from_fixture",
    "render_screen_run_report",
    "render_run_comparison_report",
    "recommendation_to_dict",
    "recommendations_to_json",
    "write_recommendations_json",
    "persist_screen_run",
    "list_screen_runs",
    "load_screen_run",
    "load_latest_screen_run",
    "load_latest_run_metadata",
    "summarize_screen_run",
    "summarize_latest_screen_run",
    "compare_screen_runs",
    "compare_latest_two_runs",
    "save_latest_dashboard",
    "save_latest_screen_report",
    "save_latest_comparison_report",
    "save_latest_execution",
]
