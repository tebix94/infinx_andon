# Backend modules
from flask import Blueprint, url_for, redirect, flash, render_template, request
from flask_login import login_user, logout_user, login_required, current_user

# SQL data and models
from app.models import Users
from app.extensions import db

# Data schema validation
from pydantic import ValidationError
from app.schemas import UserLoginSchema, UserCreateSchema

bp = Blueprint('auth', __name__)

@bp.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Use Pydantic to validate data from backend side
            data = UserLoginSchema(**request.form.to_dict())
        except ValidationError as e:
            print(e.json()) # <--- THIS WILL TELL YOU EXACTLY WHICH FIELD FAILED IN YOUR TERMINAL
            flash('Valores incorrectos, favor de usar número de empleado y contraseña.')
            return redirect(url_for('auth.login'))

        user = Users.query.filter_by(employee_id=data.employee_id).first()

        if user and user.check_password(data.password):
            login_user(user)
            return redirect(url_for('base.home'))
        
        flash('Número de empleado o contraseña incorrectos.')
    return render_template('register/login.html')

@bp.route('/logout/')
@login_required
def logout():
    logout_user()   
    return redirect(url_for('base.home'))

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
        existing_user = Users.query.filter_by(employee_id=data.employee_id).first()
        if existing_user:
            flash('¡El número de empleado ingresado ya existe!')
            return redirect(url_for('auth.signup'))

        # Create the new user instance
        new_user = Users(employee_id=data.employee_id,
                        first_name=data.first_name,
                        last_name=data.last_name,
                        )
        
        # Password encryption
        new_user.set_password(data.password)

        db.session.add(new_user)
        db.session.commit()

        flash('¡Registro exitoso! Ya puede ingresar con sus credenciales.')
        return redirect(url_for('auth.login'))

    return render_template('register/signup.html')