from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_dockerfile_runs_cli_module(self) -> None:
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn('ENTRYPOINT ["python", "-m", "quantweather.cli"]', dockerfile)
        self.assertIn("COPY src /app/src", dockerfile)

    def test_compose_uses_local_artifacts_mount(self) -> None:
        compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn("build:", compose)
        self.assertIn("./artifacts:/app/artifacts", compose)
        self.assertIn("./tests/fixtures:/app/tests/fixtures:ro", compose)
        self.assertIn("- screen", compose)

    def test_dockerignore_excludes_local_artifacts_and_omx_state(self) -> None:
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

        self.assertIn(".omx", dockerignore)
        self.assertIn("artifacts/", dockerignore)
        self.assertIn("__pycache__/", dockerignore)


if __name__ == "__main__":
    unittest.main()
