import os
from app.extensions import db
from app.models import Machines, Posts
from app.telegram_bot import send_telegram_notification 
from datetime import datetime

def background_task_telegram_status_report(app, token, chat_id):
    lock_file = "report_lock.txt"
    
    # 1. Get current hour as a string
    current_hour_str = datetime.now().strftime("%Y-%m-%d-%H")
    
    # 2. Check if file exists and compare the modification time
    if os.path.exists(lock_file):
        # Get the time the file was last modified
        mtime = os.path.getmtime(lock_file)
        last_modified_hour = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d-%H")
        
        # If it was modified in the current hour, skip
        if last_modified_hour == current_hour_str:
            return

    # 3. Overwrite the file with the current hour
    with open(lock_file, "w") as f:
        f.write(current_hour_str)

    # Use the passed app instance to open the context
    with app.app_context():
        machines = Machines.query.all()
        active_posts = {post.machine_id: post for post in Posts.query.filter_by(end_date=None).all()}
        
        message = '📋 <b>Reporte de equipos</b> 📋\n'
        for machine in machines:
            active_post = active_posts.get(machine.id)
            if not active_post:
                message += f'<b>{machine.name}</b>: Corriendo ✅\n'
            else: 
                fault_type = active_post.interruption_type.name.lower()
                message += f'<b>{machine.name}</b>: Detenido por {fault_type} 🛑\n'
        
        send_telegram_notification(token, chat_id, message)