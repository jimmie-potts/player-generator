from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOTS = {
    "reference_data_app": ROOT / "apps" / "reference-data" / "src" / "reference_data_app",
    "roster_generator": ROOT / "apps" / "roster-generator" / "src" / "roster_generator",
    "player_data_contracts": (
        ROOT / "packages" / "data-contracts" / "src" / "player_data_contracts"
    ),
    "player_attribute_engine": (
        ROOT / "packages" / "attribute-engine" / "src" / "player_attribute_engine"
    ),
}


def _import_roots(path: Path) -> set[str]:
    imported: set[str] = set()
    for source_file in path.rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    return imported


def test_planned_python_package_roots_exist() -> None:
    assert all(path.is_dir() for path in PACKAGE_ROOTS.values())


def test_reference_and_roster_apps_do_not_import_each_other() -> None:
    reference_imports = _import_roots(PACKAGE_ROOTS["reference_data_app"])
    roster_imports = _import_roots(PACKAGE_ROOTS["roster_generator"])
    assert "roster_generator" not in reference_imports
    assert "reference_data_app" not in roster_imports


def test_shared_packages_do_not_import_applications() -> None:
    for name in ("player_data_contracts", "player_attribute_engine"):
        imports = _import_roots(PACKAGE_ROOTS[name])
        assert "reference_data_app" not in imports
        assert "roster_generator" not in imports


def test_removed_coupled_package_is_not_imported() -> None:
    for path in PACKAGE_ROOTS.values():
        assert "player_generator" not in _import_roots(path)
