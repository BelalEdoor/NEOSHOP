"""
core/database.py
================
إعداد قاعدة البيانات باستخدام SQLAlchemy.
يدعم MySQL (الإنتاج) و SQLite (التطوير) بدون تغيير في الكود.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

DATABASE_URL = settings.DATABASE_URL

# إعداد المحرك بحسب نوع قاعدة البيانات
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # MySQL مع connection pool احترافي
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency لإنشاء وإغلاق جلسة قاعدة البيانات في كل طلب."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
