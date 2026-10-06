"""Static design checks that need neither Streamlit nor network: palette sync, one central stylesheet, page-shell order, keys."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_FILES = [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py")), *sorted((ROOT / "core").glob("*.py"))]
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")


def _palette() -> dict[str, str]:
    tree = ast.parse((ROOT / "core" / "ui.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "PALETTE":
            return ast.literal_eval(node.value)
    raise AssertionError("PALETTE not found in core/ui.py")


def test_config_theme_matches_palette():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    pal = _palette()
    assert theme["base"] == "light"
    assert theme["primaryColor"].lower() == pal["primary"].lower()
    assert theme["backgroundColor"].lower() == pal["bg"].lower()
    assert theme["secondaryBackgroundColor"].lower() == pal["surface"].lower()
    assert theme["textColor"].lower() == pal["text"].lower()


def test_hex_colours_only_in_central_stylesheet():
    offenders = {}
    for path in PY_FILES:
        if path.name == "ui.py":
            continue
        found = HEX.findall(path.read_text(encoding="utf-8"))
        if found:
            offenders[str(path.relative_to(ROOT))] = found
    assert not offenders, offenders


def test_single_stylesheet_block():
    sources = "\n".join(p.read_text(encoding="utf-8") for p in PY_FILES if p.name != "ui.py")
    assert "<style" not in sources


def _first_streamlit_call(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and isinstance(sub.func.value, ast.Name):
                if sub.func.value.id in {"st", "ui"}:
                    return f"{sub.func.value.id}.{sub.func.attr}"
    raise AssertionError(f"{path} makes no st/ui call")


def test_every_page_starts_with_setup_page():
    for path in [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py"))]:
        assert _first_streamlit_call(path) == "ui.setup_page", path.name


def test_set_page_config_is_first_streamlit_call_in_setup_page():
    tree = ast.parse((ROOT / "core" / "ui.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "setup_page")
    calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
             and isinstance(c.func.value, ast.Name) and c.func.value.id == "st"]
    calls.sort(key=lambda c: (c.lineno, c.col_offset))
    assert calls[0].func.attr == "set_page_config"


def test_literal_widget_keys_are_unique_per_file():
    for path in PY_FILES:
        keys = []
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "key" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        keys.append(kw.value.value)
        assert len(keys) == len(set(keys)), (path.name, sorted(k for k in keys if keys.count(k) > 1))


def test_no_deprecated_container_width_parameter_outside_compat_helper():
    for path in PY_FILES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "use_container_width" in line:
                assert path.name == "ui.py", f"{path.name}:{lineno}"
