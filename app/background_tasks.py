import os
from filelock import FileLock, Timeout
from app.models import Machines, Posts
from app.telegram_bot import send_telegram_notification 
from datetime import datetime
from collections import defaultdict
from sqlalchemy import or_

def background_task_telegram_short_status_report(scheduler, only_downtime=False):
    # Cross-platform lock (works in Linux/WSL and Windows)
    lock = FileLock("infinx_telegram.lock")
    
    try:
        with lock.acquire(timeout=0):  # Non-blocking lock
            # Fetch environment variables
            token = os.environ.get('TELEGRAM_BOT_TOKEN')
            chat_id = os.environ.get('TELEGRAM_INFINX_GROUP_ID')
            
            with scheduler.app.app_context():
                machines = Machines.query.all()
                posts_map = defaultdict(list)
                message = '📋 <b>Reporte de equipos</b> 📋\n\n'
                current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                for post in Posts.query.filter(or_(Posts.end_date.is_(None), Posts.start_date >= current_date)).all():
                    posts_map[post.machine_id].append(post)

                # Skip if no posts
                if not posts_map:
                    return
                
                for machine in machines:
                    # Get the list of posts for this machine
                    machine_posts = posts_map.get(machine.id, [])
                    total_downtime = 0

                    active_post = next((post for post in machine_posts if post.end_date is None), None)
                    
                    for post in machine_posts:
                        if post.end_date:
                            total_downtime += int((post.end_date - post.start_date).total_seconds() / 60)
                        else:
                            total_downtime += int((datetime.now() - post.start_date).total_seconds() / 60)

                    if only_downtime and total_downtime == 0:
                        continue

                    if not active_post:
                        message += f'<b>{machine.name}</b> corriendo ✅\nHoy ha parado {total_downtime} minutos.\n\n'
                    else: 
                        unique_faults = sorted({post.interruption_type.name.lower() for post in machine_posts if post.end_date is None})
                        faults = ", ".join(unique_faults)
                        message += f'<b>{machine.name}</b> detenido por [{faults}] 🛑\nHoy ha parado {total_downtime} minutos.\n\n'
                
                send_telegram_notification(token, chat_id, message)
    except Timeout:
        # Task is already running elsewhere, exit silently
        return

def run_background_tasks(scheduler):
    scheduler.add_job(
        id='telegram_update_report',
        func=background_task_telegram_short_status_report,
        args=[scheduler, True],
        trigger='cron',
        hour='*',
        minute=0,
        second=0,
        replace_existing=True # Prevents duplicate errors on reload
    )