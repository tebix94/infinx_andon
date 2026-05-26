import os
import secrets

# Import objects and methods
from flask import Flask
from .extensions import db

# Import routes
from app.routes.base import bp as bp_home
from app.routes.auth import bp as bp_auth
from app.routes.post import bp as bp_post

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
    #login_manager.init_app(app=app)

    # Add routes
    app.register_blueprint(bp_home)
    app.register_blueprint(bp_auth, url_prefix='/auth')
    app.register_blueprint(bp_post, url_prefix='/post/')

    return app