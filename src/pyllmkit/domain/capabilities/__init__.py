"""Domain Capability primitives - declarations only, no provider integration."""

from .collection import CapabilitySet
from .model import Capability, CapabilityConstraint, CapabilityId, CapabilitySupport, SupportLevel

__all__ = [
    "Capability", "CapabilityId", "CapabilitySupport", "CapabilityConstraint",
    "SupportLevel", "CapabilitySet",
]
