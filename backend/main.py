from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.rag_api import router as rag_router
import auth
import user_profile
from database import init_indexes

app = FastAPI(title="FinGuide API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user_profile.router)
app.include_router(user_profile.settings_router)
app.include_router(user_profile.conv_router)
app.include_router(rag_router)


@app.on_event("startup")
def startup():
    init_indexes()


@app.get("/health")
def health():
    return {"ok": True}