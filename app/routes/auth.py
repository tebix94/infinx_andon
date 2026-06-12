# Backend modules
from flask import Blueprint, url_for, redirect, flash, render_template, request
from flask_login import login_user, logout_user, login_required, current_user

# SQL data and models
from app.models import Users
from app.extensions import db

# Data schema validation
from pydantic import ValidationError
from app.schemas import UserCreateSchema, UserLoginSchema 

bp = Blueprint('auth', __name__)


@bp.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Use Pydantic to validate data from backend side
            data = UserLoginSchema(**request.form.to_dict())
        except ValidationError as e:
            print(e.json())
            flash('Valores incorrectos, favor de ingresar un número de empleado válido.', 'warning')
            return redirect(url_for('auth.login'))

        user = Users.query.filter_by(employee_number=data.employee_number).first()

        if not user.is_staff:
            flash('Usuario no tiene nivel de acceso.', 'danger')
            return redirect(url_for('auth.login'))
        '''
        if user and user.check_password(data.password):
            login_user(user)
            return redirect(url_for('base.home'))
        '''
        
        # At this point everything is ok
        return redirect(url_for('settings.view'))
    return render_template('register/login.html')


'''
@bp.route('/logout/')
@login_required
def logout():
    logout_user()   
    return redirect(url_for('base.home'))
'''

@bp.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # Use Pydantic to validate data from backend side
            data = UserCreateSchema(**request.form.to_dict())

        except ValidationError as e:
            msg = e.errors()[0]['msg']
            flash(f"Validation Error: {msg}")
            return redirect(url_for('auth.signup'))

        # Check if user exists
        existing_user = Users.query.filter_by(employee_number=data.employee_number).first()
        if existing_user:
            flash('¡El número de empleado ingresado ya existe!')
            return redirect(url_for('auth.signup'))
        
        # Check if the allowing user exists and if is staff
        staff_user = Users.query.filter_by(employee_number=data.employee_number_admin).first()

        if not staff_user:
            flash('¡El número de empleado ingresado como administrador no existe!', 'danger')
            return redirect(url_for('auth.signup'))

        if not staff_user.is_staff:
            flash('¡No tienes permisos para dar de alta nuevos usuarios!', 'danger')
            return redirect(url_for('auth.signup'))
        
        if data.role_name == 'administrator':
            is_operator = False
            is_technician = False
            is_staff = True
        elif data.role_name == 'technician':
            is_operator = False
            is_technician = True
            is_staff = False
        else:
            is_operator = True
            is_technician = False
            is_staff = False

        # Create the new user instance
        new_user = Users(employee_number=data.employee_number,
                        first_name=data.first_name,
                        last_name=data.last_name,
                        is_staff=is_staff,
                        is_technician=is_technician,
                        is_operator=is_operator,
                        )
        
        # Password encryption
        #new_user.set_password(data.password)

        db.session.add(new_user)
        db.session.commit()

        flash('¡Registro exitoso! Ya puede ingresar con sus credenciales.')
        return redirect(url_for('post.requests'))

    return render_template('register/signup.html')