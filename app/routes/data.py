from flask import Blueprint, request, render_template, redirect, jsonify
from sqlalchemy import or_
from app.models import Posts, Machines
from datetime import datetime, timedelta
from app.extensions import db
import calendar
from collections import defaultdict

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
    machine_downtimes = defaultdict(dict)
    machine_incidents = [0] * len(machines)
    machines_incidents_startdate = [0] * len(machines)
    machine_fault_status = [False] * len(machines)
    top_downtime_machine = ''
    top_downtime = 0

     # Variables for tracking the whole shift/day downtime value
    total_downtime = 0
    last_end_time = None

    for post in posts:
        # Correct index value, all machine related lists starts at position 0.
        idx = post.machine_id - 1

        # Build status map
        if post.end_date == None:
            machine_fault_status[idx] = True

        # Start calculating the downtime of individual posts
        calc_start = max(post.start_date, datetime_start)

        # Store the date of the day that event occurs, this will be forwarded to the metrics template, later JS
        # will use this value to sent it back to the backend as history view request argument
        machines_incidents_startdate[idx] = post.start_date.date() if machines_incidents_startdate[idx] == 0 else machines_incidents_startdate[idx]
        if post.end_date:
            calc_end = min(post.end_date, datetime_end)
        else:
            time_upper_limit = current_date_time if datetime_start <= current_date_time < datetime_end else datetime_end
            calc_end = min(time_upper_limit, datetime_end)

        downtime_minutes = int((calc_end - calc_start).total_seconds() / 60)
        if downtime_minutes < 0:
            downtime_minutes = 0

        if post.machine_id is not None:
            if post.interruption_id not in machine_downtimes[post.machine_id]:
                machine_downtimes[post.machine_id][post.interruption_id] = 0
            machine_downtimes[post.machine_id][post.interruption_id] += downtime_minutes
            machine_incidents[idx] += 1

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

    # Get top downtime machine name
    for i in range(len(machine_names)):
        idx = i + 1
        if isinstance(machine_downtimes[idx], dict) and (machine_downtimes[idx].get(1, 0) + machine_downtimes[idx].get(2, 0)) > top_downtime:
            top_downtime = machine_downtimes[idx].get(1, 0) + machine_downtimes[idx].get(2, 0)
            top_downtime_machine = machine_names[i]

    # Set data for the pie chart
    print(machine_downtimes)
    pie_labels = [machine_names[i - 1] for i in machine_downtimes if isinstance(machine_downtimes[i], dict) and machine_downtimes[i].get(1, 0) + machine_downtimes[i].get(2, 0) > 0]
    pie_data = [machine_downtimes[i].get(1, 0) + machine_downtimes[i].get(2, 0) for i in machine_downtimes if isinstance(machine_downtimes[i], dict) and machine_downtimes[i].get(1, 0) + machine_downtimes[i].get(2, 0) > 0]

    # If no data for the pie chart, lets set defaults
    if not pie_data:
        pie_labels = ["Sin incidentes"]
        pie_data = [0]

    # Merge pie labels and data in a single structure (to avoid front end to change items order during render)
    pie_items = [{"label": l, "value": v} for l, v in zip(pie_labels, pie_data)]
    pie_items.sort(key=lambda x: x["value"], reverse=True)
        
    # Render data for client request by JS (Ajax)
    if request.args.get('format') == 'json':
        return jsonify({
            'total_minutes': total_downtime,
            'total_incidents': len(posts),
            'top_downtime_machine': top_downtime_machine,
            'machine_names': machine_names,
            'machine_data': machine_downtimes,
            'machine_incidents': machine_incidents,
            'machine_incidents_startdate': machines_incidents_startdate, 
            'machine_fault_status': machine_fault_status,
            'pie_items': pie_items,
            }
        )

    # Render data for client request by URL
    return render_template(
        'data/metrics.html',
        total_minutes=total_downtime,
        total_incidents=len(posts),
        top_downtime_machine=top_downtime_machine,
        machine_names=machine_names,
        machine_data=machine_downtimes,
        machine_incidents=machine_incidents,
        machine_incidents_startdate=machines_incidents_startdate,
        machine_fault_status=machine_fault_status,
        pie_items=pie_items,
    )

@bp.route('/performance')
def performance():
    # Fetch arguments from the front end request
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', None, type=int)
    machine_id = request.args.get('machine_id', 'all')
    format_type = request.args.get('format', 'html')

    # Use calendar module to define last day of the month
    if month:
        start_date = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
    else:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)

    # Fetch machines objects from database
    query = Machines.query.options(db.joinedload(Machines.posts))
    if machine_id != 'all':
        query = query.filter(Machines.id == machine_id)
    
    # List of machines filtered by frontend machine selector filter
    machines = query.all()
    # Get a list of all machines for rendering the frontend
    all_machines = Machines.query.all()

    # Initialize chart datasets
    datasets = []

    # Create date list just for rendering days at front end
    days_list = []
    current = start_date
    while current <= end_date:
        days_list.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    # Verify the dates that contains data
    days_with_data = set()
    for machine in machines:
        for post in machine.posts:
            if start_date <= post.start_date <= end_date:
                days_with_data.add(post.start_date.strftime('%Y-%m-%d'))

    # Exclude days without data
    days_list = sorted([day for day in days_list if day in days_with_data])

    # Loop on each post from each machine to sum the downtime duration in minutes
    for machine in machines:
        # Dictionary format {'date string': 'minutes integer value'}
        downtime_map = {day: 0 for day in days_list}

        # Filter posts that matches the template date selectors and the machine
        posts = [post for post in machine.posts if start_date <= post.start_date <= end_date]

        # Get downtime per post and sum posts downtimes that belongs to the same day
        for post in posts:
            # Get time string from date time to be used as key inside the downtime map
            date_str = post.start_date.strftime('%Y-%m-%d')

            # Get post time duration
            time_delta = (post.end_date - post.start_date).total_seconds() / 60 if post.end_date else 0
            
            # Add delta time to the each date key in the downtime ma
            downtime_map[date_str] += time_delta

        # Convert downtime structure to flat list
        datapoints = [downtime_map[day] for day in days_list]

        datasets.append({
            'label': machine.name,
            'data': datapoints,
            'fill': False,
            'tension': 0.3
        })

    if format_type == 'json':
        return jsonify({
            'labels': days_list,
            'datasets': datasets
        })

    return render_template('data/performance.html', 
                           years=range(2023, datetime.now().year + 1),
                           current_year=year,
                           current_month=month,
                           machines=all_machines,)