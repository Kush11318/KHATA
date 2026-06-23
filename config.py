import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '8b6f77032919654a2afbe29f4633be31'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Check if we can use the high-performance psycopg2 driver, fallback to pure Python pg8000
        try:
            import psycopg2
            driver = 'postgresql+psycopg2://'
        except ImportError:
            driver = 'postgresql+pg8000://'
            
        if DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', driver, 1).replace('postgresql://', driver, 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Default to SQLite if MySQL is not explicitly configured
        MYSQL_HOST = os.environ.get('MYSQL_HOST')
        MYSQL_PORT = os.environ.get('MYSQL_PORT')
        MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME')
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
        MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')
        
        if MYSQL_HOST or MYSQL_DATABASE:
            MYSQL_HOST = MYSQL_HOST or 'localhost'
            MYSQL_PORT = int(MYSQL_PORT or 3306)
            MYSQL_USERNAME = MYSQL_USERNAME or 'root'
            MYSQL_PASSWORD = MYSQL_PASSWORD or 'kush'
            MYSQL_DATABASE = MYSQL_DATABASE or 'inventory_db'
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        else:
            SQLALCHEMY_DATABASE_URI = 'sqlite:///inventory.db'
            
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options to prevent connection timeouts (especially for hosted PostgreSQL on Render)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True
    }
    
    # Other configurations
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
