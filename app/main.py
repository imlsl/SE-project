from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, blender

app = FastAPI(title="Smart City Generation System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(blender.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart City Generation System Backend!"}
