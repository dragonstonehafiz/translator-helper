"""
Declarative provider settings.

A provider declares its settings as a ModelConfig dataclass whose attributes are ConfigFields built with
`setting()`. The base class loads and saves the provider's JSON file under CONFIG_DIR and produces the
Settings-page schema, so adding a setting means declaring one field.
"""

import copy
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Generic, TypeVar

from utils.config import CONFIG_DIR

ConfigValue = str | int | float | bool
ValueT = TypeVar("ValueT", str, int, float, bool)


@dataclass(frozen=True)
class Choice:
    """One selectable dropdown entry."""

    label: str
    value: str


class OptionType(ABC, Generic[ValueT]):
    """Describes how a setting is validated and which Settings-page control renders it."""

    FRONTEND_TYPE: ClassVar[str] = "text"

    @abstractmethod
    def consume(self, value: Any) -> ValueT:
        """Validate and convert a newly submitted value, raising ValueError when it is not acceptable."""
        raise NotImplementedError

    def restore(self, value: Any) -> ValueT:
        """Convert a value read from the saved JSON file; stricter checks are left to consume()."""
        return self.consume(value)

    def frontend_type(self) -> str:
        """Return the control type name the Settings page renders for this option."""
        return self.FRONTEND_TYPE

    def to_frontend(self, current: Any) -> dict[str, Any]:
        """Return extra schema keys for this option (bounds, choices, placeholder)."""
        return {}


@dataclass(frozen=True)
class TextOption(OptionType[str]):
    """Free text, optionally rendered as a password input whose value is never sent to the browser."""

    password: bool = False
    placeholder: str | None = None

    def consume(self, value: Any) -> str:
        """Accept any scalar as text."""
        if isinstance(value, (dict, list)):
            raise ValueError("expected text")
        return "" if value is None else str(value)

    def frontend_type(self) -> str:
        """Return 'password' or 'text'."""
        return "password" if self.password else "text"

    def to_frontend(self, current: Any) -> dict[str, Any]:
        """Return the placeholder when one is declared."""
        return {"placeholder": self.placeholder} if self.placeholder else {}


def _check_range(value: float, minimum: float | None, maximum: float | None) -> None:
    """Raise ValueError when value falls outside the inclusive bounds."""
    if minimum is not None and value < minimum:
        raise ValueError(f"must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"must be at most {maximum}")


@dataclass(frozen=True)
class NumberOption(OptionType[float]):
    """A decimal number with optional bounds."""

    FRONTEND_TYPE: ClassVar[str] = "number"
    min: float | None = None
    max: float | None = None
    step: float | None = None

    def consume(self, value: Any) -> float:
        """Accept numbers and numeric strings within the bounds; booleans are rejected."""
        if isinstance(value, bool):
            raise ValueError("expected a number")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("expected a number") from None
        _check_range(number, self.min, self.max)
        return number

    def restore(self, value: Any) -> float:
        """Convert a saved number without enforcing bounds."""
        return float(value)

    def to_frontend(self, current: Any) -> dict[str, Any]:
        """Return min, max and step when declared."""
        return {k: v for k, v in (("min", self.min), ("max", self.max), ("step", self.step)) if v is not None}


@dataclass(frozen=True)
class IntegerOption(OptionType[int]):
    """A whole number with optional bounds; fractional input is rejected rather than truncated."""

    FRONTEND_TYPE: ClassVar[str] = "number"
    min: int | None = None
    max: int | None = None
    step: int = 1

    def consume(self, value: Any) -> int:
        """Accept integers, whole floats and integer strings within the bounds."""
        if isinstance(value, bool):
            raise ValueError("expected a whole number")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("expected a whole number") from None
        if not number.is_integer():
            raise ValueError("expected a whole number")
        _check_range(number, self.min, self.max)
        return int(number)

    def restore(self, value: Any) -> int:
        """Convert a saved whole number without enforcing bounds."""
        return int(value)

    def to_frontend(self, current: Any) -> dict[str, Any]:
        """Return min, max and step."""
        extras: dict[str, Any] = {"step": self.step}
        if self.min is not None:
            extras["min"] = self.min
        if self.max is not None:
            extras["max"] = self.max
        return extras


@dataclass(frozen=True)
class BooleanOption(OptionType[bool]):
    """A true/false switch; the strings "true"/"false" and 1/0 are understood."""

    FRONTEND_TYPE: ClassVar[str] = "boolean"

    def consume(self, value: Any) -> bool:
        """Accept booleans, 0/1 and true/false strings."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str) and value.strip().lower() in ("true", "false", "1", "0"):
            return value.strip().lower() in ("true", "1")
        raise ValueError("expected true or false")


@dataclass(frozen=True)
class DropdownOption(OptionType[str]):
    """A fixed or runtime-computed list of choices; a saved value no longer listed stays selectable."""

    FRONTEND_TYPE: ClassVar[str] = "select"
    options: tuple[Choice, ...] | Callable[[], tuple[Choice, ...]] = ()

    def choices(self) -> tuple[Choice, ...]:
        """Return the current choices, computing them when they are provided as a function."""
        return tuple(self.options()) if callable(self.options) else self.options

    def consume(self, value: Any) -> str:
        """Accept only a listed choice."""
        text = "" if value is None else str(value)
        if text not in {choice.value for choice in self.choices()}:
            raise ValueError(f"'{text}' is not an available choice")
        return text

    def restore(self, value: Any) -> str:
        """Keep a saved value even when it is no longer listed."""
        return "" if value is None else str(value)

    def to_frontend(self, current: Any) -> dict[str, Any]:
        """Return the choices, adding the current value if it is not among them so it stays visible."""
        listed = [{"label": choice.label, "value": choice.value} for choice in self.choices()]
        if current not in ("", None) and all(item["value"] != current for item in listed):
            listed.append({"label": str(current), "value": str(current)})
        return {"options": listed}


@dataclass
class ConfigField(Generic[ValueT]):
    """One declared setting: its option type, default and current value."""

    name: str
    value: ValueT
    option: OptionType[ValueT]
    label: str
    default: ValueT
    required: bool = False
    help: str | None = None

    def set_value(self, raw: Any) -> None:
        """Validate and store a newly submitted value."""
        value = self.option.consume(raw)
        if self.required and value == "":
            raise ValueError("is required")
        self.value = value

    def to_frontend(self) -> dict[str, Any]:
        """Return this field's Settings-page schema entry; password values are reported only as set or not set."""
        is_password = isinstance(self.option, TextOption) and self.option.password
        entry: dict[str, Any] = {
            "key": self.name,
            "label": self.label,
            "type": self.option.frontend_type(),
            "value": "" if is_password else self.value,
            "default": "" if is_password else self.default,
            "required": self.required,
        }
        if is_password:
            entry["is_set"] = bool(self.value)
        if self.help:
            entry["help"] = self.help
        entry.update(self.option.to_frontend(self.value))
        return entry


def setting(label: str, option: OptionType[Any], default: ConfigValue, required: bool = False, help: str | None = None) -> Any:
    """Declare a ModelConfig attribute; every config instance receives its own field and option objects."""
    return field(default_factory=lambda: ConfigField(
        name="",
        value=default,
        option=copy.deepcopy(option),
        label=label,
        default=default,
        required=required,
        help=help,
    ))


@dataclass
class ModelConfig:
    """Base class for provider settings; subclasses only declare their fields with setting()."""

    CONFIG_FILE: ClassVar[str] = ""
    PROVIDER: ClassVar[str] = ""
    TITLE: ClassVar[str] = ""

    def __post_init__(self) -> None:
        """Name each declared field after its attribute."""
        for declared in fields(self):
            config_field = getattr(self, declared.name)
            if isinstance(config_field, ConfigField):
                config_field.name = declared.name

    def get_fields(self) -> list[ConfigField[Any]]:
        """Return the declared fields in declaration order."""
        return [getattr(self, declared.name) for declared in fields(self) if isinstance(getattr(self, declared.name), ConfigField)]

    @classmethod
    def load(cls) -> "ModelConfig":
        """Read the provider's JSON file, creating it with defaults when missing; malformed JSON raises and is left untouched."""
        path = CONFIG_DIR / cls.CONFIG_FILE
        if not path.is_file():
            config = cls()
            config.save()
            return config
        with open(path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        if not isinstance(data, dict):
            raise ValueError(f"{cls.CONFIG_FILE} must contain a JSON object")
        return cls.from_json(data)

    def save(self) -> None:
        """Write the current values to the provider's JSON file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_DIR / self.CONFIG_FILE, "w", encoding="utf-8") as config_file:
            json.dump(self.to_json(), config_file, indent=2)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "ModelConfig":
        """Build a config from saved values; unknown keys are ignored and missing keys keep their defaults."""
        config = cls()
        for config_field in config.get_fields():
            if config_field.name in data:
                try:
                    config_field.value = config_field.option.restore(data[config_field.name])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{cls.CONFIG_FILE}: invalid value for '{config_field.name}': {exc}") from None
        return config

    def to_json(self) -> dict[str, ConfigValue]:
        """Return the values keyed by field name, as saved to disk."""
        return {config_field.name: config_field.value for config_field in self.get_fields()}

    def from_frontend(self, settings: Mapping[str, Any]) -> "ModelConfig":
        """Apply submitted Settings-page values; omitted and unknown keys are left alone, and nothing changes if any value is invalid."""
        by_name = {config_field.name: config_field for config_field in self.get_fields()}
        staged: list[tuple[ConfigField[Any], ConfigField[Any]]] = []
        for key, raw in settings.items():
            if key not in by_name:
                continue
            candidate = copy.copy(by_name[key])
            try:
                candidate.set_value(raw)
            except ValueError as exc:
                raise ValueError(f"{candidate.label}: {exc}") from None
            staged.append((by_name[key], candidate))
        for target, candidate in staged:
            target.value = candidate.value
        return self

    def to_frontend(self) -> dict[str, Any]:
        """Return the Settings-page schema: provider id, title and one entry per field."""
        return {
            "provider": self.PROVIDER,
            "title": self.TITLE,
            "fields": [config_field.to_frontend() for config_field in self.get_fields()],
        }
