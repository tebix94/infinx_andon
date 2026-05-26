from flask import Blueprint, render_template
from app.models import Posts
from app import db
from sqlalchemy import func
from datetime import datetime

bp = Blueprint('base', __name__)

@bp.app_context_processor
def inject_active_posts():
    # Suponiendo que usas SQLAlchemy para contar los registros activos
    count = Posts.query.filter(Posts.end_date == None).count()
    return dict(active_posts_count=count)

@bp.route('/')
def home():
    status_map = {
        0: {"class": "bg-success text-white", "text": "Corriendo"},
        1: {"class": "bg-danger text-white", "text": "Mantenimiento"},
        2: {"class": "bg-danger text-white", "text": "Cambio de modelo"},
        3: {"class": "bg-orange text-white", "text": "Falta de material"},
        4: {"class": "bg-warning text-dark", "text": "Validación"},
        5: {"class": "bg-warning text-dark", "text": "Validación"},
    }
    
    # Check for active posts
    posts = Posts.query.filter(Posts.end_date == None).all()

    # Machine interruption map
    machines_interruption_map = [status_map[0].copy() for _ in range(16)]

    for post in posts:
        if post.machine_id and 0 <= post.machine_id < len(machines_interruption_map):
            status_data = status_map.get(post.interruption_id, status_map[0])
            machines_interruption_map[post.machine_id] = status_data

    return render_template('home.html', map=machines_interruption_map)

@bp.route('/metrics')
def metrics():
    # 1. Obtener todos los posts (activos e históricos)
    all_posts = Posts.query.all()
    now = datetime.now()

    # Inicializar contenedores para los cálculos
    total_minutes = 0
    total_incidents = len(all_posts)
    
    # Estructuras para acumular minutos por máquina (0-15) y por tipo de interrupción (1-5)
    minutes_per_machine = {i: 0.0 for i in range(16)}
    minutes_per_type = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    # Mapa de nombres de máquinas para las etiquetas de la gráfica de barras
    machine_names_map = {
        1: "WAM Plug 1", 2: "WAM Plug 2", 3: "PAM",
        4: "WAM Receptacle 1", 5: "WAM Receptacle 2", 6: "RAM",
        14: "Opti Vix", 15: "Shibuya",
        7: "Ball Attach 3", 8: "Ball Attach 4", 9: "Ball Attach 5",
        10: "Ball Attach 6", 11: "Ball Attach 7", 12: "Ball Attach 8", 13: "Ball Attach 10"
    }

    # Mapa de nombres de tipos de paro para la gráfica de dona
    type_names_map = {
        1: "Mantenimiento",
        2: "Cambio de Modelo",
        3: "Falta de Material",
        4: "Validación (Tipo 4)",
        5: "Validación (Tipo 5)"
    }

    for post in all_posts:
        # Si el paro sigue activo, calculamos el tiempo transcurrido hasta el momento exacto de la consulta
        end = post.end_date if post.end_date else now
        duration_minutes = (end - post.start_date).total_seconds() / 60.0
        
        total_minutes += duration_minutes

        # Acumular minutos por máquina si el ID es válido
        if post.machine_id in minutes_per_machine:
            minutes_per_machine[post.machine_id] += duration_minutes

        # Acumular minutos por tipo de falla si el ID es válido
        if post.interruption_id in minutes_per_type:
            minutes_per_type[post.interruption_id] += duration_minutes

    # 2. Calcular el MTTR (Mean Time To Repair) promedio en minutos
    mttr = (total_minutes / total_incidents) if total_incidents > 0 else 0

    # 3. Preparar datos para la Gráfica de Barras (Solo máquinas del layout con tiempo > 0)
    bar_labels = []
    bar_data = []
    for m_id, name in machine_names_map.items():
        bar_labels.append(name)
        bar_data.append(round(minutes_per_machine[m_id], 1))

    # Encontrar la máquina "Top Ofensora" (la que sume más minutos)
    top_machine_id = max(minutes_per_machine, key=minutes_per_machine.get)
    top_machine_name = machine_names_map.get(top_machine_id, "N/A") if minutes_per_machine[top_machine_id] > 0 else "Ninguna"

    # 4. Preparar datos para la Gráfica de Dona (Tipos de Interrupción)
    pie_labels = list(type_names_map.values())
    pie_data = [round(minutes_per_type[t_id], 1) for t_id in type_names_map.keys()]

    return render_template(
        'metrics.html',
        total_minutes=round(total_minutes, 1),
        mttr=round(mttr, 1),
        total_incidents=total_incidents,
        top_machine=top_machine_name,
        bar_labels=bar_labels,
        bar_data=bar_data,
        pie_labels=pie_labels,
        pie_data=pie_data
    )