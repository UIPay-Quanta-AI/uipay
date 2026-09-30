from app.core.context import RequestContext
from app.prompts.builder import build_quanta_system_prompt


def test_build_quanta_system_prompt():
    ctx = RequestContext.create(
        user_id="user_123",
        session_id="sess_456",
        operation="TEXT",
        locale="pcm",
    )
    prompt = build_quanta_system_prompt(
        context=ctx,
        active_workflow="FINANCIAL_PROFILE_SETUP",
        session_data={"monthly_income": 500000},
    )

    assert "Quanta" in prompt
    assert "user_123" in prompt
    assert "sess_456" in prompt
    assert "pcm" in prompt
    assert "FINANCIAL_PROFILE_SETUP" in prompt
    assert "500000" in prompt
    assert "YOU CANNOT EXECUTE TRANSFERS" in prompt
