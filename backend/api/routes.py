from fastapi import APIRouter
from .models import ClickRequest, TypeRequest, ScrollRequest, CalibrationRequest
try:
    from interaction.engine import InteractionEngine
    from calibration.calibrator import Calibrator
    from calibration.calibration_store import CalibrationStore
except ImportError:
    from ..interaction.engine import InteractionEngine
    from ..calibration.calibrator import Calibrator
    from ..calibration.calibration_store import CalibrationStore

router = APIRouter()
engine = InteractionEngine()
store = CalibrationStore()
calibrator = Calibrator(store)


@router.get("/health")
def health_check():
    """Lightweight readiness check used by the launcher and Docker."""
    return {"status": "ok", "service": "percepta-backend"}


@router.post("/interaction/click")
def perform_click(req: ClickRequest):
    success = engine.click(req.x, req.y)
    return {"success": success, "action": "click", "x": req.x, "y": req.y}

@router.post("/interaction/type")
def perform_type(req: TypeRequest):
    success = engine.type_text(req.text)
    return {"success": success, "action": "type", "text": req.text}

@router.post("/interaction/scroll")
def perform_scroll(req: ScrollRequest):
    success = engine.scroll(req.amount)
    return {"success": success, "action": "scroll", "amount": req.amount}

@router.post("/calibration")
def calibrate(req: CalibrationRequest):
    success = calibrator.calibrate_screen(req.width, req.height, req.dpi)
    return {"success": success, "action": "calibrate"}

@router.get("/calibration")
def get_calibration():
    return calibrator.get_screen_info()
