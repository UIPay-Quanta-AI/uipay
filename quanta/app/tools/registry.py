from __future__ import annotations

from app.tools.base import Tool, ToolNotFoundError


class ToolRegistry:
    """
    Central registry of tools available to Quanta orchestration.

    The registry controls what capabilities exist.
    It does not make authorization decisions.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found: {name}") from exc

    def has(self, name: str) -> bool:
        return name in self._tools

    def definitions(self) -> list[dict]:
        """
        Return LLM-compatible definitions for registered tools.
        """
        return [tool.definition() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
