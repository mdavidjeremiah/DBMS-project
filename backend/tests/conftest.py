import os
import secrets
import sys
from pathlib import Path
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
sys.path.insert(0, str(Path(__file__).parents[1]))
