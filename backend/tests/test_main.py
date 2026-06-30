import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models

# Use memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_task():
    # Test task creation route
    due = (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).isoformat()
    response = client.post(
        "/api/tasks/",
        json={
            "title": "Test urgent task",
            "description": "Needs decomposition",
            "due_date": due,
            "priority": "High",
            "estimated_hours": 2.0,
            "category": "Work"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test urgent task"
    assert data["priority"] == "High"
    assert data["panic_index"] > 0.0

def test_multi_agent_event_bus():
    # Verify that creating a task automatically runs the planner (populating subtasks)
    # and prediction engine (calculating success probability)
    due = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).isoformat()
    response = client.post(
        "/api/tasks/",
        json={
            "title": "Build hackathon dashboard UI",
            "description": "Must feature circular gauges and agent logs",
            "due_date": due,
            "priority": "Urgent",
            "estimated_hours": 1.5,
            "category": "Work"
        }
    )
    assert response.status_code == 201
    data = response.json()
    
    # Subtasks should be populated by the Planner Agent
    assert len(data["subtasks"]) > 0
    assert data["completion_probability"] > 0.0
    
    # Verification of explainable AI fields
    assert data["impact"] in ["High", "Medium", "Low"]
    assert data["ai_reasoning"] is not None

def test_negotiation_draft():
    # Let's retrieve generated drafts from the negotiation endpoint
    response = client.get("/api/negotiation/drafts")
    assert response.status_code == 200
    drafts = response.json()
    assert isinstance(drafts, list)
