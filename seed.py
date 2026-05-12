from app.models import SessionLocal
from app.models.models import User, Client, Tier, ClientTier

def seed_data():
    db = SessionLocal()
    if db.query(User).count() > 0: db.close(); return
    users = [
        User(name="Sarah Chen", email="sarah.llyod@company.com", tier=Tier.T2, role="Senior SDM", avatar_initials="SC", efficiency_score=96.0,
             skills=[{"name": "Database", "count": 47, "level": "expert"}, {"name": "Infrastructure", "count": 32, "level": "expert"}, {"name": "Cloud AWS", "count": 15, "level": "growing"}], current_load=3, status="busy"),
        User(name="Marcus Johnson", email="marcus.ll@company.com", tier=Tier.T1, role="SDM", avatar_initials="MJ", efficiency_score=91.0,
             skills=[{"name": "API", "count": 38, "level": "expert"}, {"name": "Performance", "count": 29, "level": "expert"}, {"name": "Node.js", "count": 12, "level": "growing"}], current_load=5, status="busy"),
        User(name="Alex Rivera", email="alex.ll.yod@company.com", tier=Tier.T1, role="SDM", avatar_initials="AR", efficiency_score=87.0,
             skills=[{"name": "Security", "count": 22, "level": "expert"}, {"name": "Auth", "count": 18, "level": "expert"}, {"name": "OAuth2", "count": 8, "level": "growing"}], current_load=2, status="available"),
        User(name="Priya Patel", email="priya.llyod@company.com", tier=Tier.T1, role="Junior SDM", avatar_initials="PP", efficiency_score=82.0,
             skills=[{"name": "Backend", "count": 15, "level": "growing"}, {"name": "Reports", "count": 12, "level": "growing"}, {"name": "Python", "count": 6, "level": "beginner"}], current_load=2, status="available"),
        User(name="David Kim", email="david.llyod@company.com", tier=Tier.T3, role="Engineering Lead", avatar_initials="DK", efficiency_score=95.0,
             skills=[{"name": "Infrastructure", "count": 55, "level": "expert"}, {"name": "Database", "count": 40, "level": "expert"}, {"name": "Kubernetes", "count": 30, "level": "expert"}], current_load=1, status="available"),
    ]
    for user in users: db.add(user)
    clients = [
        Client(name="Stripe Enterprise", tier=ClientTier.ENTERPRISE, contract_value=2400000.0, escalation_contact="cto@stripe.com"),
        Client(name="Acme Corp", tier=ClientTier.VIP, contract_value=850000.0, escalation_contact="ops@acme.com"),
        Client(name="TechFlow Inc", tier=ClientTier.VIP, contract_value=620000.0, escalation_contact="support@techflow.io"),
        Client(name="BetaSoft", tier=ClientTier.PREMIUM, contract_value=180000.0),
        Client(name="StartupXYZ", tier=ClientTier.STANDARD, contract_value=24000.0),
    ]
    for client in clients: db.add(client)
    db.commit(); db.close()
    print("Seed data created!")

if __name__ == "__main__":
    seed_data()
