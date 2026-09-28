from sqlalchemy import Column, Integer, String, Float
from database import Base

class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String)
    reviewer = Column(String)
    review_score = Column(Float)
    risk_score = Column(Float)
    review_time = Column(Float)
