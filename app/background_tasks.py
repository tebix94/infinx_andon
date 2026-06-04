from app.extensions import db
from app.models import Machines, Posts
from app.telegram_bot import send_telegram_notification

def background_task_telegram_status_report(app, token, chat_id):
    # Use the passed app instance to open the context
    with app.app_context():
        machines = Machines.query.all()
        active_posts = {post.machine_id: post for post in Posts.query.filter_by(end_date=None).all()}
        
        message = '📋 <b>Reporte de equipos</b> 📋\n'
        for machine in machines:
            active_post = active_posts.get(machine.id)
            if not active_post:
                message += f'<b>{machine.name}</b>: Corriendo 🟢\n'
            else: 
                fault_type = active_post.interruption_type.name.lower()
                message += f'<b>{machine.name}</b>: Detenido por {fault_type} 🔴\n'
        
        send_telegram_notification(token, chat_id, message)