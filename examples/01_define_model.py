"""L1.1 example: pure domain, no credentials, no provider SDK."""

from pyllmkit.domain.models import (
    Model,
    ModelFamily,
    ModelId,
    ModelIdentity,
    ModelVersion,
    model_to_dict,
)

model = Model(
    id=ModelId("example/llm/2026-10"),
    identity=ModelIdentity(
        family=ModelFamily("example-llm"),
        version=ModelVersion("2026-10"),
    ),
)
print(model_to_dict(model))
