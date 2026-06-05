import os
import fcntl
from app.models import Machines, Posts
from app.telegram_bot import send_telegram_notification 
from datetime import datetime
from collections import defaultdict
from sqlalchemy import or_

def run_background_tasks(scheduler):
    def background_task_telegram_status_report():
        #Use a file lock to ensure only one instance runs
        lock_file = '/tmp/infinx_telegram.lock'
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
        
        try:
            # Try to lock. If another process has it, this fails immediately.
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, BlockingIOError):
            # Task is already running elsewhere, exit silently
            os.close(fd)
            return
        
        try:
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

                    if not active_post:
                        message += f'<b>{machine.name}</b> corriendo ✅\nHoy ha parado {total_downtime} minutos.\n\n'
                    else: 
                        unique_faults = sorted({post.interruption_type.name.lower() for post in machine_posts if post.end_date is None})
                        faults = ", ".join(unique_faults)
                        message += f'<b>{machine.name}</b> detenido por [{faults}] 🛑\nHoy ha parado {total_downtime} minutos.\n\n'
                
                send_telegram_notification(token, chat_id, message)
        finally:
            # Always release the lock
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    scheduler.add_job(
        id='telegram_update_report',
        func=background_task_telegram_status_report,
        trigger='cron',
        hour='*',
        minute=0,
        second=0,
        replace_existing=True # Prevents duplicate errors on reload
    )