from pydantic import BaseModel

class ClickRequest(BaseModel):
    x: int
    y: int

class TypeRequest(BaseModel):
    text: str

class ScrollRequest(BaseModel):
    amount: int

class CalibrationRequest(BaseModel):
    width: int
    height: int
    dpi: int
