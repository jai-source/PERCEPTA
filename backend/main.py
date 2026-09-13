from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from api.routes import router as api_router
    from api.websocket import router as ws_router
except ImportError:
    from backend.api.routes import router as api_router
    from backend.api.websocket import router as ws_router

try:
    from api.websocket import get_processor
except ImportError:
    from backend.api.websocket import get_processor


@asynccontextmanager
async def lifespan(_app: FastAPI):
    started = asyncio.get_running_loop().time()
    active_processor = await get_processor()
    elapsed = asyncio.get_running_loop().time() - started
    loaded = [provider.model_name for provider in (active_processor.provider, active_processor.hand_provider, active_processor.face_provider) if provider.loaded]
    print(f"PERCEPTA backend ready: models loaded [{', '.join(loaded) or 'none'}] in {elapsed:.2f}s", flush=True)
    print("PERCEPTA websocket ready: ws://localhost:8000/ws", flush=True)
    yield

app = FastAPI(title="PERCEPTA Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
