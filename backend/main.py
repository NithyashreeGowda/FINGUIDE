from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth
import profile
from database import init_indexes

app = FastAPI(title="FinGuide API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(profile.settings_router)
app.include_router(profile.conv_router)


@app.on_event("startup")
def startup():
    init_indexes()


@app.get("/health")
def health():
    return {"ok": True}