import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine, SessionLocal
from database.models import Applicant, FraudPattern, EligibilityRule, ClaimHistory

def init_db():
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize eligibility rules
    with SessionLocal() as db:
        rules = [
            EligibilityRule(
                rule_name="min_employment",
                condition="employment_months >= 6",
                message="Minimum 6 months employment required"
            ),
            EligibilityRule(
                rule_name="min_earnings",
                condition="earnings >= 3000",
                message="Minimum $3,000 earnings in base period"
            ),
            EligibilityRule(
                rule_name="voluntary_quit",
                condition="'quit' not in separation_reason.lower() and 'resigned' not in separation_reason.lower()",
                message="Voluntary separations not eligible"
            ),
            EligibilityRule(
                rule_name="employer_blacklist",
                condition="employer not in ['Fake Corp', 'Fraud LLC', 'Shell Co', 'Quick Temp']",
                message="Employer verification failed"
            ),
            EligibilityRule(
                rule_name="excessive_earnings",
                condition="earnings <= 15000",
                message="Earnings exceed reasonable threshold"
            )
        ]
        
        for rule in rules:
            db.add(rule)
        
        db.commit()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db() 