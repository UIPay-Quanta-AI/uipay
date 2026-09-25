from __future__ import annotations

import json
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.context import RequestContext
from app.schemas.transfer import TransferPreparation
from app.tools.base import (
    Tool,
    ToolClassification,
    ToolResult,
)


class PrepareTransferInput(BaseModel):
    """
    Arguments the LLM may provide.

    Currency is intentionally absent: the application always uses NGN and
    the LLM must not be able to set or override it.
    """

    beneficiary_id: str = Field(min_length=1)
    amount: int = Field(gt=0)


class PrepareTransferOutput(BaseModel):
    reference: str
    beneficiary_id: str
    amount: int
    currency: str


class PrepareTransferTool(Tool[PrepareTransferInput, PrepareTransferOutput]):
    """
    Prepare a transfer for user confirmation.

    This tool validates and structures the proposed transfer but never
    executes or authorises a financial transaction.  Execution is reserved
    for the UI Pay authorisation workflow that runs after the user provides
    their PIN / biometric.

    Currency is always NGN – it is set here by the application, not by the
    LLM.
    """

    name = "prepare_transfer"

    description = (
        "Prepare a transfer of Nigerian Naira (NGN) to a saved beneficiary. "
        "Validates and structures the proposed transfer for the user to review "
        "and confirm. Does NOT execute or authorise any financial transaction."
    )

    classification = ToolClassification.WRITE
    input_model = PrepareTransferInput
    output_model = PrepareTransferOutput

    # Currency is application-controlled.  The LLM never decides this.
    _CURRENCY = "NGN"

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: PrepareTransferInput,
    ) -> ToolResult:
        preparation = TransferPreparation(
            reference=f"prep-{uuid4().hex[:8]}",
            beneficiary_id=arguments.beneficiary_id,
            amount=arguments.amount,
            currency=self._CURRENCY,
        )

        return ToolResult(
            success=True,
            data=json.loads(preparation.model_dump_json()),
        )
