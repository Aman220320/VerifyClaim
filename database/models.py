from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from database import Base

class Applicant(Base):
    __tablename__ = "applicants"
    
    id = Column(Integer, primary_key=True, index=True)
    ssn_last4 = Column(String(4), index=True)
    employer = Column(String(100))
    separation_reason = Column(String)
    separation_embedding = Column(Vector(768))
    earnings = Column(Float)
    employment_months = Column(Integer)
    status = Column(String(20))
    fraud_score = Column(Float)
    decision_reason = Column(String)
    created_at = Column(DateTime, default=func.now())

class FraudPattern(Base):
    __tablename__ = "fraud_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), index=True)
    embedding = Column(Vector(768))
    severity = Column(Integer)

class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(50), unique=True, index=True)
    condition = Column(String)
    message = Column(String)

class ClaimHistory(Base):
    __tablename__ = "claim_history"
    id = Column(Integer, primary_key=True, index=True)
    ssn_last4 = Column(String(4), index=True)
    claim_date = Column(DateTime)
    employer = Column(String(100))
    embedding = Column(Vector(768)) 