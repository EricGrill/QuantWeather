from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ExecutionConfig:
    database_url: str = "sqlite:///artifacts/execution.db"
    environment: str = "development"
    dry_run: bool = True


def load_config() -> ExecutionConfig:
    return ExecutionConfig(
        database_url=os.getenv("QW_EXEC_DATABASE_URL", "sqlite:///artifacts/execution.db"),
        environment=os.getenv("QW_EXEC_ENV", "development"),
        dry_run=os.getenv("QW_EXEC_DRY_RUN", "true").lower() != "false",
    )
