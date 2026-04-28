from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.models import get_db
from app.models.models import Ticket, User, Client, Activity, CollaborationTask, TicketStatus, Priority, Tier, ClientTier
from app.schemas import TicketCreate, TicketResponse, TicketDetail, AssignmentRequest, HandoffRequest, ContextTaskRequest
from app.services.intelligence import intelligence

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post("/", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    sla_map = {Priority.P0: 0.5, Priority.P1: 1.0, Priority.P2: 4.0, Priority.P3: 8.0}
    sla_hours = sla_map.get(ticket.priority, 8.0)
    if ticket.client_id:
        client = db.query(Client).filter(Client.id == ticket.client_id).first()
        if client and client.tier in [ClientTier.VIP, ClientTier.ENTERPRISE]: sla_hours *= 0.6
    db_ticket = Ticket(title=ticket.title, description=ticket.description, priority=ticket.priority,
                       category=ticket.category, client_id=ticket.client_id, sla_hours=sla_hours,
                       sla_deadline=datetime.utcnow() + timedelta(hours=sla_hours))
    db.add(db_ticket); db.commit(); db.refresh(db_ticket)
    db_ticket.auto_context = intelligence.gather_auto_context(db_ticket, db)
    if intelligence.should_auto_resolve(db_ticket):
        db_ticket.status = TicketStatus.RESOLVED; db_ticket.resolved_at = datetime.utcnow()
        db_ticket.auto_resolved = True; db_ticket.auto_resolution_reason = "Routine request auto-processed"
        db.add(Activity(ticket_id=db_ticket.id, action="auto_resolved", category=ticket.category, success=True))
    else:
        best_assignee = intelligence.find_best_assignee(db_ticket, db)
        if best_assignee:
            db_ticket.assignee_id = best_assignee.id; best_assignee.current_load += 1
            if best_assignee.current_load >= best_assignee.max_capacity: best_assignee.status = "busy"
            db.add(Activity(user_id=best_assignee.id, ticket_id=db_ticket.id, action="auto_assigned", category=ticket.category, success=True))
        if db_ticket.priority == Priority.P1:
            assignee = db.query(User).filter(User.id == db_ticket.assignee_id).first()
            if assignee and assignee.tier == Tier.T1:
                partner = intelligence.find_collaboration_partner(assignee, db)
                if partner:
                    db.add(CollaborationTask(ticket_id=db_ticket.id, task_type="context_compilation",
                                             assigned_to=partner.id, assigned_by=assignee.id,
                                             description=f"Compile context package for P1 ticket: {db_ticket.title}"))
    db.commit(); db.refresh(db_ticket); return db_ticket

@router.get("/", response_model=List[TicketDetail])
def list_tickets(status: str = None, priority: str = None, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if status: query = query.filter(Ticket.status == status)
    if priority: query = query.filter(Ticket.priority == priority)
    return query.order_by(Ticket.created_at.desc()).all()

@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/{ticket_id}/assign")
def assign_ticket(ticket_id: int, req: AssignmentRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.assignee_id:
        old_user = db.query(User).filter(User.id == ticket.assignee_id).first()
        if old_user:
            old_user.current_load = max(0, old_user.current_load - 1)
            if old_user.current_load < old_user.max_capacity: old_user.status = "available"
    if req.user_id:
        new_user = db.query(User).filter(User.id == req.user_id).first()
        if not new_user: raise HTTPException(status_code=404, detail="User not found")
        ticket.assignee_id = req.user_id; new_user.current_load += 1
        if new_user.current_load >= new_user.max_capacity: new_user.status = "busy"
    else:
        best = intelligence.find_best_assignee(ticket, db)
        if best: ticket.assignee_id = best.id; best.current_load += 1
    ticket.status = TicketStatus.IN_PROGRESS; db.commit()
    return {"message": "Ticket assigned", "ticket_id": ticket_id, "assignee_id": ticket.assignee_id}

@router.post("/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = TicketStatus.RESOLVED; ticket.resolved_at = datetime.utcnow()
    if ticket.assignee_id:
        user = db.query(User).filter(User.id == ticket.assignee_id).first()
        if user:
            user.current_load = max(0, user.current_load - 1)
            if user.current_load < user.max_capacity: user.status = "available"
            skills = user.skills or []; skill_found = False
            for skill in skills:
                if skill.get("name", "").lower() == ticket.category.lower():
                    skill["count"] = skill.get("count", 0) + 1
                    if skill["count"] > 20: skill["level"] = "expert"
                    elif skill["count"] > 10: skill["level"] = "growing"
                    skill_found = True; break
            if not skill_found: skills.append({"name": ticket.category, "count": 1, "level": "beginner"})
            user.skills = skills
            db.add(Activity(user_id=user.id, ticket_id=ticket.id, action="resolved", category=ticket.category, success=True))
    db.commit()
    return {"message": "Ticket resolved", "ticket_id": ticket_id}

@router.post("/{ticket_id}/handoff")
def handoff_ticket(ticket_id: int, req: HandoffRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.handoff_from = req.from_user_id; ticket.handoff_to = req.to_user_id; ticket.handoff_reason = req.reason
    from_user = db.query(User).filter(User.id == req.from_user_id).first()
    to_user = db.query(User).filter(User.id == req.to_user_id).first()
    if from_user:
        from_user.current_load = max(0, from_user.current_load - 1)
        if from_user.current_load < from_user.max_capacity: from_user.status = "available"
    if to_user:
        to_user.current_load += 1
        if to_user.current_load >= to_user.max_capacity: to_user.status = "busy"
    ticket.assignee_id = req.to_user_id
    db.add(Activity(user_id=req.from_user_id, ticket_id=ticket.id, action="handoff_from", category=ticket.category))
    db.add(Activity(user_id=req.to_user_id, ticket_id=ticket.id, action="handoff_to", category=ticket.category))
    db.commit()
    return {"message": "Handoff complete", "ticket_id": ticket_id}

@router.post("/{ticket_id}/context")
def compile_context(ticket_id: int, req: ContextTaskRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.context_compiled = True; ticket.context_compiled_by = req.assigned_to
    collab_task = db.query(CollaborationTask).filter(CollaborationTask.ticket_id == ticket_id, CollaborationTask.assigned_to == req.assigned_to).first()
    if collab_task: collab_task.status = "completed"; collab_task.completed_at = datetime.utcnow()
    db.commit()
    return {"message": "Context compiled", "ticket_id": ticket_id}
