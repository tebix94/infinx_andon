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
        # If shift is already started, limit the calculations to the current time
        if datetime_end > current_date_time:
            datetime_end = current_date_time

        # Fetch posts that matches the datetime parameters
        posts = Posts.query.filter(Posts.start_date < datetime_end, 
                                   or_(Posts.end_date > datetime_start, 
                                       Posts.end_date == None)).order_by(Posts.start_date).all()

    # Lists and variables for calculating invidivual posts downtime values
    machine_downtimes = [0] * len(machines)
    top_downtime_machine = ''
    top_downtime = 0

     # Variables for tracking the whole shift/day downtime value
    total_downtime = 0
    last_end_time = None

    for post in posts:

        # Start calculating the downtime of individual posts
        calc_start = max(post.start_date, datetime_start)

        if post.end_date:
            calc_end = min(post.end_date, datetime_end)
        else:
            time_upper_limit = current_date_time if datetime_start <= current_date_time < datetime_end else datetime_end
            calc_end = min(time_upper_limit, datetime_end)

        downtime_minutes = int((calc_end - calc_start).total_seconds() / 60)
        if downtime_minutes < 0:
            downtime_minutes = 0

        if post.machine_id is not None and 0 < post.machine_id <= len(machine_downtimes):
            machine_downtimes[post.machine_id - 1] += downtime_minutes

        # Start accumulating the downtime of the whole post
        line_start = max(post.start_date, datetime_start)
        line_end = calc_end # calc_end is delimited with the frontend filters

        if last_end_time is None:
            # Calculate first post donwtime and add it to the total downtime time accumulator
            total_downtime += int((line_end - line_start).total_seconds() / 60)
            last_end_time = line_end
        else:
            # If current post lapse time does not overlaps with the last post lapse time
            if line_start > last_end_time:
                total_downtime += int((line_end - line_start).total_seconds() / 60)
                last_end_time = line_end
            # If current post lapse time partially overlaps with the last post lapse time
            elif line_end > last_end_time:
                total_downtime += int((line_end - last_end_time).total_seconds() / 60)
                last_end_time = line_end

    # Set data for the pie chart
    pie_labels = [machine_names[i] for i in range(len(machine_downtimes)) if machine_downtimes[i] > 0]
    pie_data = [time for time in machine_downtimes if time > 0]

    # Get top downtime machine name
    for i in range(len(machine_downtimes)):
        if machine_downtimes[i] > top_downtime:
            top_downtime = machine_downtimes[i]
            top_downtime_machine = machine_names[i]

    # If no data for the pie chart, lets set defaults
    if not pie_data:
        pie_labels = ["Sin incidentes"]
        pie_data = [0]

    return render_template(
        'metrics.html',
        total_minutes=total_downtime,
        total_incidents=len(posts),
        top_downtime_machine=top_downtime_machine,
        bar_labels=machine_names,
        bar_data=machine_downtimes,
        pie_labels=pie_labels,
        pie_data=pie_data,
        selected_date=date_base.strftime('%Y-%m-%d'),
    )