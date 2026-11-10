import importlib.metadata
from unittest.mock import patch

import pytest

from scripts.check_environment import check_dependencies


def test_environment_pins(tmp_path):
    (tmp_path / "requirements.txt").write_text("# exact pins\nexample==1.0\n")
    with (
        patch("scripts.check_environment.importlib.metadata.version", return_value="1.0"),
        patch("scripts.check_environment.importlib.import_module") as imports,
    ):
        check_dependencies(tmp_path)
    assert imports.call_count >= 9


def test_missing_or_wrong_dependency(tmp_path):
    (tmp_path / "requirements.txt").write_text("example==1.0\n")
    with patch("scripts.check_environment.importlib.metadata.version", return_value="2.0"):
        with pytest.raises(ValueError, match="mismatch"):
            check_dependencies(tmp_path)
    with patch(
        "scripts.check_environment.importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        with pytest.raises(importlib.metadata.PackageNotFoundError):
            check_dependencies(tmp_path)
    (tmp_path / "requirements.txt").write_text("example>=1.0\n")
    with pytest.raises(ValueError, match="exact version"):
        check_dependencies(tmp_path)
