from flask import Blueprint, render_template, jsonify
from app.models import Posts
from app import db
from sqlalchemy import func
from datetime import datetime

bp = Blueprint('base', __name__)

# Update count indicator on base menu when client request page from URL
@bp.app_context_processor
def inject_active_posts():
    count = Posts.query.filter(Posts.end_date == None).count()
    return dict(active_posts_count=count)

# JS requests asynchronously the count value which will be inserted in active_posts_count from the frontend side
@bp.route('/active-post-count')
def get_active_posts_count():
    count = Posts.query.filter(Posts.end_date == None).count()
    return jsonify(count=count)

@bp.route('/')
def home():
    status_map = {
        0: {"class": "bg-success text-white", "text": "Corriendo"},
        1: {"class": "bg-danger text-white", "text": "Mantenimiento"},
        2: {"class": "bg-danger text-white", "text": "Cambio de modelo"},
        3: {"class": "bg-orange text-white", "text": "Falta de material"},
        4: {"class": "bg-warning text-dark", "text": "Validación"},
        5: {"class": "bg-warning text-dark", "text": "Validación"},
    }
    
    # Check for active posts
    posts = Posts.query.filter(Posts.end_date == None).all()

    # Machine interruption map
    machines_interruption_map = [status_map[0].copy() for _ in range(16)]

    for post in posts:
        if post.machine_id and 0 <= post.machine_id < len(machines_interruption_map):
            status_data = status_map.get(post.interruption_id, status_map[0])
            machines_interruption_map[post.machine_id] = status_data

    return render_template('home.html', map=machines_interruption_map)