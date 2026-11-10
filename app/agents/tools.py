"""LangChain tools bound to a single validated upload, not arbitrary code or queries."""

from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict

from app.services.analytics import TOOLS, execute_tool
from app.services.validation import ValidatedData

DESCRIPTIONS = {
    "duplicates": "Find exact and possible duplicate invoices with source-row evidence.",
    "budget": "Reconcile monthly allocations and identify budget overruns or conflicts.",
    "anomalies": "Screen unusually high expense amounts using category IQR thresholds.",
    "missing_data": "Inspect missing fields, invalid financial records and duplicate identifiers.",
}


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["current_upload"] = "current_upload"


def build_tools(data: ValidatedData) -> dict[str, StructuredTool]:
    """Register deterministic checks; the agent has no control over data or SQL arguments."""

    def bind(name: str) -> StructuredTool:
        def run(scope: str = "current_upload") -> dict:
            return execute_tool(name, data).model_dump()

        return StructuredTool.from_function(
            run, name=name, description=DESCRIPTIONS[name], args_schema=NoArguments
        )

    return {name: bind(name) for name in TOOLS}
