from sqlalchemy import UniqueConstraint, ForeignKey, Boolean, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db#, login_manager

class Users(UserMixin, db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    #password: Mapped[str] = mapped_column(String(256), nullable=False)
    first_name: Mapped[str] = mapped_column(String(16), nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    is_technician: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    is_operator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    # Relationships
    posts_from_user_requester: Mapped[list['Posts']] = relationship(back_populates='user_requester',
                                                                    foreign_keys='Posts.user_requester_id')
    posts_from_user_assigned: Mapped[list['Posts']] = relationship(back_populates='user_assigned',
                                                                   foreign_keys='Posts.user_assigned_id')

    def __repr__(self):
        return f'<User {self.first_name} {self.last_name}>'
    
    '''
    # Helper method to set the password
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # Helper method to check the password
    def check_password(self, password):
        return check_password_hash(self.password, password)
    '''
'''  
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))
'''

class Machines(db.Model):
    __tablename__ = 'machines'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True,nullable=False)

    # Relationships
    posts: Mapped[list['Posts']] = relationship(back_populates='machine')
    substations: Mapped[list['Substations']] = relationship(back_populates='machine')

class Substations(db.Model):
    __tablename__ = 'substations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64),nullable=False)
    machine_id: Mapped[int] = mapped_column(Integer, ForeignKey('machines.id'), nullable=False)

    # Relationships
    machine: Mapped['Machines'] = relationship(back_populates='substations')
    devices: Mapped[list['Devices']] = relationship(back_populates='substation', cascade='all, delete-orphan')
    posts: Mapped[list['Posts']] = relationship(back_populates='substation')

    __table_args__ = (
        UniqueConstraint('name', 'machine_id', name='uq_substation_per_machine'),
    )

class Devices(db.Model):
    __tablename__ = 'devices'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    substation_id: Mapped[int] = mapped_column(Integer, ForeignKey('substations.id'), nullable=False)

    # Relationships
    substation: Mapped['Substations'] = relationship(back_populates='devices')
    posts: Mapped[list['Posts']] = relationship(back_populates='device')

    __table_args__ = (
        UniqueConstraint('name', 'substation_id', name='uq_device_per_substation'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "substationId": self.substation_id  # Nota: usamos camelCase para JS
        }

class InterruptionTypes(db.Model):
    __tablename__ = 'interruption_types'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(16))

    # Relationships
    posts: Mapped[list['Posts']] = relationship(back_populates='interruption_type')

class ErrorCauses(db.Model):
    __tablename__ = 'error_causes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    posts: Mapped[list['Posts']] = relationship(back_populates='error_cause')

class Posts(db.Model):
    __tablename__ = 'posts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_requester_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    user_assigned_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    machine_id: Mapped[int] = mapped_column(Integer, ForeignKey('machines.id'), nullable=False)
    interruption_id: Mapped[int] = mapped_column(Integer, ForeignKey('interruption_types.id'), nullable=True)
    substation_id: Mapped[int] = mapped_column(Integer, ForeignKey('substations.id'), nullable=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey('devices.id'), nullable=True)
    error_cause_id: Mapped[int] = mapped_column(Integer, ForeignKey('error_causes.id'), nullable=True)

    start_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    resolution_comment: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relationships
    user_requester: Mapped['Users'] = relationship(back_populates='posts_from_user_requester',
                                                   foreign_keys=[user_requester_id])
    user_assigned: Mapped['Users'] = relationship(back_populates='posts_from_user_assigned',
                                                  foreign_keys=[user_assigned_id])
    interruption_type: Mapped['InterruptionTypes'] = relationship(back_populates='posts')
    machine: Mapped['Machines'] = relationship(back_populates='posts')
    substation: Mapped['Substations'] = relationship(back_populates='posts')
    device: Mapped['Devices'] = relationship(back_populates='posts')
    error_cause: Mapped['ErrorCauses'] = relationship(back_populates='posts')