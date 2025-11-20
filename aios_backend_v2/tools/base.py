from __future__ import annotations

import abc
from typing import Any, Dict, List


class Tool(abc.ABC):
    name: str
    description: str
    permissions: List[str] = []
    params_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    returns_schema: Dict[str, Any] = {"type": "object"}

    @abc.abstractmethod
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ...


def serialize_tool(tool: Tool) -> Dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "permissions": tool.permissions,
        "params_schema": tool.params_schema,
        "returns_schema": tool.returns_schema,
    }
