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
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
ENABLE_TELEGRAM = os.environ.get('ENABLE_TELEGRAM')

def background_task_telegram_report(scheduler, enable):
    if not enable:
        print('Telegram messenger service has been disabled from .env file.')
        return

    # Cross-platform lock (works in Linux/WSL and Windows)
    lock = FileLock("infinx_telegram_graph.lock")

    try:
        with lock.acquire(timeout=0):
            with scheduler.app.app_context():
                # Fetch environment variables
                token = os.environ.get('TELEGRAM_BOT_TOKEN')
                chat_id = os.environ.get('TELEGRAM_INFINX_GROUP_ID')
                machines = Machines.query.all()
                machine_downtime = defaultdict(dict)
                machine_events = {machine.name: 0 for machine in machines}
                machine_fault_status = {machine.name: False for machine in machines}
                at_least_one_machine_failed_onshift = False
                current_datetime = datetime.now()
                FIRST_SHIFT_START_TIME = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
                SECOND_SHIFT_START_TIME = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
                shift_string = ''

                if current_datetime < FIRST_SHIFT_START_TIME:
                    start_date = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=5, minute=59, second=59, microsecond=0)
                    shift_string = 'tercer turno'
                elif current_datetime < SECOND_SHIFT_START_TIME:
                    start_date = current_datetime.replace(hour=6, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=15, minute=29, second=59, microsecond=0)
                    shift_string = 'primer turno'
                else:
                    start_date = current_datetime.replace(hour=15, minute=0, second=0, microsecond=0)
                    end_date = current_datetime.replace(hour=23, minute=59, second=59, microsecond=0)
                    shift_string = 'segundo turno'

                message = f'📋 <b>Reporte de equipos ({shift_string})</b> 📋\n\n'

                # Fetch objects from database
                posts = Posts.query.filter(or_(Posts.end_date.is_(None), and_(start_date <= Posts.start_date, Posts.start_date <= end_date)))

                for post in posts:
                    # Calculate downtime delta
                    if post.end_date == None:
                        downtime = int((current_datetime - post.start_date).total_seconds() / 60)
                    else:
                        downtime = int((post.end_date - post.start_date).total_seconds() / 60)

                    if post.interruption_id not in machine_downtime[post.machine.name]:
                        machine_downtime[post.machine.name][post.interruption_id] = 0
                    machine_downtime[post.machine.name][post.interruption_id] += downtime
                    if post.machine.name not in machine_events:
                        machine_events[post.machine.name] = 0
                    machine_events[post.machine.name] += 1  

                    # If at least a post was openned, mark the following flag
                    at_least_one_machine_failed_onshift = True

                    # If at least one post is not closed, set the machine status as faulted
                    if not post.end_date:
                        machine_fault_status[post.machine.name] = True

                    if not machine_fault_status[post.machine.name]:
                        message += f'<b>{post.machine.name}</b> corriendo ✅\nEn {shift_string} ha parado {machine_downtime[post.machine_id].get(1, 0)} minutos por reparación.'
                        message += f'\nEn {shift_string} ha parado {machine_downtime[post.machine_id].get(2, 0)} minutos por cambio de modelo.\n\n'
                    else:
                        unique_faults = sorted({post.interruption_type.name.lower() for post in post.machine.posts if post.end_date is None})
                        faults = ", ".join(unique_faults)
                        message += f'<b>{post.machine.name}</b> detenido por [{faults}] 🛑\nEn {shift_string} ha parado {machine_downtime[post.machine_id].get(1, 0)} minutos por reparación.'
                        message += f'\nEn {shift_string} ha parado {machine_downtime[post.machine_id].get(2, 0)} minutos por cambio de modelo.\n\n'
                if at_least_one_machine_failed_onshift:
                    report_data = []
                    for machine in machines:
                        m_name = machine.name
                        
                        report_data.append({
                            'Machines': m_name,
                            'Minutes1': machine_downtime[m_name].get(1, 0),
                            'Minutes2': machine_downtime[m_name].get(2, 0),
                            'Events': machine_events.get(m_name, 0),
                            'Status': "● Detenido" if machine_fault_status.get(m_name, False) else "● Corriendo"
                        })

                    # Build Pandas dataframe
                    df = pd.DataFrame(report_data)
                    labels = df['Machines']
                    fig = plt.figure(figsize=(25, 18))
                    gs = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.6)

                    # Define axes as sepparate
                    ax = fig.add_subplot(gs[0])
                    ax_table = fig.add_subplot(gs[1])

                    # Build bar plot
                    bar1_data = df['Minutes1'].tolist()
                    bar2_data = df['Minutes2'].tolist()
                    labels = df['Machines'].tolist()
                    bar1 = ax.bar(labels, bar1_data, color="#0d30ae", label='Reparación', edgecolor='white')
                    bar2 = ax.bar(labels, bar2_data, bottom=bar1_data, color="#ef7b00", label='Cambio de modelo', edgecolor='white')
                    ax.set_title(f'Tiempos de paro por equipo - {shift_string}', style='italic', fontweight='bold', fontsize=25)
                    ax.set_ylabel('Minutos', fontsize=25)
                    ax.tick_params(axis='x', rotation=45, labelsize=12)
                    ax.grid(axis='x', linestyle='--', alpha=0.7)
                    ax.grid(axis='y', linestyle='--', alpha=0.7)

                    ax.legend(handles=[bar1, bar2], loc='upper right', fontsize=12)

                    for i in range(len(df)):
                        m1 = df.loc[i, 'Minutes1']
                        m2 = df.loc[i, 'Minutes2']
                        if m1 > 0:
                            ax.text(i, m1/2, str(int(m1)), ha='center', va='center', color='white', fontweight='bold')
                        if m2 > 0:
                            ax.text(i, m1 + m2/2, str(int(m2)), ha='center', va='center', color='white', fontweight='bold')

                    # Build table
                    df_filtered = df[(df['Minutes1'] > 0) | (df['Minutes2'] > 0)].copy()

                    if not df_filtered.empty:
                        table_data = [[row['Minutes1'], row['Minutes2'], row['Events'], row['Status']] for _, row in df_filtered.iterrows()]

                        table = ax_table.table(
                            cellText=table_data,
                            rowLabels=df_filtered['Machines'].tolist(),
                            colLabels=['Reparación', 'Cambio de modelo', 'Incidencias', 'Estado'],
                            loc='center', 
                            cellLoc='center'
                        )
                        ax_table.axis('off')

                        # Customize the table style
                        table.auto_set_font_size(False)
                        table.set_fontsize(15)
                        table.scale(1, 2.5)

                        # Style the headers
                        for (row, col), cell in table.get_celld().items():
                            if row == 0:
                                cell.set_text_props(weight='bold', color='white', fontsize=16)
                                if col == 0: cell.set_facecolor('#0d30ae')
                                elif col == 1: cell.set_facecolor('#ef7b00')
                                else: cell.set_facecolor('#40466e')
                            else:
                                cell.set_facecolor('#f8f9fa')
                                cell.set_text_props(weight='bold', color='black', fontsize=14)
                                
                            
                            if row > 0 and col == 3: # Columna 3 es 'Status'
                                val = cell.get_text().get_text()
                                if 'Detenido' in val: cell.get_text().set_color('#ff4d4d')
                                elif 'Corriendo' in val: cell.get_text().set_color('#2ecc71')
                            
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

                    send_telegram_notification(token=token,
                                               chat_id=chat_id,
                                               message=f'📋 <b>Reporte de equipos ({shift_string})</b> 📋\n\n',
                                               image_path=temp_path)
                else:
                    send_telegram_notification(token=token, chat_id=chat_id, message=f'Sin fallas que reportar en {shift_string}.')

    except Timeout:
        return

def run_background_tasks(scheduler):
    scheduler.add_job(
        id='telegram_update_report',
        func=background_task_telegram_report,
        args=[scheduler, ENABLE_TELEGRAM == 'YES'],
        trigger='cron',
        hour='*',
        minute=0,
        second=0,
        replace_existing=True # Prevents duplicate errors on reload
    )