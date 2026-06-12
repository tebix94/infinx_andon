from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Machines, InterruptionTypes, ErrorCauses

bp = Blueprint('settings', __name__)

@bp.route('/view/')
@login_required
def view():
    
    return render_template('/settings/view.html', 
                           machines=Machines.query.all(),
                           interruption_types=InterruptionTypes.query.all(),
                           error_causes=ErrorCauses.query.all())