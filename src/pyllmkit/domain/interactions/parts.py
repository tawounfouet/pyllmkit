"""Typed, provider-independent content part contract (ADR-010)."""

from abc import ABC, abstractmethod

from pyllmkit.domain.modalities import Modality


class ContentPart(ABC):
    """Semantic content-part interface, distinct from providers and capabilities.

    Concrete parts provide an explicit kind and an M1 Modality. Serialization
    support for a kind is a separate decision; this base performs no I/O.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def kind(self) -> str:
        """Canonical content kind used by an explicit future codec."""

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """Describe content modality, without inferring model capabilities."""
