from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from rag.rag_api import router as rag_router
except Exception as e:
    rag_router = None
    print("RAG disabled:", e)
import auth
import user_profile
from database import init_indexes
from market_insights import router as insights_router, start_insights_worker
from market_news import router as news_router, start_news_worker, _db, _now
from history_tools import router as history_tools_router

app = FastAPI(title="FinGuide API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user_profile.router)
app.include_router(news_router)
app.include_router(user_profile.settings_router)
app.include_router(history_tools_router)
app.include_router(user_profile.conv_router)
app.include_router(insights_router)
if rag_router:
    app.include_router(rag_router)


@app.on_event("startup")
def startup():
    init_indexes()
    start_news_worker()
    start_insights_worker()


@app.get("/health")
def health():
    return {"ok": True}