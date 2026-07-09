from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.api.routes_books import router as books_router
from pipeline.api.routes_chunks import router as chunks_router
from pipeline.api.routes_conversations import router as conversations_router
from pipeline.api.routes_import import router as import_router
from pipeline.api.routes_status import router as status_router

app = FastAPI(title="BookAgent API")
# Tauri 前端跨源调用本地服务：生产打包后是 tauri://localhost（Windows 上是
# http://tauri.localhost），`npm run tauri dev` 开发模式下 Vite 默认跑在
# http://localhost:1420 —— 三个来源都要放行，否则浏览器 fetch 会被 CORS 拦掉。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地桌面应用，安全风险为零——仅监听 127.0.0.1，外网不可达
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(status_router)
app.include_router(books_router)
app.include_router(import_router)
app.include_router(conversations_router)
app.include_router(chunks_router)
