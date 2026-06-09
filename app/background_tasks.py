import os
import tempfile
from filelock import FileLock, Timeout
from app.models import Machines, Posts
from app.telegram_bot import send_telegram_notification 
from datetime import datetime
from collections import defaultdict
from sqlalchemy import or_, and_
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def background_task_telegram_status_report(scheduler, only_downtime=False):
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
                        message += f'<b>{machine.name}</b> corriendo ✅\nHoy ha parado {total_downtime} Minutes.\n\n'
                    else: 
                        unique_faults = sorted({post.interruption_type.name.lower() for post in machine_posts if post.end_date is None})
                        faults = ", ".join(unique_faults)
                        message += f'<b>{machine.name}</b> detenido por [{faults}] 🛑\nHoy ha parado {total_downtime} Minutes.\n\n'
                
                send_telegram_notification(token, chat_id, message)
    except Timeout:
        # Task is already running elsewhere, exit silently
        return

def run_background_tasks(scheduler):
    scheduler.add_job(
        id='telegram_update_report',
        func=background_task_telegram_status_report,
        args=[scheduler, True],
        trigger='cron',
        hour='*',
        minute=0,
        second=0,
        replace_existing=True # Prevents duplicate errors on reload
    )

def background_task_telegram_graph_report(scheduler):
    # Cross-platform lock (works in Linux/WSL and Windows)
    lock = FileLock("infinx_telegram_graph.lock")

    try:
        with lock.acquire(timeout=0):
            with scheduler.app.app_context():
                # Fetch environment variables
                token = os.environ.get('TELEGRAM_BOT_TOKEN')
                chat_id = os.environ.get('TELEGRAM_INFINX_GROUP_ID')
                machines = Machines.query.all()
                machine_downtime = {machine.name: 0 for machine in machines}
                machine_events = {machine.name: 0 for machine in machines}
                machine_fault_status = {machine.name: False for machine in machines}
                current_datetime = datetime.now()
                shift_string = ''

                if current_datetime.hour < 6:
                    start_date = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=5, minute=59, second=59, microsecond=0)
                    shift_string = 'tercer turno'
                elif current_datetime.hour <= 15 and current_datetime.minute < 30:
                    start_date = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=15, minute=29, second=59, microsecond=0)
                    shift_string = 'primer turno'
                elif current_datetime.hour <= 23:
                    start_date = current_datetime.replace(hour=15, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=23, minute=59, second=59, microsecond=0)
                    shift_string = 'segundo turno'

                # Fetch objects from database
                posts = Posts.query.filter(or_(Posts.end_date.is_(None), and_(start_date <= Posts.start_date, Posts.start_date <= end_date)))

                for post in posts:
                    # Calculate downtime delta
                    if post.end_date == None:
                        downtime = int((current_datetime - post.start_date).total_seconds() / 60)
                    else:
                        downtime = int((post.end_date - post.start_date).total_seconds() / 60)

                    machine_downtime[post.machine.name] = machine_downtime.get(post.machine.name, 0) + downtime
                    machine_events[post.machine.name] += 1
                    machine_fault_status[post.machine.name] = True

                report_data = []
                for m_name in machine_downtime.keys():
                    report_data.append({
                        'Machines': m_name,
                        'Minutes': machine_downtime[m_name],
                        'Events': machine_events[m_name],
                        'Status': "● Detenida" if machine_fault_status[m_name] else "● Operando"
                    })

                # Build Pandas dataframe
                df = pd.DataFrame(report_data)
                fig = plt.figure(figsize=(25, 18))
                gs = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.6)

                # Define axes as sepparate
                ax = fig.add_subplot(gs[0])
                ax_table = fig.add_subplot(gs[1])

                # Build bar plot
                bar_labels = df['Machines']
                bar_data = df['Minutes']

                bar_graph = ax.bar(bar_labels, bar_data, color="#0d30ae", edgecolor='white', linewidth=1.2)
                ax.set_title(f'Tiempos de paro por equipo - {shift_string}', style='italic', fontweight='bold', fontsize=25)
                ax.set_ylabel('Minutos', fontsize=25)
                ax.tick_params(axis='x', rotation=45, labelsize=12)
                ax.grid(axis='x', linestyle='--', alpha=0.7)
                ax.grid(axis='y', linestyle='--', alpha=0.7)

                for rect in bar_graph:
                    height = rect.get_height()
                    if height != 0:
                        ax.text(
                            rect.get_x() + rect.get_width() / 2, # Posición X (centro de la barra)
                            height,                              # Posición Y (altura de la barra)
                            f'{int(height)}',                    # Texto (valor)
                            ha='center',                         # Alineación horizontal
                            va='bottom',                         # Alineación vertical
                            fontsize=14,                         # Tamaño de letra
                            fontweight='bold',
                            color='black'
                        )

                # Build table
                df_filtered = df[df['Minutes'] != 0]

                if not df_filtered.empty:
                    table_data = [[row['Minutes'], row['Events'], row['Status']] for _, row in df_filtered.iterrows()]

                    table = ax_table.table(cellText=table_data,
                            rowLabels=df_filtered['Machines'].tolist(),
                            colLabels=['Minutes', 'Incidencias', 'Status'],
                            loc='center', cellLoc='center',
                            )
                    ax_table.axis('off')

                    # Customize the table style
                    table.auto_set_font_size(False)
                    table.set_fontsize(15)
                    table.scale(1, 2.5)

                    # Style the headers
                    for (row, col), cell in table.get_celld().items():
                        if row == 0:  # Header row
                            cell.set_text_props(weight='bold', color='white', fontsize=16)
                            cell.set_facecolor('#40466e')
                        else:  # Data rows
                            cell.set_facecolor('#f8f9fa')
                            cell.set_text_props(weight='bold', color='black', fontsize=14)
                        if row > 0 and col == 2:
                            val = cell.get_text().get_text()
                            if 'Detenida' in val: cell.get_text().set_color('#ff4d4d')
                            elif 'Operando' in val: cell.get_text().set_color('#2ecc71')
                            
                        # Optional: Add borders to all cells
                        cell.set_edgecolor('#dcdcdc')
                else: # When table is empty
                    ax_table.text(0.5, 0.5, 'No hay paros activos en este turno', 
                                ha='center', va='center', fontsize=20, fontweight='bold')
                    ax_table.axis('off')

                # Set file path to OS temp diretory
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', prefix='andon_report_', delete=False)
                temp_path = temp_file.name
                temp_file.close()

                plt.subplots_adjust(left=0.3, bottom=0.28, right=0.8, top=0.72)
                plt.savefig(temp_path, dpi=150, bbox_inches='tight') # DPI 150 da mejor resolución
                plt.close()
                print(f'plot has been created at {temp_path}')

                send_telegram_notification(token, chat_id, 'Gráficas de tiempos de paro', temp_path)
    except Timeout:
        return
    
def run_background_tasks(scheduler):
    scheduler.add_job(
        id='telegram_update_graph_report',
        func=background_task_telegram_graph_report,
        args=[scheduler,],
        trigger='cron',
        hour='*',
        minute=0,
        second=0,
        replace_existing=True # Prevents duplicate errors on reload
    )