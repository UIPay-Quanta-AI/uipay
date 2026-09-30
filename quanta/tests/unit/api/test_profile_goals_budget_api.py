from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_api_get():
    response = client.get(
        "/api/v1/profile",
        headers={"X-User-ID": "user_api_1", "X-Session-ID": "sess_1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user_api_1"


def test_profile_api_update():
    response = client.post(
        "/api/v1/profile",
        json={"updates": {"monthly_income": "450000.00"}},
        headers={"X-User-ID": "user_api_1", "X-Session-ID": "sess_1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_income"] == "450000.00"


def test_goals_api_create_and_get():
    # Create goal
    res_create = client.post(
        "/api/v1/goals",
        json={"name": "Vacation Fund", "target_amount": "200000.00"},
        headers={"X-User-ID": "user_api_2", "X-Session-ID": "sess_2"},
    )
    assert res_create.status_code == 200
    goal_data = res_create.json()
    assert goal_data["name"] == "Vacation Fund"

    # Get goals
    res_get = client.get(
        "/api/v1/goals",
        headers={"X-User-ID": "user_api_2", "X-Session-ID": "sess_2"},
    )
    assert res_get.status_code == 200
    goals_list = res_get.json()
    assert len(goals_list) >= 1
    assert any(g["name"] == "Vacation Fund" for g in goals_list)


def test_budget_api_generate_and_get():
    res_gen = client.post(
        "/api/v1/budget",
        json={"start_date": "2026-10-01", "end_date": "2026-10-31"},
        headers={"X-User-ID": "user_api_3", "X-Session-ID": "sess_3"},
    )
    assert res_gen.status_code == 200
    budget_data = res_gen.json()
    assert budget_data["user_id"] == "user_api_3"
    assert budget_data["status"] == "active"

    res_get = client.get(
        "/api/v1/budget",
        headers={"X-User-ID": "user_api_3", "X-Session-ID": "sess_3"},
    )
    assert res_get.status_code == 200
    current_budget = res_get.json()
    assert current_budget["id"] == budget_data["id"]
