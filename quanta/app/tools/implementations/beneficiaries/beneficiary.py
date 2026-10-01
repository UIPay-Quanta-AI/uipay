from __future__ import annotations

from pydantic import BaseModel, Field

from app.clients.ui_pay.base import UIPayClient
from app.core.context import RequestContext
from app.tools.base import (
    Tool,
    ToolClassification,
    ToolResult,
)


class SearchBeneficiaryInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=100,
    )


class Beneficiary(BaseModel):
    id: str = Field(min_length=1)
    nickname: str | None = None
    account_name: str = Field(min_length=1)
    bank_name: str = Field(min_length=1)
    account_number: str = Field(min_length=1)


class SearchBeneficiaryOutput(BaseModel):
    # Echoes the tool's own validated input back out. Safe to round-trip to
    # the LLM (unlike raw tool-call arguments) because it already passed
    # through SearchBeneficiaryInput's validation, same as everything else
    # this tool returns.
    query: str
    beneficiaries: list[Beneficiary]


class SearchBeneficiaryTool(Tool[SearchBeneficiaryInput, SearchBeneficiaryOutput]):
    name = "search_beneficiary"

    description = (
        "Search the authenticated user's saved beneficiaries by nickname or recipient name."
    )

    classification = ToolClassification.READ

    input_model = SearchBeneficiaryInput
    output_model = SearchBeneficiaryOutput

    def __init__(self, *, client: UIPayClient) -> None:
        self._client = client

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: SearchBeneficiaryInput,
    ) -> ToolResult:
        beneficiaries = await self._client.search_beneficiaries(
            user_id=context.user_id,
            query=arguments.query,
        )

        output = SearchBeneficiaryOutput(
            query=arguments.query,
            beneficiaries=[Beneficiary.model_validate(item) for item in beneficiaries],
        )

        return ToolResult(
            success=True,
            data=output.model_dump(mode="json"),
        )
