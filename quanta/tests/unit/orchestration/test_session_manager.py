from app.domain.conversational.session import SessionManager, SessionState


def test_session_manager_singleton_and_get():
    mgr = SessionManager()
    session = mgr.get_session(session_id="sess_1", user_id="user_1")
    assert session.session_id == "sess_1"
    assert session.user_id == "user_1"
    assert session.active_workflow is None

    # Retrieve existing session
    session2 = mgr.get_session(session_id="sess_1", user_id="user_1")
    assert session2 is session


def test_session_state_reset():
    session = SessionState(session_id="sess_2", user_id="user_2")
    session.active_workflow = "TRANSFER"
    session.collected_data["bank"] = "GTBank"

    session.reset_workflow()
    assert session.active_workflow is None
    assert len(session.collected_data) == 0
