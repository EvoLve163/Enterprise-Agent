from langchain_core.tools import BaseTool


class ToolRegistry:
    """轻量工具注册中心，对应 Hello Agents 第7章的工具抽象思路。"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    @property
    def tools(self) -> list[BaseTool]:
        return list(self._tools.values())
