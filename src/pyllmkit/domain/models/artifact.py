"""Physical model artifact Entity, independent of Deployment/Endpoint."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .descriptors import ModelRevision
from .identifiers import ModelArtifactId, ModelId, require_nonblank


@dataclass(frozen=True, slots=True, eq=False)
class ModelArtifact:
    """Identified physical representation of a logical Model (INV-004)."""

    id: ModelArtifactId
    model_id: ModelId
    format: str
    precision: str | None = None
    quantization: str | None = None
    size_bytes: int | None = None
    source: str | None = None
    checksum: str | None = None
    revision: ModelRevision | None = None

    __hash__ = None  # type: ignore[assignment]  # Entities are unhashable

    def __post_init__(self) -> None:
        if not isinstance(self.id, ModelArtifactId):
            raise DomainValidationError("id must be ModelArtifactId")
        if not isinstance(self.model_id, ModelId):
            raise DomainValidationError("model_id must be ModelId")
        require_nonblank(self.format, "format")
        for field in ("precision", "quantization", "source", "checksum"):
            value = getattr(self, field)
            if value is not None:
                require_nonblank(value, field)
        if self.size_bytes is not None and (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes < 0
        ):
            raise DomainValidationError("size_bytes must be a non-negative integer or None")
        if self.revision is not None and not isinstance(self.revision, ModelRevision):
            raise DomainValidationError("revision must be ModelRevision or None")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModelArtifact) and self.id == other.id
