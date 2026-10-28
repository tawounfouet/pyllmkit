"""L1.1 example: multiple physical artifacts for one logical model."""

from pyllmkit.domain.models import ModelArtifact, ModelArtifactId, ModelId

model_id = ModelId("example/llm/2026-10")
artifacts = [
    ModelArtifact(ModelArtifactId("fp16"), model_id, "safetensors", precision="FP16"),
    ModelArtifact(ModelArtifactId("q4"), model_id, "GGUF", quantization="Q4_K_M"),
]
for artifact in artifacts:
    print(artifact.id, "->", artifact.model_id)
