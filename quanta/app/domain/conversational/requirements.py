from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.domain.financial_profile.models import FinancialProfile


class QuestionRequirement(BaseModel):
    """
    Reusable representation of a missing information or workflow question.
    """

    model_config = ConfigDict(frozen=True)

    field_name: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    why_required: str = Field(min_length=1)
    input_type: str = Field(default="text")  # "monetary", "select", "text", "date"
    is_optional: bool = False
    allowed_options: list[str] | None = None
    accepts_natural_language: bool = True
    accepts_batch: bool = True


class FinancialProfileRequirementManager:
    """
    Determines missing or unconfirmed planning requirements for a user's FinancialProfile.
    """

    PROFILE_QUESTIONS: ClassVar[dict[str, QuestionRequirement]] = {
        "monthly_income": QuestionRequirement(
            field_name="monthly_income",
            question_text="What is your approximate monthly income?",
            why_required="Required to establish your total monthly budget capacity.",
            input_type="monetary",
            is_optional=False,
        ),
        "income_frequency": QuestionRequirement(
            field_name="income_frequency",
            question_text="How frequently do you receive income? (monthly, biweekly, weekly, irregular)",
            why_required="Required to align your spending schedule with your cash flow.",
            input_type="select",
            allowed_options=["monthly", "biweekly", "weekly", "irregular"],
            is_optional=False,
        ),
        "employment_type": QuestionRequirement(
            field_name="employment_type",
            question_text="Is your income salaried, freelance, self-employed, or another type?",
            why_required="Helps assess income stability when creating your budget plan.",
            input_type="select",
            allowed_options=["salaried", "self_employed", "freelance", "unemployed", "other"],
            is_optional=False,
        ),
        "fixed_expenses": QuestionRequirement(
            field_name="fixed_expenses",
            question_text="What are your fixed monthly expenses (such as rent, utilities, or recurring bills)?",
            why_required="Required to ensure essential obligations are covered before discretionary spending.",
            input_type="monetary",
            is_optional=False,
        ),
        "variable_expenses": QuestionRequirement(
            field_name="variable_expenses",
            question_text="Approximately how much do you spend on variable expenses (food, transport, entertainment) monthly?",
            why_required="Helps set realistic category limits for day-to-day spending.",
            input_type="monetary",
            is_optional=False,
        ),
        "savings_target": QuestionRequirement(
            field_name="savings_target",
            question_text="What is your monthly savings target?",
            why_required="Ensures a portion of income is allocated toward your savings goals.",
            input_type="monetary",
            is_optional=False,
        ),
    }

    @classmethod
    def get_missing_requirements(
        cls,
        profile: FinancialProfile,
        confirmed_fields: set[str] | None = None,
    ) -> list[QuestionRequirement]:
        """
        Identify profile fields that are missing or unconfirmed.
        Default 0.00 / unconfirmed values are considered missing until confirmed by user.
        """
        confirmed = confirmed_fields or set()
        missing: list[QuestionRequirement] = []

        # monthly_income must be > 0 or explicitly confirmed
        if profile.monthly_income <= 0 and "monthly_income" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["monthly_income"])

        if "income_frequency" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["income_frequency"])

        if "employment_type" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["employment_type"])

        if profile.fixed_expenses <= 0 and "fixed_expenses" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["fixed_expenses"])

        if profile.variable_expenses <= 0 and "variable_expenses" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["variable_expenses"])

        if profile.savings_target <= 0 and "savings_target" not in confirmed:
            missing.append(cls.PROFILE_QUESTIONS["savings_target"])

        return missing
