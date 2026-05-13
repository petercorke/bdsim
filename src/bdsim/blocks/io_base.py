"""Shared interfaces for realtime I/O backends.

This module intentionally contains no block classes.  It provides a small
provider protocol that generic I/O blocks can use to bind to a backend chosen
by the realtime runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, ClassVar, Protocol, runtime_checkable


class IOProviderError(RuntimeError):
    """Raised when a runtime I/O provider cannot satisfy a block request."""


class MissingIOProviderError(IOProviderError):
    """Raised when a diagram uses I/O blocks without a configured provider."""


class UnsupportedIOBlockError(IOProviderError):
    """Raised when a provider does not implement a requested I/O primitive."""


@runtime_checkable
class AnalogInputHandle(Protocol):
    def read(self) -> Any:
        """Return the current analog input sample."""


@runtime_checkable
class AnalogOutputHandle(Protocol):
    def write(self, value: Any) -> None:
        """Write the current analog output sample."""


@runtime_checkable
class DigitalInputHandle(Protocol):
    def read(self) -> Any:
        """Return the current digital input sample."""


@runtime_checkable
class DigitalOutputHandle(Protocol):
    def write(self, value: Any) -> None:
        """Write the current digital output sample."""


@dataclass(frozen=True)
class IOBlockSpec:
    """Resolved configuration for one logical I/O block instance."""

    block_type: str
    channel: Any
    device: str | None = None
    options: dict[str, Any] | None = None


class IOProvider:
    """Base class for concrete hardware/OS-specific realtime I/O providers.

    Subclasses can implement whichever primitives they support.  Generic
    blocks call these factory methods during ``start()`` and then retain the
    returned handle for ``output()`` or ``step()``.
    """

    name = "base"
    aliases: ClassVar[tuple[str, ...]] = ()
    _registry: ClassVar[dict[str, type["IOProvider"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        name = getattr(cls, "name", None)
        if not isinstance(name, str) or name in {"", "base"}:
            return

        keys = [name, *getattr(cls, "aliases", ())]
        for key in keys:
            normalized = str(key).strip().lower()
            if not normalized:
                continue
            existing = IOProvider._registry.get(normalized)
            if existing is not None and existing is not cls:
                raise ValueError(
                    f"duplicate I/O provider key {normalized!r}: "
                    f"{existing.__name__} and {cls.__name__}"
                )
            IOProvider._registry[normalized] = cls

    @classmethod
    def _load_builtin_providers(cls) -> None:
        # Import known provider modules once so subclasses can self-register.
        for module_name in (
            "bdsim.blocks.io_mock",
            "bdsim.blocks.io_firmata",
            "bdsim.blocks.io_arduio",
        ):
            try:
                importlib.import_module(module_name)
            except Exception:
                continue

    @classmethod
    def create(cls, provider: str, **kwargs: Any) -> "IOProvider":
        cls._load_builtin_providers()
        key = provider.strip().lower()
        impl = cls._registry.get(key)
        if impl is None:
            known = ", ".join(sorted(cls._registry))
            raise IOProviderError(
                f"unknown I/O provider {provider!r}; known providers: {known}"
            )
        return impl(**kwargs)

    @classmethod
    def registered_names(cls) -> tuple[str, ...]:
        cls._load_builtin_providers()
        return tuple(sorted(cls._registry))

    def open_analog_input(self, spec: IOBlockSpec) -> AnalogInputHandle:
        raise UnsupportedIOBlockError(
            f"provider {self.name} does not support analog input"
        )

    def open_analog_output(self, spec: IOBlockSpec) -> AnalogOutputHandle:
        raise UnsupportedIOBlockError(
            f"provider {self.name} does not support analog output"
        )

    def open_digital_input(self, spec: IOBlockSpec) -> DigitalInputHandle:
        raise UnsupportedIOBlockError(
            f"provider {self.name} does not support digital input"
        )

    def open_digital_output(self, spec: IOBlockSpec) -> DigitalOutputHandle:
        raise UnsupportedIOBlockError(
            f"provider {self.name} does not support digital output"
        )

    def close(self) -> None:
        """Release provider resources at runtime shutdown."""


def get_runtime_io_provider(runtime: Any) -> IOProvider:
    """Return the configured provider from a runtime object.

    The runtime side is expected to eventually supply either a dedicated
    ``get_io_provider()`` method or an ``io_provider`` attribute.  Keeping this
    adapter in one place lets the generic blocks stay stable while the runtime
    API is finalized.
    """

    if runtime is None:
        raise MissingIOProviderError("I/O blocks require a configured runtime")

    getter = getattr(runtime, "get_io_provider", None)
    if callable(getter):
        provider = getter()
    else:
        provider = getattr(runtime, "io_provider", None)

    if provider is None:
        raise MissingIOProviderError(
            "no I/O provider configured; supply one via the realtime runtime"
        )
    if not isinstance(provider, IOProvider):
        raise IOProviderError(
            f"configured I/O provider has unexpected type {type(provider)!r}"
        )
    return provider
