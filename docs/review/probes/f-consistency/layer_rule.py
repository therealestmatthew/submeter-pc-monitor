"""Apply tests/test_layers.py's rule to the import edges the brief says the build will add.

docs/14 says store.raw will be imported by "the collector loop" and the growth arithmetic by
"the detectors"; docs/05 says analysis reads windows from the store; docs/17 says the layers are
providers, sampler, attribution, store, analysis with data flowing one way. This loads the LAYER
table from the test file and asks whether each edge would pass. Run from the repository root:
    uv run python docs/review/probes/f-consistency/layer_rule.py
"""

from __future__ import annotations

import ast
from pathlib import Path

source = Path("tests/test_layers.py").read_text(encoding="utf-8")
layer: dict[str, int] = {}
for node in ast.parse(source).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "LAYER":
        layer = ast.literal_eval(node.value)
print("LAYER from tests/test_layers.py:", layer)


def allowed(package: str, target: str) -> bool:
    """The assertion at tests/test_layers.py:43."""
    return target == package or layer[target] < layer[package]


edges = [
    ("collector", "store", "docs/14 store.raw: imported by 'the collector loop', phase 1"),
    ("collector", "attribution", "docs/05: sampler -> attribution inside the collector"),
    ("attribution", "store", "docs/17 'five layers': attribution feeds the store"),
    ("analysis", "store", "docs/05: analysis 'reads windows from the store'"),
    ("store", "collector", "the reverse, in case the loop lives in store"),
    ("analysis", "core", "for contrast: a downward edge"),
]
for package, target, why in edges:
    verdict = "passes" if allowed(package, target) else "FAILS"
    print(f"{package:>11} imports {target:<11} {verdict:<6}  {why}")
