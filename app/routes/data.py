from flask import Blueprint, request, render_template
from sqlalchemy import func
from app.models import Posts
from datetime import datetime, timedelta

bp = Blueprint('data', __name__)

@bp.route('/metrics')
def metrics(): 
    # Downtime is calculated in minutes

    # Initialize auxiliar lists and variables
    machine_downtimes = [0] * 15
    total_downtime = 0
    top_downtime_machine = 'None'
    top_downtime = 0

    machine_names = ['WAM Plug 1',
                  'WAM Plug 2',
                  'WAM Recepticle 1',
                  'WAM Recepticle 2',
                  'PAM',
                  'RAM',
                  'Ball Attached 3',
                  'Ball Attached 4',
                  'Ball Attached 5',
                  'Ball Attached 6',
                  'Ball Attached 7',
                  'Ball Attached 8',
                  'Ball Attached 10',
                  'Opti Vix',
                  'Shibuya',]

    # Set target date
    datetime_now = datetime.now()
    datetime_start = datetime_now.replace(hour=0, minute=0, second=0, microsecond=0)
    datetime_end = datetime_start + timedelta(days=1)

    # Fetch posts that matches the target date
    posts = Posts.query.filter((datetime_start <= Posts.start_date) & (Posts.start_date < datetime_end)).all()

    # Calculate all of our dashboard downtime metrics
    current_date_time = datetime.now()

    for post in posts:
        if post.end_date:
            downtime = post.end_date - post.start_date
        else:
            downtime = current_date_time - post.start_date

        downtime_minutes = int(downtime.total_seconds() / 60)
        machine_downtimes[post.machine_id] += downtime_minutes
        total_downtime += downtime_minutes

    for i in range(len(machine_downtimes)):
        if machine_downtimes[i] > top_downtime:
            top_downtime = machine_downtimes[i]
            top_downtime_machine = machine_names[i]

    return render_template(
        'metrics.html',
        total_minutes=total_downtime,
        total_incidents=len(posts),
        top_downtime_machine=top_downtime_machine,
        bar_labels=machine_names,
        bar_data=machine_downtimes,
        pie_labels=machine_names,
        pie_data=machine_downtimes,
    )