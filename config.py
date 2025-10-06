import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
    # Default to a SQLite DB inside the instance folder (Flask convention)
    basedir = os.path.abspath(os.path.dirname(__file__))
    default_db = f"sqlite:///{os.path.join(basedir, 'instance', 'site.db')}"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", default_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False