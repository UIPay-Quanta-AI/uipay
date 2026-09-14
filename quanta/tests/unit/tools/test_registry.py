import pytest

from app.tools.base import (
    ToolNotFoundError,
)
from app.tools.registry import ToolRegistry
from tests.unit.tools.test_base import (
    DummyTool,
)


def test_registry_starts_empty():
    registry = ToolRegistry()

    assert len(registry) == 0
    assert registry.names() == []


def test_register_tool():
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    assert len(registry) == 1
    assert registry.has("dummy_tool")
    assert registry.get("dummy_tool") is tool


def test_registry_rejects_duplicate_tool():
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_registry_rejects_unknown_tool():
    registry = ToolRegistry()

    with pytest.raises(
        ToolNotFoundError,
        match="Tool not found",
    ):
        registry.get("does_not_exist")


def test_registry_definitions():
    registry = ToolRegistry()
    registry.register(DummyTool())

    definitions = registry.definitions()

    assert len(definitions) == 1
    assert definitions[0]["name"] == "dummy_tool"
