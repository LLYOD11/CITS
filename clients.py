from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models import get_db
from app.models.models import Client
from app.schemas import ClientCreate, ClientResponse

router = APIRouter(prefix="/clients", tags=["clients"])

@router.post("/", response_model=ClientResponse)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = Client(**client.dict()); db.add(db_client); db.commit(); db.refresh(db_client); return db_client

@router.get("/", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)): return db.query(Client).all()

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client: raise HTTPException(status_code=404, detail="Client not found")
    return client
