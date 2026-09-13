from .calibration_store import CalibrationStore

class Calibrator:
    def __init__(self, store: CalibrationStore):
        self.store = store

    def calibrate_screen(self, width: int, height: int, dpi: int) -> bool:
        self.store.set("screen", {
            "width": width,
            "height": height,
            "dpi": dpi
        })
        return True

    def get_screen_info(self) -> dict:
        return self.store.get("screen", {"width": 1920, "height": 1080, "dpi": 96})
