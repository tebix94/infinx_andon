import os
import secrets
from datetime import datetime
from dotenv import load_dotenv

# Import objects and methods
from flask import Flask
from .extensions import db
from werkzeug.serving import is_running_from_reloader

# Import scheduler and related modules
from flask_apscheduler import APScheduler
from app.background_tasks import run_background_tasks

# Import routes
from app.routes.base import bp as bp_home
from app.routes.auth import bp as bp_auth
from app.routes.post import bp as bp_post
from app.routes.data import bp as bp_data
from app.routes.settings import bp as bp_settings

# Load enviroment variables
load_dotenv()

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
    app.register_blueprint(bp_settings, url_prefix='/settings/')
  
    # Start background tasks
    if not is_running_from_reloader():
        scheduler.start()
        run_background_tasks(scheduler)
        
    return app