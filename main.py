from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routers import tickets, users, clients, dashboard
from app.models.models import Base
from app.models import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CITS — Collaborative Intelligence Ticketing System",
              description="Employee-first smart ticketing with AI-powered routing, collaboration, and automation", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(tickets.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def root(): return {"message": "CITS API is running", "docs": "/docs", "version": "1.0.0"}

@app.get("/health")
def health(): return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
