from app.domain.conversational.requirements import (
    FinancialProfileRequirementManager,
    QuestionRequirement,
)
from app.domain.financial_profile.models import FinancialProfile


def test_question_requirement_model():
    req = QuestionRequirement(
        field_name="monthly_income",
        question_text="What is your income?",
        why_required="To plan your budget.",
    )
    assert req.field_name == "monthly_income"
    assert req.input_type == "text"
    assert req.is_optional is False


def test_missing_requirements_unconfirmed_profile():
    profile = FinancialProfile(user_id="user_test")
    missing = FinancialProfileRequirementManager.get_missing_requirements(profile)
    assert len(missing) == 6
    fields = [m.field_name for m in missing]
    assert "monthly_income" in fields
    assert "income_frequency" in fields
    assert "employment_type" in fields
    assert "fixed_expenses" in fields
    assert "variable_expenses" in fields
    assert "savings_target" in fields


def test_missing_requirements_partially_confirmed():
    profile = FinancialProfile(user_id="user_test", monthly_income=500000)
    confirmed = {"monthly_income", "employment_type"}
    missing = FinancialProfileRequirementManager.get_missing_requirements(
        profile, confirmed_fields=confirmed
    )
    fields = [m.field_name for m in missing]
    assert "monthly_income" not in fields
    assert "employment_type" not in fields
    assert "fixed_expenses" in fields
