# app.py  frontend code

from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

API_BASE = "https://ayodhyatravels.online"

@app.context_processor
def inject_api():
    return {'API_BASE': API_BASE}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html', API_BASE=API_BASE)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', API_BASE=API_BASE)

@app.route('/leads')
def leads():
    return render_template('leads.html', API_BASE=API_BASE)

@app.route('/leads/new')
def lead_new():
    return render_template('lead_form.html', API_BASE=API_BASE)

@app.route('/leads/<int:lid>')
def lead_detail(lid):
    return render_template('lead_detail.html', API_BASE=API_BASE, lead_id=lid)

@app.route('/followups')
def followups():
    return render_template('followups.html', API_BASE=API_BASE)

@app.route('/bookings')
def bookings():
    return render_template('bookings.html', API_BASE=API_BASE)

@app.route('/staff')
def staff():
    return render_template('staff.html', API_BASE=API_BASE)

@app.route('/reports')
def reports():
    return render_template('reports.html', API_BASE=API_BASE)

@app.route('/activity')
def activity():
    return render_template('activity.html', API_BASE=API_BASE)


@app.route('/tour-categories')
def tour_categories():
    return render_template('tour_categories.html', API_BASE=API_BASE)

if __name__ == '__main__':
    app.run(port=5055, debug=False)