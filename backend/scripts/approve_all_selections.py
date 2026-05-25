"""One-off: set all active course selections to APPROVED."""
from app.core.database import SessionLocal
from app.modules.course_selections.models import CourseSelection

db = SessionLocal()
n = (
    db.query(CourseSelection)
    .filter(CourseSelection.is_deleted == False, CourseSelection.status != "APPROVED")
    .update({"status": "APPROVED"}, synchronize_session=False)
)
db.commit()
print(f"updated {n} rows")
