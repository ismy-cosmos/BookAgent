from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.api.routes_books import router as books_router
from pipeline.api.routes_chunks import router as chunks_router
from pipeline.api.routes_conversations import router as conversations_router
from pipeline.api.routes_import import router as import_router
from pipeline.api.routes_status import router as status_router

app = FastAPI(title="BookAgent API")
# 真正的 Tauri 窗口（webkit2gtk）走 @tauri-apps/plugin-http 发请求，不经过浏览器
# fetch，不受 CORS 约束。这条 CORS 配置是为了保留 `npx vite` 直接用浏览器打开
# http://localhost:1420 的开发方式（不用等 Rust 编译、不用启 Tauri 窗口）——
# 这条路径走的是浏览器原生 fetch，会被 CORS 拦，所以还要放行。
# 本地桌面应用只监听 127.0.0.1，外网不可达，全放行没有安全风险。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(status_router)
app.include_router(books_router)
app.include_router(import_router)
app.include_router(conversations_router)
app.include_router(chunks_router)
