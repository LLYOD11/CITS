from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.models.models import Ticket, User, Client, Activity, CollaborationTask, TicketStatus, Priority, Tier, ClientTier
import random

class IntelligenceEngine:
    @staticmethod
    def gather_auto_context(ticket: Ticket, db: Session) -> Dict[str, Any]:
        context = {"gathered_at": datetime.utcnow().isoformat(), "sources": []}
        if ticket.category in ["Infrastructure", "Database", "Performance"]:
            context["logs"] = {
                "application": f"Error rate spike detected at {datetime.utcnow().strftime('%H:%M')}",
                "infrastructure": "CPU usage: 87%, Memory: 92%",
                "recent_deployment": "v2.4.1 deployed 2 hours ago"
            }
            context["sources"].append("system_logs")
        if ticket.category in ["Security", "Auth"]:
            context["security"] = {
                "failed_attempts": random.randint(5, 50),
                "affected_users": random.randint(10, 200),
                "last_successful_auth": (datetime.utcnow() - timedelta(minutes=random.randint(5, 60))).isoformat()
            }
            context["sources"].append("security_logs")
        if ticket.client_id:
            client = db.query(Client).filter(Client.id == ticket.client_id).first()
            if client:
                recent_tickets = db.query(Ticket).filter(Ticket.client_id == client.id, Ticket.id != ticket.id).order_by(Ticket.created_at.desc()).limit(5).all()
                context["client_history"] = {
                    "tier": client.tier.value, "contract_value": client.contract_value,
                    "recent_tickets": len(recent_tickets), "satisfaction_trend": "stable"
                }
                context["sources"].append("client_database")
        related = db.query(Ticket).filter(Ticket.category == ticket.category, Ticket.id != ticket.id, Ticket.created_at > datetime.utcnow() - timedelta(days=7)).order_by(Ticket.created_at.desc()).limit(3).all()
        if related:
            context["related_incidents"] = [{"id": r.id, "title": r.title, "resolved": r.status == TicketStatus.RESOLVED} for r in related]
            context["sources"].append("incident_database")
        return context

    @staticmethod
    def calculate_expertise_score(user: User, ticket: Ticket, db: Session) -> float:
        score = user.efficiency_score * 0.2
        for skill in (user.skills or []):
            if skill.get("name", "").lower() in ticket.category.lower() or ticket.category.lower() in skill.get("name", "").lower():
                count = skill.get("count", 0)
                level_multiplier = {"expert": 2.0, "growing": 1.2, "beginner": 0.8}.get(skill.get("level", ""), 1.0)
                score += min(count * 0.5, 50) * level_multiplier
        if ticket.client_id:
            client = db.query(Client).filter(Client.id == ticket.client_id).first()
            if client and client.tier in [ClientTier.VIP, ClientTier.ENTERPRISE]:
                vip_activities = db.query(Activity).filter(Activity.user_id == user.id, Activity.category == "vip_resolution").count()
                score += min(vip_activities * 2, 30)
        load_ratio = user.current_load / user.max_capacity if user.max_capacity > 0 else 1
        load_factor = 1 - (load_ratio * 0.6)
        score *= max(load_factor, 0.3)
        recent_activity = db.query(Activity).filter(Activity.user_id == user.id, Activity.category == ticket.category, Activity.created_at > datetime.utcnow() - timedelta(days=7)).order_by(Activity.created_at.desc()).first()
        if recent_activity: score += 15
        return round(score, 2)

    @staticmethod
    def find_best_assignee(ticket: Ticket, db: Session, tier_preference: Optional[Tier] = None) -> Optional[User]:
        query = db.query(User).filter(User.status.in_(["available", "busy"]), User.current_load < User.max_capacity)
        if tier_preference: query = query.filter(User.tier == tier_preference)
        if ticket.priority in [Priority.P0, Priority.P1]:
            if ticket.client_id:
                client = db.query(Client).filter(Client.id == ticket.client_id).first()
                if client and client.tier in [ClientTier.VIP, ClientTier.ENTERPRISE]:
                    t2_users = query.filter(User.tier == Tier.T2).all()
                    if t2_users:
                        scored = [(u, IntelligenceEngine.calculate_expertise_score(u, ticket, db)) for u in t2_users]
                        scored.sort(key=lambda x: x[1], reverse=True)
                        return scored[0][0] if scored else None
        users = query.all()
        if not users: return None
        scored = [(u, IntelligenceEngine.calculate_expertise_score(u, ticket, db)) for u in users]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    @staticmethod
    def find_collaboration_partner(requester: User, db: Session) -> Optional[User]:
        return db.query(User).filter(User.tier == Tier.T1, User.id != requester.id, User.status == "available", User.current_load < 3).order_by(User.current_load.asc()).first()

    @staticmethod
    def predict_breach_risk(ticket: Ticket) -> Dict[str, Any]:
        if not ticket.sla_deadline: return {"risk": "unknown", "confidence": 0}
        time_remaining = ticket.sla_deadline - datetime.utcnow()
        hours_remaining = time_remaining.total_seconds() / 3600
        risk_factors = []; risk_score = 0
        if ticket.priority == Priority.P0 and hours_remaining < 0.5:
            risk_score += 50; risk_factors.append("P0 with < 30 min remaining")
        elif ticket.priority == Priority.P1 and hours_remaining < 1:
            risk_score += 40; risk_factors.append("P1 with < 1 hour remaining")
        elif hours_remaining < ticket.sla_hours * 0.2:
            risk_score += 30; risk_factors.append("Less than 20% SLA remaining")
        if not ticket.assignee_id:
            risk_score += 20; risk_factors.append("Not yet assigned")
        if risk_score >= 50: return {"risk": "critical", "confidence": min(risk_score, 95), "factors": risk_factors}
        elif risk_score >= 30: return {"risk": "high", "confidence": risk_score, "factors": risk_factors}
        elif risk_score >= 15: return {"risk": "medium", "confidence": risk_score, "factors": risk_factors}
        else: return {"risk": "low", "confidence": max(100 - risk_score, 80), "factors": []}

    @staticmethod
    def should_auto_resolve(ticket: Ticket) -> bool:
        if ticket.priority in [Priority.P0, Priority.P1]: return False
        auto_resolvable_categories = ["Password Reset", "Access Request", "Routine Provisioning"]
        auto_resolvable_keywords = ["password", "reset", "access request", "unlock account"]
        if ticket.category in auto_resolvable_categories: return True
        title_lower = ticket.title.lower()
        for keyword in auto_resolvable_keywords:
            if keyword in title_lower: return True
        return False

intelligence = IntelligenceEngine()
