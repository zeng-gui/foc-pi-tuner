"""FastAPI应用主文件。

配置静态文件服务、CORS和路由。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.routes import tune, chat

# 静态文件目录
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="FOC PI参数整定工具",
    description="PMSM电机PI参数整定Web API",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tune.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# 静态文件服务
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """根路由，返回index.html。"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "FOC PI参数整定工具 API"}
