from __future__ import annotations

from abc import ABC


class ProviderError(Exception):
    """
    Base exception for provider-related failures.

    Provider-specific implementations should raise subclasses of this
    exception rather than leaking third-party exceptions into the
    orchestration layer.
    """


class Provider(ABC):
    """
    Base interface for all Quanta providers.

    Concrete providers should expose a stable interface to the rest
    of the application and hide provider-specific implementation details.
    """
