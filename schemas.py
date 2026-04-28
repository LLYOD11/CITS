from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    P0 = "p0"; P1 = "p1"; P2 = "p2"; P3 = "p3"
class TicketStatus(str, Enum):
    OPEN = "open"; IN_PROGRESS = "in_progress"; PENDING = "pending"; RESOLVED = "resolved"; CLOSED = "closed"
class Tier(str, Enum):
    T1 = "t1"; T2 = "t2"; T3 = "t3"
class ClientTier(str, Enum):
    STANDARD = "standard"; PREMIUM = "premium"; VIP = "vip"; ENTERPRISE = "enterprise"

class UserBase(BaseModel):
    name: str; email: str; tier: Tier = Tier.T1; role: str = "SDM"; avatar_initials: str = "XX"
    max_capacity: int = 5; status: str = "available"; efficiency_score: float = 85.0; skills: List[Dict[str, Any]] = []
class UserCreate(UserBase): pass
class UserResponse(UserBase):
    id: int; current_load: int; created_at: datetime
    class Config: from_attributes = True

class ClientBase(BaseModel):
    name: str; tier: ClientTier = ClientTier.STANDARD; contract_value: float = 0.0; escalation_contact: Optional[str] = None
class ClientCreate(ClientBase): pass
class ClientResponse(ClientBase):
    id: int; created_at: datetime
    class Config: from_attributes = True

class TicketBase(BaseModel):
    title: str; description: Optional[str] = None; priority: Priority = Priority.P3; category: str = "General"; client_id: Optional[int] = None
class TicketCreate(TicketBase): pass
class TicketResponse(BaseModel):
    id: int; title: str; description: Optional[str]; priority: Priority; status: TicketStatus; category: str
    sla_hours: float; sla_deadline: Optional[datetime]; breached: bool; resolved_at: Optional[datetime]
    assignee_id: Optional[int]; client_id: Optional[int]; auto_context: Dict[str, Any]; context_compiled: bool
    auto_resolved: bool; auto_resolution_reason: Optional[str]; handoff_from: Optional[int]; handoff_to: Optional[int]
    handoff_reason: Optional[str]; created_at: datetime; updated_at: datetime
    class Config: from_attributes = True
class TicketDetail(TicketResponse):
    assignee: Optional[UserResponse]; client: Optional[ClientResponse]

class AssignmentRequest(BaseModel):
    ticket_id: int; user_id: Optional[int] = None
class HandoffRequest(BaseModel):
    ticket_id: int; from_user_id: int; to_user_id: int; reason: Optional[str] = None
class ContextTaskRequest(BaseModel):
    ticket_id: int; assigned_to: int; assigned_by: int; description: Optional[str] = None

class DashboardStats(BaseModel):
    vip_active: int; team_flow_score: float; auto_resolved_today: int; collaboration_events: int; at_risk_count: int; avg_resolution_time: float
class InsightItem(BaseModel):
    icon: str; title: str; description: str; type: str = "info"
