from flask import Blueprint, request, render_template, flash, redirect, url_for
from sqlalchemy import or_
from app.schemas import CreatePostSchema
from app.models import Posts
from app.extensions import db
from app.models import Users, Posts, Machines, Devices, Substations, InterruptionTypes, ErrorCauses
from flask_login import current_user, login_required
from datetime import datetime, timedelta

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
    ).paginate(page=page, per_page=10)

    # Fetch data to be render as template context
    interruption_types = InterruptionTypes.query.all()    
    substations = Substations.query.all()
    devices = Devices.query.all()
    error_causes = ErrorCauses.query.all()

    return render_template('post/show_my_requests.html',
                           posts=posts_pagination,
                           pagination=posts_pagination,
                           interruption_types=interruption_types,
                           substations=substations,
                           devices=devices,
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
            post.description = request.form.get('resolution_comment')
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
    
@bp.route('/history')
def history():
    # 1. Obtener parámetros de paginación y filtros de la URL (Query Strings)
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    machine_id_raw = request.args.get('machine_id', '')
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

    if start_date_raw:
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d')
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