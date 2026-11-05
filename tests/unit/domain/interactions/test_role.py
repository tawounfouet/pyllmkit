"""L2.1 canonical Role taxonomy and rejection of invalid provider roles."""

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.interactions import Role


def test_five_canonical_roles_and_values() -> None:
    assert tuple(Role) == (
        Role.SYSTEM,
        Role.DEVELOPER,
        Role.USER,
        Role.ASSISTANT,
        Role.TOOL,
    )
    assert tuple(role.value for role in Role) == (
        "system",
        "developer",
        "user",
        "assistant",
        "tool",
    )


@pytest.mark.parametrize("raw", ["system", "developer", "user", "assistant", "tool"])
def test_explicit_role_parsing_accepts_canonical_values(raw: str) -> None:
    assert Role(raw).value == raw


@pytest.mark.parametrize("bad", ["", "moderator", "USER", "User", "human", None, 42, {}])
def test_unrecognized_role_is_not_silently_mapped(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="canonical interaction role"):
        Role(bad)
