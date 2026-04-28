from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON, Enum
from sqlalchemy.orm import relationship
from . import Base
from datetime import datetime
import enum

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Priority(str, enum.Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"

class Tier(str, enum.Enum):
    T1 = "t1"
    T2 = "t2"
    T3 = "t3"

class ClientTier(str, enum.Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    VIP = "vip"
    ENTERPRISE = "enterprise"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    tier = Column(Enum(Tier), default=Tier.T1)
    role = Column(String, default="SDM")
    avatar_initials = Column(String, default="XX")
    current_load = Column(Integer, default=0)
    max_capacity = Column(Integer, default=5)
    status = Column(String, default="available")
    efficiency_score = Column(Float, default=85.0)
    skills = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee")
    activities = relationship("Activity", back_populates="user")

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    tier = Column(Enum(ClientTier), default=ClientTier.STANDARD)
    contract_value = Column(Float, default=0.0)
    escalation_contact = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    tickets = relationship("Ticket", back_populates="client")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    priority = Column(Enum(Priority), default=Priority.P3)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    category = Column(String, default="General")
    sla_hours = Column(Float, default=8.0)
    sla_deadline = Column(DateTime)
    breached = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    auto_context = Column(JSON, default=dict)
    context_compiled = Column(Boolean, default=False)
    context_compiled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    handoff_from = Column(Integer, ForeignKey("users.id"), nullable=True)
    handoff_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    handoff_reason = Column(Text)
    auto_resolved = Column(Boolean, default=False)
    auto_resolution_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tickets")
    client = relationship("Client", back_populates="tickets")

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    action = Column(String)
    category = Column(String)
    time_spent = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="activities")

class CollaborationTask(Base):
    __tablename__ = "collaboration_tasks"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    task_type = Column(String)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    assigned_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

Base.metadata.create_all(bind=engine)
