import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Try connecting to MySQL if configured, else fall back gracefully to local SQLite
default_mysql_url = "mysql+pymysql://root:Akena123akena.@localhost:3306/hardware_world"
target_url = os.getenv("DATABASE_URL", default_mysql_url)

try:
    if target_url.startswith("mysql"):
        test_engine = create_engine(target_url, pool_pre_ping=True)
        with test_engine.connect() as conn:
            pass
        SQLALCHEMY_DATABASE_URL = target_url
        engine = test_engine
    else:
        SQLALCHEMY_DATABASE_URL = target_url
        connect_args = {"check_same_thread": False} if "sqlite" in target_url else {}
        engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
except Exception:
    # Graceful local SQLite fallback
    SQLALCHEMY_DATABASE_URL = "sqlite:///./hardware_world.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

