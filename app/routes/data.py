from flask import Blueprint, request, render_template
from sqlalchemy import or_
from app.models import Posts, Machines
from datetime import datetime, timedelta

bp = Blueprint('data', __name__)

@bp.route('/metrics')
def metrics(): 
    # Downtime is calculated in minutes

    # Fetch calendar data from the frontend
    template_date_string = request.args.get('date')
    template_shift_string = request.args.get('shift', 'day')

    # Define base date
    if template_date_string:
        try:
            # Convert string from request into a Python date object
            date_base = datetime.strptime(template_date_string, '%Y-%m-%d')
        except ValueError:
            date_base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        date_base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Shift selection
    if template_shift_string == '1':
        # 1st shift
        datetime_start = date_base.replace(hour=6, minute=0)
        datetime_end = date_base.replace(hour=15, minute=30)
    elif template_shift_string == '2':
        # 2nd shift
        datetime_start = date_base.replace(hour=15, minute=30)
        datetime_end = (date_base + timedelta(days=1)).replace(hour=0, minute=0)
    elif template_shift_string == '3':
        # 3rd shift
        datetime_start = date_base.replace(hour=0, minute=0)
        datetime_end = datetime_start + timedelta(hours=6)
    else:
        # Whole day
        datetime_start = date_base.replace(hour=0, minute=0, second=0)
        datetime_end = datetime_start + timedelta(days=1)

    # Fetch all machine names from the database and store them in a list
    machines = Machines.query.order_by(Machines.id).all()
    machine_names = [machine.name for machine in machines]

    # Fetch data from database
    current_date_time = datetime.now()

    # Lock future dates to avoid the calendar to extrapolate downtime values and set nulls instead
    if datetime_start > current_date_time:
        posts = []
        datetime_end = datetime_start # Forzar ventana de tiempo cero
    else:
        # If shift is already started, with limit the calculations to the current time
        if datetime_end > current_date_time:
            datetime_end = current_date_time

        # Fetch posts that matches the datetime parameters
        posts = Posts.query.filter(Posts.start_date < datetime_end, 
                                   or_(Posts.end_date > datetime_start, 
                                       Posts.end_date == None)).all()

    # Calculate all of our dashboard downtime metrics
    current_date_time = datetime.now()

    # Calculate downtimes and top offender
    machine_downtimes = [0] * len(machines)
    top_downtime_machine = ''
    top_downtime = 0

    for post in posts:
        calc_start = max(post.start_date, datetime_start)

        if post.end_date:
            downtime = post.end_date - calc_start
        else:
            time_upper_limit = current_date_time if datetime_start <= current_date_time < datetime_end else datetime_end
            downtime = time_upper_limit - calc_start

        downtime_minutes = int(downtime.total_seconds() / 60)
        
        # 1. Validar signo primero
        if downtime_minutes < 0:
            downtime_minutes = 0

        # 2. Sumar una única vez validando la existencia de la máquina
        if post.machine_id is not None and 0 < post.machine_id <= len(machine_downtimes):
            machine_downtimes[post.machine_id - 1] += downtime_minutes

    for i in range(len(machine_downtimes)):
        if machine_downtimes[i] > top_downtime:
            top_downtime = machine_downtimes[i]
            top_downtime_machine = machine_names[i]

    return render_template(
        'metrics.html',
        total_minutes=top_downtime,
        total_incidents=len(posts),
        top_downtime_machine=top_downtime_machine,
        bar_labels=machine_names,
        bar_data=machine_downtimes,
        pie_labels=machine_names,
        pie_data=machine_downtimes,
        selected_date=date_base.strftime('%Y-%m-%d'),
    )