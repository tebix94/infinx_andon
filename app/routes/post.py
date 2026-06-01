from flask import Blueprint, request, render_template, flash, redirect, url_for, make_response
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app.schemas import CreatePostSchema
from app.extensions import db
from app.models import Users, Posts, Machines, Devices, Substations, InterruptionTypes, ErrorCauses
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import pandas as pd
import io

bp = Blueprint('post', __name__)

@bp.route('/requests/')
def requests():
    # Get the current page number from the URL query string (e.g., /mis-solicitudes/?page=2)
    # Default to page 1, and ensure it's an integer
    page = request.args.get('page', 1, type=int)

    posts_pagination = Posts.query.filter_by(end_date=None).options(
        db.joinedload(Posts.machine),
        db.joinedload(Posts.user_requester),
        db.joinedload(Posts.interruption_type)
    ).paginate(page=page, per_page=4)

    # Fetch data to be render as template context
    interruption_types = InterruptionTypes.query.all()    
    substations = Substations.query.all()
    devices = Devices.query.all()
    devices_list = [d.to_dict() for d in devices]
    error_causes = ErrorCauses.query.all()

    return render_template('post/show_my_requests.html',
                           posts=posts_pagination,
                           pagination=posts_pagination,
                           interruption_types=interruption_types,
                           substations=substations,
                           devices=devices_list,
                           error_causes=error_causes,
                           )

@bp.route('/create/', methods=['GET','POST'])
def create():
    if request.method == 'POST':
        try:
            # Use Pydantic to validate data from backend side
            data = CreatePostSchema(**request.form.to_dict())
        except Exception as e:
            print(e.json())
            flash('Valores incorrectos, favor de verificar la informacion ingresada')
            return redirect(url_for('post.create'))

        user = Users.query.filter_by(employee_number=data.employee_number).first()
        
        if not user or not (user.is_staff or user.is_operator):
            print(e.json())
            flash('Número de empleado inválido o no registrado', 'danger')
            return redirect(url_for('post.create'))

        try:
            new_post = Posts(
                user_requester_id=user.id,
                machine_id=data.machine_id,
                interruption_id=data.interruption_id,
                description=data.description
            )

            new_post.start_date = datetime.now()
            
            db.session.add(new_post)
            db.session.commit()
            
            flash('¡Tu solicitud se ha creado con éxito!', 'success')
            return redirect(url_for('post.requests'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar en la base de datos: {str(e)}")
            flash('Ocurrió un error al procesar tu solicitud en el sistema.', 'danger')
            return redirect(url_for('post.create'))
    
    # Get users to pass a list to the static file script to validate that the user is_staff or is_operator to allow form submit
    users = Users.query.filter(or_(Users.is_staff == True, Users.is_operator == True)).all()

    # Get machines and interruption types to render these values at the form dropwdown lists
    machines = Machines.query.all()
    interruption_types = InterruptionTypes.query.all()

    return render_template('post/create.html', users=users, machines=machines, interruption_types=interruption_types)
    
@bp.route('/reassign/<int:post_id>', methods=['POST',])
def reassign(post_id):
    if request.method == 'POST':
        post = Posts.query.get_or_404(post_id)

        post.interruption_id = request.form.get('interruption_id')

        db.session.commit()

        return redirect(url_for('post.requests'))
    
@bp.route('/delete/<int:post_id>', methods=['POST',])
def delete(post_id):
    post = Posts.query.get_or_404(post_id)

    try:
        db.session.delete(post)
        db.session.commit()

        flash('La orden ha sido eliminada exitosamente', 'success')

    except Exception:
        db.session.rollback()
        flash('Hubo un error al intentar eliminar la orden', 'danger')

    return redirect(url_for('post.requests'))
    
@bp.route('/close/<int:post_id>', methods=['POST',])
def close(post_id):
    if request.method == 'POST':
        try:

            post = Posts.query.get_or_404(post_id)
            employee_number = request.form.get('employee_number')
            post.substation_id = request.form.get('substation_id')
            post.device_id = request.form.get('device_id')
            post.error_cause_id = request.form.get('error_cause_id')
            post.resolution_comment = request.form.get('resolution_comment')
            post.end_date = datetime.now()

            assigned_user = Users.query.filter_by(employee_number=employee_number).first()

            if not (assigned_user.is_staff or assigned_user.is_technician):
                db.session.rollback()
                flash('¡Tu usuario no tiene permisos para cerrar órdenes!', 'danger')
                return redirect(url_for('post.requests'))

            post.user_assigned_id = assigned_user.id

            db.session.commit()
            flash('La orden se ha cerrado exitosamente', 'success')
        except Exception:
            db.session.rollback()
            flash('Ocurrió un error al intentar finalizar cerrar la orden')
        
        return redirect(url_for('post.requests'))
    
@bp.route('/history/')
def history():
    # 1. Obtener parámetros de paginación y filtros de la URL (Query Strings)
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    machine_id_raw = request.args.get('machine_id', '') if request.args.get('id', '') == '' else request.args.get('id', '')
    interruption_type_id_raw = request.args.get('interruption_type_id', '')
    user_requester_id_raw = request.args.get('user_requester_id', '')
    user_assigned_id_raw = request.args.get('user_assigned_id', '')
    start_date_raw = request.args.get('start_date', '')
    end_date_raw = request.args.get('end_date', '')

    # Inicializamos las variables en None para evitar UnboundLocalError si los ifs no se cumplen
    user_requester_id = None
    user_assigned_id = None

    # 2. Query base con joinedload para evitar el problema de consultas N+1 en la tabla
    query = Posts.query.options(
        db.joinedload(Posts.machine),
        db.joinedload(Posts.user_requester),
        db.joinedload(Posts.user_assigned),
        db.joinedload(Posts.interruption_type)
    )

    # Bloques de filtrado (Filter statements)
    if status_filter == 'open':
        query = query.filter(Posts.end_date == None)
    elif status_filter == 'closed':
        query = query.filter(Posts.end_date != None)

    if machine_id_raw and machine_id_raw.strip() != '':
        try:
            machine_id = int(machine_id_raw)
            query = query.filter(Posts.machine_id == machine_id)
        except ValueError:
            pass  

    if user_requester_id_raw and user_requester_id_raw.strip() != '':
        try:
            user_requester_id = int(user_requester_id_raw)
            query = query.filter(Posts.user_requester_id == user_requester_id)
        except ValueError:
            pass

    if user_assigned_id_raw and user_assigned_id_raw.strip() != '':
        try:
            user_assigned_id = int(user_assigned_id_raw)
            query = query.filter(Posts.user_assigned_id == user_assigned_id)
        except ValueError:
            pass

    if interruption_type_id_raw and interruption_type_id_raw.strip() != '':
        try:
            itype_id = int(interruption_type_id_raw)
            query = query.filter(Posts.interruption_id == itype_id)
        except ValueError:
            pass

    if start_date_raw and request.args.get('id', '') == '':
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d')
        query = query.filter(Posts.start_date >= start_date)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print(start_date)
        query = query.filter(Posts.start_date >= start_date)
        
    if end_date_raw:
        # Sumamos 1 día para incluir los eventos ocurridos dentro del último día seleccionado
        end_date = datetime.strptime(end_date_raw, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(Posts.start_date < end_date)

    # 7. Ejecutar paginación ordenando por el más reciente primero
    pagination = query.order_by(Posts.start_date.desc()).paginate(page=page, per_page=15)

    # 8. Cargar catálogos requeridos exclusivamente para renderizar los <select> del template
    machines = Machines.query.order_by(Machines.name).all()
    interruption_types = InterruptionTypes.query.order_by(InterruptionTypes.name).all()
    
    # NUEVO: Traer la lista de usuarios de la base de datos para los selects del HTML
    # (Ajusta "Users" por el nombre exacto de tu modelo de usuarios si es necesario)
    users = Users.query.order_by(Users.first_name).all() 

    return render_template(
        'post/history.html', 
        posts=pagination, 
        machines=machines, 
        interruption_types=interruption_types,
        users=users,                          # Enviamos la lista completa de objetos usuario
        user_requester_id=user_requester_id,  # Enviamos el ID filtrado (o None)
        user_assigned_id=user_assigned_id     # Enviamos el ID filtrado (o None)
    )

@bp.route('/export')
def export():
    # 1. Capturar filtros y forzar a None si vienen vacíos "" en la URL
    status = request.args.get('status', '').strip() or None
    
    machine_id = request.args.get('machine_id', type=int)
    interruption_type_id = request.args.get('interruption_type_id', type=int)
    user_requester_id = request.args.get('user_requester_id', type=int)
    user_assigned_id = request.args.get('user_assigned_id', type=int)
    
    start_date_str = request.args.get('start_date', '').strip() or None
    end_date_str = request.args.get('end_date', '').strip() or None

    # 2. Construir el Query aplicando Eager Loading para optimizar los JOINs
    # Esto reduce las cientos de consultas a una SOLA consulta masiva y eficiente
    query = Posts.query.options(
        joinedload(Posts.machine),
        joinedload(Posts.interruption_type),
        joinedload(Posts.user_requester),
        joinedload(Posts.user_assigned)
    )

    if status == 'open':
        query = query.filter(Posts.end_date == None)
    elif status == 'closed':
        query = query.filter(Posts.end_date != None)

    if machine_id is not None:
        query = query.filter(Posts.machine_id == machine_id)

    if interruption_type_id is not None:
        query = query.filter(Posts.interruption_type_id == interruption_type_id)

    if user_requester_id is not None:
        query = query.filter(Posts.user_requester_id == user_requester_id)

    if user_assigned_id is not None:
        query = query.filter(Posts.user_assigned_id == user_assigned_id)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Posts.start_date >= start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Posts.start_date <= end_date)
        except ValueError:
            pass

    # Traer todos los registros filtrados ordenados por fecha
    posts = query.order_by(Posts.start_date.desc()).all()

    # 3. Estructurar los datos para el reporte de Excel (Ahora el bucle es instantáneo)
    data = []
    for post in posts:
        duration = ""
        if post.end_date and post.start_date:
            duration = int((post.end_date - post.start_date).total_seconds() / 60)

        data.append({
            "Folio": f"REQ#{post.id}",
            "Máquina": post.machine.name if post.machine else "N/A",
            "Tipo de Interrupción": post.interruption_type.name if post.interruption_type else "N/A",
            "Solicitado Por": f"{post.user_requester.first_name} {post.user_requester.last_name}" if post.user_requester else "N/A",
            "Cerrado Por": f"{post.user_assigned.first_name} {post.user_assigned.last_name}" if post.end_date and post.user_assigned else "-- En Proceso --",
            "Fecha Apertura": post.start_date.strftime('%Y-%m-%d %H:%M') if post.start_date else "",
            "Fecha Cierre": post.end_date.strftime('%Y-%m-%d %H:%M') if post.end_date else "-- En Proceso --",
            "Tiempo Muerto (Minutos)": duration,
            "Estatus": "Cerrado" if post.end_date else "Abierto",
            "Comentarios Iniciales": post.description or "",
            "Reporte de Solución": post.resolution_comment or ""
        })

    # 4. Generación del archivo Excel
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Historial_OT')
    
    output.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Reporte_Infinx_{timestamp}.xlsx"
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return response