"""ASGI app for the e2e only: the normal app with ScriptedFakeAI injected as the AI provider (no model calls).
Lives under tests/, not app/, so nothing in the deployed image can load it. scripts/e2e.sh runs it with
`uvicorn e2e_app:app --app-dir tests/e2e` from backend/."""
from app.main import create_app
from app.tender.scripted_ai import ScriptedFakeAI

app = create_app(ai=ScriptedFakeAI())
