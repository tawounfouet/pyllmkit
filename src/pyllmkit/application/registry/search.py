"""No-network catalog read service; delegates typed queries to registry ports."""

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.models import Model
from pyllmkit.domain.registry import DeploymentQuery, ModelQuery
from pyllmkit.protocols import DeploymentRegistryPort, ModelRegistryPort


class CatalogSearchService:
    """Read-only application service; no SDK access or implicit provider mapping."""

    __slots__ = ("_models", "_deployments")

    def __init__(
        self, models: ModelRegistryPort, deployments: DeploymentRegistryPort
    ) -> None:
        self._models = models
        self._deployments = deployments

    def find_models(self, query: ModelQuery) -> tuple[Model, ...]:
        if not isinstance(query, ModelQuery):
            from pyllmkit.domain.errors import DomainValidationError

            raise DomainValidationError("find_models expects ModelQuery")
        return self._models.find(query)

    def find_deployments(self, query: DeploymentQuery) -> tuple[Deployment, ...]:
        if not isinstance(query, DeploymentQuery):
            from pyllmkit.domain.errors import DomainValidationError

            raise DomainValidationError("find_deployments expects DeploymentQuery")
        return self._deployments.find(query)
