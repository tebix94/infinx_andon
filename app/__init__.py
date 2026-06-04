import os
import secrets
from dotenv import load_dotenv

# Import objects and methods
from flask import Flask
from .extensions import db

# Import scheduler
from flask_apscheduler import APScheduler

# Import routes
from app.routes.base import bp as bp_home
from app.routes.auth import bp as bp_auth
from app.routes.post import bp as bp_post
from app.routes.data import bp as bp_data

# Load enviroment variables
load_dotenv()
TELEGRAM_INFINX_GROUP_ID = os.environ.get('TELEGRAM_INFINX_GROUP_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Load scheduler
scheduler = APScheduler()

def start_app():
    # Create backend instance
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # Add secret key
    app.secret_key = secrets.token_hex()

    # Assign database
    basedir = os.path.abspath(os.path.dirname(__file__)) # This is the /app folder
    db_path = os.path.join(os.path.dirname(basedir), 'app.db')
    app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_path}'

    # Connect the app with the extensions
    db.init_app(app=app)
    scheduler.init_app(app=app)
    #login_manager.init_app(app=app)

    # Add routes
    app.register_blueprint(bp_home)
    app.register_blueprint(bp_auth, url_prefix='/auth')
    app.register_blueprint(bp_post, url_prefix='/post/')
    app.register_blueprint(bp_data)

    # Start background tasks
    scheduler.start()
    
    with app.app_context():
        scheduler.add_job(
            id='telegram_update_report',
            func='app.background_tasks:background_task_telegram_status_report',
            args=[app, TELEGRAM_BOT_TOKEN, TELEGRAM_INFINX_GROUP_ID],
            trigger='cron',
            minute=0,    # Run exactly at the 0th minute of every hour
            second=0     # Optional: ensures it runs at the very start of the minute
        )

    return app