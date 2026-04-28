from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import get_db
from app.models.models import Ticket, User, Client, Activity, CollaborationTask, TicketStatus, Priority, ClientTier
from app.schemas import DashboardStats, InsightItem
from app.services.intelligence import intelligence

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    vip_active = db.query(Ticket).join(Client).filter(Client.tier.in_([ClientTier.VIP, ClientTier.ENTERPRISE]), Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])).count()
    auto_resolved = db.query(Ticket).filter(Ticket.auto_resolved == True, Ticket.resolved_at >= today).count()
    collab_events = db.query(CollaborationTask).filter(CollaborationTask.created_at >= today).count()
    at_risk = 0
    for ticket in db.query(Ticket).filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])).all():
        risk = intelligence.predict_breach_risk(ticket)
        if risk["risk"] in ["critical", "high"]: at_risk += 1
    week_ago = datetime.utcnow() - timedelta(days=7)
    resolved = db.query(Ticket).filter(Ticket.status == TicketStatus.RESOLVED, Ticket.resolved_at >= week_ago).all()
    avg_time = 0
    if resolved:
        total_hours = sum([(t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved if t.resolved_at])
        avg_time = round(total_hours / len(resolved), 1)
    total_users = db.query(User).count()
    overloaded = db.query(User).filter(User.current_load >= User.max_capacity).count()
    flow_score = round(((total_users - overloaded) / total_users) * 100, 1) if total_users > 0 else 100
    return DashboardStats(vip_active=vip_active, team_flow_score=flow_score, auto_resolved_today=auto_resolved,
                          collaboration_events=collab_events, at_risk_count=at_risk, avg_resolution_time=avg_time)

@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    queue = []
    for ticket in db.query(Ticket).filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])).order_by(Ticket.priority, Ticket.created_at).all():
        risk = intelligence.predict_breach_risk(ticket)
        assignee = db.query(User).filter(User.id == ticket.assignee_id).first()
        client = db.query(Client).filter(Client.id == ticket.client_id).first()
        queue.append({"id": ticket.id, "title": ticket.title, "priority": ticket.priority.value, "status": ticket.status.value,
                      "category": ticket.category, "client_name": client.name if client else "Unknown",
                      "client_tier": client.tier.value if client else "standard",
                      "assignee_name": assignee.name if assignee else "Unassigned", "assignee_id": assignee.id if assignee else None,
                      "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
                      "breach_risk": risk, "auto_context": ticket.auto_context, "context_compiled": ticket.context_compiled,
                      "created_at": ticket.created_at.isoformat(), "handoff_from": ticket.handoff_from, "handoff_to": ticket.handoff_to})
    return queue

@router.get("/team")
def get_team_status(db: Session = Depends(get_db)):
    team = []
    for user in db.query(User).all():
        recent_resolved = db.query(Activity).filter(Activity.user_id == user.id, Activity.action == "resolved", Activity.created_at >= datetime.utcnow() - timedelta(days=7)).count()
        team.append({"id": user.id, "name": user.name, "tier": user.tier.value, "role": user.role, "avatar_initials": user.avatar_initials,
                     "status": user.status, "current_load": user.current_load, "max_capacity": user.max_capacity,
                     "efficiency_score": user.efficiency_score, "skills": user.skills, "weekly_resolved": recent_resolved})
    return team

@router.get("/collaborations")
def get_collaborations(db: Session = Depends(get_db)):
    events = []
    for task in db.query(CollaborationTask).filter(CollaborationTask.status.in_(["pending", "in_progress"])).order_by(CollaborationTask.created_at.desc()).all():
        ticket = db.query(Ticket).filter(Ticket.id == task.ticket_id).first()
        assigned_to = db.query(User).filter(User.id == task.assigned_to).first()
        assigned_by = db.query(User).filter(User.id == task.assigned_by).first()
        events.append({"id": task.id, "type": task.task_type, "description": task.description,
                       "from_user": assigned_by.name if assigned_by else "System", "to_user": assigned_to.name if assigned_to else "Unknown",
                       "ticket_title": ticket.title if ticket else "Unknown", "created_at": task.created_at.isoformat()})
    return events

@router.get("/insights")
def get_insights(db: Session = Depends(get_db)):
    insights = []
    overloaded = db.query(User).filter(User.current_load >= User.max_capacity).all()
    if overloaded:
        names = ", ".join([u.name for u in overloaded[:2]])
        insights.append(InsightItem(icon="⚠️", title="Capacity Alert", description=f"{names} and others are at max capacity. Consider redistributing load.", type="warning"))
    urgent_unassigned = db.query(Ticket).filter(Ticket.priority.in_([Priority.P0, Priority.P1]), Ticket.assignee_id == None, Ticket.status == TicketStatus.OPEN).count()
    if urgent_unassigned > 0:
        insights.append(InsightItem(icon="🚨", title="Urgent Tickets Unassigned", description=f"{urgent_unassigned} P0/P1 tickets need immediate assignment.", type="warning"))
    for user in db.query(User).all():
        skills = user.skills or []
        growing_skills = [s for s in skills if s.get("level") == "growing"]
        if growing_skills and user.current_load < 3:
            insights.append(InsightItem(icon="📈", title="Growth Opportunity", description=f"{user.name} is growing in {growing_skills[0]['name']}. Assign matching tickets to level up.", type="success"))
            break
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    auto_count = db.query(Ticket).filter(Ticket.auto_resolved == True, Ticket.resolved_at >= today).count()
    if auto_count > 0:
        insights.append(InsightItem(icon="🤖", title="Automation Working", description=f"CITS auto-resolved {auto_count} tickets today, saving ~{auto_count * 15} minutes of manual work.", type="success"))
    vip_breached = db.query(Ticket).join(Client).filter(Client.tier.in_([ClientTier.VIP, ClientTier.ENTERPRISE]), Ticket.breached == True).count()
    if vip_breached == 0:
        insights.append(InsightItem(icon="🛡️", title="VIP Shield Active", description="All VIP tickets within SLA. Smart routing is protecting high-value clients.", type="success"))
    return insights
