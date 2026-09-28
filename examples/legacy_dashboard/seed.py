from database import SessionLocal, engine, Base
from models import PullRequest


# Tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)


db = SessionLocal()


# Xóa dữ liệu cũ nếu có
db.query(PullRequest).delete()


data = [

    PullRequest(
        status="Approved",
        reviewer="Nguyen A",
        review_score=90,
        risk_score=20,
        review_time=3
    ),

    PullRequest(
        status="Open",
        reviewer="Nguyen B",
        review_score=70,
        risk_score=60,
        review_time=5
    ),

    PullRequest(
        status="Rejected",
        reviewer="Nguyen A",
        review_score=50,
        risk_score=85,
        review_time=8
    ),

    PullRequest(
        status="Merged",
        reviewer="Nguyen C",
        review_score=95,
        risk_score=10,
        review_time=2
    )

]


db.add_all(data)

db.commit()

db.close()


print("Database created successfully")