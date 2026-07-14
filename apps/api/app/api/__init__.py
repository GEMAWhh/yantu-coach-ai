from app.api.assets import router as assets_router
from app.api.evidence import router as evidence_router
from app.api.imports import router as imports_router
from app.api.insights import router as insights_router
from app.api.knowledge import router as knowledge_router
from app.api.mastery import router as mastery_router
from app.api.planning import router as planning_router
from app.api.reviews import router as reviews_router
from app.api.time_calibration import router as time_calibration_router
from app.api.wrongbook import router as wrongbook_router

__all__ = [
    "assets_router",
    "evidence_router",
    "imports_router",
    "insights_router",
    "knowledge_router",
    "mastery_router",
    "planning_router",
    "reviews_router",
    "time_calibration_router",
    "wrongbook_router",
]
