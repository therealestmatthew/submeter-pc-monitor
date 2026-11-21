"""Settings: one validated, immutable object built from layered sources.

Precedence, lowest to highest: built-in default, submeter.toml,
SUBMETER_* environment variables, command-line
overrides. Every value remembers which layer it came from, which is what
`submeter config show --effective` prints.

Out-of-range values are refused with the allowed range in the message. Nothing
is clamped, and unknown keys are errors, so a typo cannot silently do nothing.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from submeter.core.models import Confidence, Record, Severity
from submeter.core.names import WorkloadPattern
from submeter.core.units import (
    Duration,
    Fraction,
    Rate,
    Size,
    duration_range,
    fraction_range,
    parse_duration,
    parse_percent,
)

ENV_PREFIX = "SUBMETER_"

ActiveInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("250ms", "10s"))
]
IdleInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("1s", "60s"))
]
IdleAfter = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("10s", "10m"))
]
SlowInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("1s", "60s"))
]
GpuInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("1s", "30s"))
]
UssInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("10s", "5m"))
]
KeyframeInterval = Annotated[
    float, BeforeValidator(parse_duration), AfterValidator(duration_range("1m", "1h"))
]
OverheadShare = Annotated[
    float, BeforeValidator(parse_percent), AfterValidator(fraction_range("0.5%", "10%"))
]


class OverheadLimit(Record):
    idle: OverheadShare = 0.01
    active: OverheadShare = 0.03


class Sampling(Record):
    mode: Literal["adaptive", "fixed"] = "adaptive"
    active_interval: ActiveInterval = 2.0
    idle_interval: IdleInterval = 5.0
    idle_after: IdleAfter = 60.0
    uss_interval: UssInterval = 30.0
    uss_top_n: int = Field(default=25, ge=0, le=200)
    gpu_interval: GpuInterval = 2.0
    thermal_interval: SlowInterval = 5.0
    network_interval: SlowInterval = 5.0
    on_battery_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    overhead_limit: OverheadLimit = OverheadLimit()


class Retention(Record):
    raw: Duration = 48 * 3600.0
    minute: Duration = 30 * 86400.0
    executables: Duration = 365 * 86400.0


class Backups(Record):
    keep: int = Field(default=3, ge=1, le=30)


class ChangeThreshold(Record):
    cpu_points: float = Field(default=0.5, ge=0.0, le=100.0)
    memory: Size = 8 * 1024**2


class Storage(Record):
    disk_budget: Size = 2 * 1024**3
    keyframe_interval: KeyframeInterval = 600.0
    change_threshold: ChangeThreshold = ChangeThreshold()
    retention: Retention = Retention()
    backups: Backups = Backups()


class Leak(Record):
    min_duration: Duration = 2 * 3600.0
    min_slope: Rate = 50 * 1024**2 / 3600.0


class SlowGrowth(Record):
    window: Duration = 7 * 86400.0


class Baseline(Record):
    learning_period: Duration = 7 * 86400.0
    window: Duration = 14 * 86400.0
    sensitivity: float = Field(default=4.0, gt=0.0)


class Analysis(Record):
    leak: Leak = Leak()
    slow_growth: SlowGrowth = SlowGrowth()
    baseline: Baseline = Baseline()


class Verdict(Record):
    window: Duration = 300.0
    min_confidence: Confidence = Confidence.MODERATE
    thresholds: dict[str, float] = Field(default_factory=dict)


class AlertRule(Record):
    """A threshold on one metric of one workload pattern. Fields, not a sentence to parse."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    name: str
    workload: WorkloadPattern = "*"
    metric: str
    above: float | None = None
    below: float | None = None
    duration: Duration = Field(default=0.0, alias="for")
    severity: Severity = Severity.WARNING

    @model_validator(mode="after")
    def _one_bound(self) -> AlertRule:
        if (self.above is None) == (self.below is None):
            raise ValueError("give exactly one of 'above' or 'below'")
        return self


class Alerts(Record):
    """Alert settings.

    `rules` holds the user's own rules. Built-in rules come with the alerts component.
    """

    cooldown: Duration = 900.0
    quiet_hours: str | None = None
    channels: tuple[Literal["dashboard", "desktop"], ...] = ("dashboard", "desktop")
    rules: tuple[AlertRule, ...] = ()


class Attribution(Record):
    rules_file: str = "rules.toml"
    inherit_from_parent: bool = True
    unattributed_alert: Fraction = 0.10
    max_workload_names: int = Field(default=200, ge=1)


class Privacy(Record):
    redaction: Literal["scrub", "exe_only"] = "exe_only"
    redact_patterns: tuple[str, ...] = ()

    @field_validator("redact_patterns")
    @classmethod
    def _compiles(cls, patterns: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"redact pattern {pattern!r} is not valid: {error}") from error
        return patterns


class Providers(Record):
    """Which providers may run. An empty list means all of them."""

    enabled: tuple[str, ...] = ()


class Api(Record):
    port: int = Field(default=8787, ge=1024, le=65535)
    mcp_enabled: bool = False


class Ui(Record):
    units: Literal["GiB", "GB"] = "GiB"
    default_range: Duration = 3600.0


class Settings(Record):
    sampling: Sampling = Sampling()
    storage: Storage = Storage()
    analysis: Analysis = Analysis()
    verdict: Verdict = Verdict()
    alerts: Alerts = Alerts()
    attribution: Attribution = Attribution()
    privacy: Privacy = Privacy()
    providers: Providers = Providers()
    api: Api = Api()
    ui: Ui = Ui()


class ConfigError(ValueError):
    """Raised with one readable line per problem, each naming the setting at fault."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True, slots=True)
class LoadedSettings:
    settings: Settings
    sources: dict[str, str]

    def effective(self) -> list[tuple[str, str, str]]:
        """Every setting as (dotted key, value, source), sorted by key."""
        values = _flatten(self.settings.model_dump(mode="json", by_alias=True))
        return [
            (key, str(value), self.sources.get(key, "default"))
            for key, value in sorted(values.items())
        ]


def _flatten(tree: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in tree.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, Mapping) and value:
            flat.update(_flatten(value, dotted + "."))
        else:
            flat[dotted] = value
    return flat


def _merge(base: dict[str, Any], layer: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in layer.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _merge(current, value)
        else:
            merged[key] = dict(value) if isinstance(value, Mapping) else value
    return merged


def _from_environment(env: Mapping[str, str]) -> dict[str, Any]:
    """SUBMETER_SAMPLING__ACTIVE_INTERVAL=2s becomes {"sampling": {"active_interval": "2s"}}."""
    tree: dict[str, Any] = {}
    for name, value in env.items():
        if not name.startswith(ENV_PREFIX) or "__" not in name:
            continue
        *parents, leaf = name[len(ENV_PREFIX) :].lower().split("__")
        node = tree
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value
    return tree


def load_settings(
    path: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> LoadedSettings:
    """Build settings from every layer and record where each value came from."""
    layers: list[tuple[str, Mapping[str, Any]]] = []
    if path is not None:
        try:
            with path.open("rb") as handle:
                document = tomllib.load(handle)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError([f"{path}: {error}"]) from error
        layers.append(("file", document))
    if env:
        layers.append(("env", _from_environment(env)))
    if overrides:
        layers.append(("flag", overrides))

    merged: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for name, layer in layers:
        merged = _merge(merged, layer)
        sources.update(dict.fromkeys(_flatten(layer), name))
    try:
        settings = Settings.model_validate(merged)
    except ValidationError as error:
        problems = []
        for issue in error.errors():
            where = ".".join(str(part) for part in issue["loc"])
            problems.append(f"{where}: {issue['msg'].removeprefix('Value error, ')}")
        raise ConfigError(problems) from error
    return LoadedSettings(settings=settings, sources=sources)
