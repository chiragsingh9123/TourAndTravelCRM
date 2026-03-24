#app.py Backend server
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
from mysql.connector import Error
import bcrypt
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'travel-crm-secret-key-2026'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)

CORS(app, origins="*", supports_credentials=True)
jwt = JWTManager(app)

# ─── DB CONFIG ───────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',          # Change to your MySQL password
    'database': 'travel_crm',
    'charset': 'utf8mb4'
}

def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

def db_query(sql, params=None, fetch=True):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f"Query Error: {e}")
        if conn:
            conn.close()
        return None

def db_execute(sql, params=None):
    return db_query(sql, params, fetch=False)

# ─── AUTH ─────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    user = db_query("SELECT * FROM users WHERE username=%s AND is_active=1", (username,))
    print(user)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user = user[0]
    if bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        token = create_access_token(identity=json.dumps({
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'full_name': user['full_name']
        }))
        db_execute("INSERT INTO activity_logs (user_id, action, details) VALUES (%s,'LOGIN',%s)",
                   (user['id'], f"User {user['username']} logged in"))
        return jsonify({
            'token': token,
            'user': {'id': user['id'], 'username': user['username'],
                     'role': user['role'], 'full_name': user['full_name']}
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    identity = json.loads(get_jwt_identity())
    return jsonify(identity)

# ─── USERS ───────────────────────────────────────────────────
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    users = db_query("SELECT id, username, full_name, email, phone, role, is_active, created_at FROM users ORDER BY full_name")
    return jsonify(users or [])

@app.route('/api/users', methods=['POST'])
@jwt_required()
def create_user():
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    pw_hash = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode()
    uid = db_execute(
        "INSERT INTO users (username, password_hash, full_name, email, phone, role) VALUES (%s,%s,%s,%s,%s,%s)",
        (data['username'], pw_hash, data['full_name'], data.get('email',''), data.get('phone',''), data.get('role','staff'))
    )
    db_execute("INSERT INTO activity_logs (user_id, action, details) VALUES (%s,'CREATE_USER',%s)",
               (identity['id'], f"Created user {data['username']}"))
    return jsonify({'id': uid, 'message': 'User created'}), 201

@app.route('/api/users/<int:uid>', methods=['PUT'])
@jwt_required()
def update_user(uid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    fields = []
    params = []
    for f in ['full_name','email','phone','role','is_active']:
        if f in data:
            fields.append(f"{f}=%s")
            params.append(data[f])
    if 'password' in data and data['password']:
        fields.append("password_hash=%s")
        params.append(bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()).decode())
    params.append(uid)
    db_execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", params)
    return jsonify({'message': 'Updated'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@jwt_required()
def delete_user(uid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    db_execute("UPDATE users SET is_active=0 WHERE id=%s", (uid,))
    return jsonify({'message': 'Deactivated'})

# ─── LEADS ───────────────────────────────────────────────────
def next_lead_id():
    year = datetime.now().year
    row = db_query("SELECT COUNT(*) as cnt FROM leads WHERE YEAR(created_at)=%s", (year,))
    n = (row[0]['cnt'] if row else 0) + 1
    return f"LEAD-{year}-{n:05d}"

@app.route('/api/leads', methods=['GET'])
@jwt_required()
def get_leads():
    identity = json.loads(get_jwt_identity())
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    assigned = request.args.get('assigned_to', '')
    offset = (page - 1) * per_page

    where = []
    params = []

    if identity['role'] == 'staff':
        where.append("l.assigned_to=%s")
        params.append(identity['id'])
    elif assigned:
        where.append("l.assigned_to=%s")
        params.append(assigned)

    if status:
        where.append("l.status=%s")
        params.append(status)

    if search:
        where.append("(l.customer_name LIKE %s OR l.mobile LIKE %s OR l.alt_mobile LIKE %s OR l.tour_name LIKE %s OR l.lead_id LIKE %s)")
        s = f"%{search}%"
        params.extend([s, s, s, s, s])

    where_str = "WHERE " + " AND ".join(where) if where else ""
    
    total = db_query(f"SELECT COUNT(*) as cnt FROM leads l {where_str}", params)
    total = total[0]['cnt'] if total else 0

    leads = db_query(
        f"""SELECT l.*, u.full_name as assigned_name 
            FROM leads l LEFT JOIN users u ON l.assigned_to=u.id 
            {where_str} ORDER BY l.created_at DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset]
    )
    return jsonify({'leads': leads or [], 'total': total, 'page': page, 'per_page': per_page})

@app.route('/api/leads', methods=['POST'])
@jwt_required()
def create_lead():
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    lead_id = next_lead_id()
    
    lid = db_execute("""
        INSERT INTO leads (lead_id, customer_name, mobile, alt_mobile, email, city,
            tour_name, travel_date, pickup_location, drop_location,
            adults, children, hotel_category, meal_plan,
            vehicle_type, lead_source, assigned_to, status, enquiry_date, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        lead_id, data.get('customer_name'), data.get('mobile'), data.get('alt_mobile',''),
        data.get('email',''), data.get('city',''), data.get('tour_name'),
        data.get('travel_date'), data.get('pickup_location',''), data.get('drop_location',''),
        data.get('adults',1), data.get('children',0),
        data.get('hotel_category','Budget'), data.get('meal_plan','MAP'),
        data.get('vehicle_type','Sedan'), data.get('lead_source','Call'),
        data.get('assigned_to', identity['id']),
        data.get('status','New Lead'), data.get('enquiry_date', datetime.now().date()),
        data.get('notes','')
    ))
    db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'CREATE_LEAD','lead',%s,%s)",
               (identity['id'], lid, f"Created lead {lead_id}"))
    return jsonify({'id': lid, 'lead_id': lead_id, 'message': 'Lead created'}), 201

@app.route('/api/leads/<int:lid>', methods=['GET'])
@jwt_required()
def get_lead(lid):
    identity = json.loads(get_jwt_identity())
    lead = db_query("""
        SELECT l.*, u.full_name as assigned_name 
        FROM leads l LEFT JOIN users u ON l.assigned_to=u.id 
        WHERE l.id=%s""", (lid,))
    if not lead:
        return jsonify({'error': 'Not found'}), 404
    lead = lead[0]
    
    if identity['role'] == 'staff' and lead['assigned_to'] != identity['id']:
        return jsonify({'error': 'Forbidden'}), 403

    convs = db_query("""
        SELECT c.*, u.full_name as staff_name FROM conversations c 
        LEFT JOIN users u ON c.user_id=u.id WHERE c.lead_id=%s ORDER BY c.created_at DESC""", (lid,))
    
    followups = db_query("""
        SELECT f.*, u.full_name as staff_name FROM followups f 
        LEFT JOIN users u ON f.user_id=u.id WHERE f.lead_id=%s ORDER BY f.followup_date ASC""", (lid,))
    
    packages = db_query("SELECT * FROM packages WHERE lead_id=%s ORDER BY created_at DESC", (lid,))
    booking = db_query("SELECT * FROM bookings WHERE lead_id=%s", (lid,))
    
    # Check same mobile history
    history = db_query("""
        SELECT id, lead_id, customer_name, tour_name, status, created_at 
        FROM leads WHERE mobile=%s AND id!=%s ORDER BY created_at DESC LIMIT 5""",
        (lead['mobile'], lid))

    lead['conversations'] = convs or []
    lead['followups'] = followups or []
    lead['packages'] = packages or []
    lead['booking'] = booking[0] if booking else None
    lead['history'] = history or []
    return jsonify(lead)

@app.route('/api/leads/<int:lid>', methods=['PUT'])
@jwt_required()
def update_lead(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    allowed = ['customer_name','mobile','alt_mobile','email','city','tour_name','travel_date',
               'pickup_location','drop_location','adults','children','hotel_category','meal_plan',
               'vehicle_type','lead_source','assigned_to','status','notes']
    fields = []
    params = []
    for f in allowed:
        if f in data:
            fields.append(f"{f}=%s")
            params.append(data[f])
    params.append(lid)
    db_execute(f"UPDATE leads SET {', '.join(fields)} WHERE id=%s", params)
    db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'UPDATE_LEAD','lead',%s,%s)",
               (identity['id'], lid, f"Updated lead {lid}"))
    return jsonify({'message': 'Updated'})

@app.route('/api/leads/<int:lid>/assign', methods=['POST'])
@jwt_required()
def assign_lead(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin','manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    db_execute("UPDATE leads SET assigned_to=%s WHERE id=%s", (data['assigned_to'], lid))
    db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ASSIGN_LEAD','lead',%s,%s)",
               (identity['id'], lid, f"Assigned lead {lid} to user {data['assigned_to']}"))
    return jsonify({'message': 'Assigned'})

# ─── CONVERSATIONS ────────────────────────────────────────────
@app.route('/api/leads/<int:lid>/conversations', methods=['POST'])
@jwt_required()
def add_conversation(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    cid = db_execute("""
        INSERT INTO conversations (lead_id, user_id, summary, call_result, call_type, next_followup_date)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (lid, identity['id'], data.get('summary',''), data.get('call_result',''),
          data.get('call_type','Outgoing'), data.get('next_followup_date')))
    
    if data.get('next_followup_date'):
        db_execute("""
            INSERT INTO followups (lead_id, user_id, followup_date, notes, status)
            VALUES (%s,%s,%s,%s,'Pending')
        """, (lid, identity['id'], data['next_followup_date'], data.get('summary','')))

    if data.get('status_update'):
        db_execute("UPDATE leads SET status=%s WHERE id=%s", (data['status_update'], lid))

    db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ADD_CONVERSATION','lead',%s,%s)",
               (identity['id'], lid, f"Added conversation to lead {lid}"))
    return jsonify({'id': cid, 'message': 'Conversation added'}), 201

# ─── FOLLOWUPS ────────────────────────────────────────────────
@app.route('/api/followups', methods=['GET'])
@jwt_required()
def get_followups():
    identity = json.loads(get_jwt_identity())
    filter_type = request.args.get('filter', 'today')
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    where = []
    params = []

    if identity['role'] == 'staff':
        where.append("f.user_id=%s")
        params.append(identity['id'])

    if filter_type == 'today':
        where.append("DATE(f.followup_date)=%s")
        params.append(today)
    elif filter_type == 'tomorrow':
        where.append("DATE(f.followup_date)=%s")
        params.append(tomorrow)
    elif filter_type == 'overdue':
        where.append("DATE(f.followup_date)<%s AND f.status='Pending'")
        params.append(today)

    where.append("f.status='Pending'")
    where_str = "WHERE " + " AND ".join(where)
    
    followups = db_query(f"""
        SELECT f.*, l.customer_name, l.mobile, l.tour_name, l.lead_id, l.id as LeadId, u.full_name as staff_name
        FROM followups f 
        LEFT JOIN leads l ON f.lead_id=l.id
        LEFT JOIN users u ON f.user_id=u.id
        {where_str} ORDER BY f.followup_date ASC
    """, params)
    return jsonify(followups or [])

@app.route('/api/followups/<int:fid>/complete', methods=['POST'])
@jwt_required()
def complete_followup(fid):
    db_execute("UPDATE followups SET status='Completed', completed_at=NOW() WHERE id=%s", (fid,))
    return jsonify({'message': 'Completed'})

# ─── PACKAGES ────────────────────────────────────────────────
@app.route('/api/leads/<int:lid>/packages', methods=['POST'])
@jwt_required()
def create_package(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    pid = db_execute("""
        INSERT INTO packages (lead_id, user_id, tour_name, itinerary, hotels, transport, 
            other_charges, base_price, discount, final_price, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (lid, identity['id'], data.get('tour_name',''),
          json.dumps(data.get('itinerary',[])), json.dumps(data.get('hotels',[])),
          json.dumps(data.get('transport',{})), json.dumps(data.get('other_charges',[])),
          data.get('base_price',0), data.get('discount',0), data.get('final_price',0),
          data.get('notes','')))
    return jsonify({'id': pid, 'message': 'Package created'}), 201

@app.route('/api/packages/<int:pid>', methods=['GET'])
@jwt_required()
def get_package(pid):
    pkg = db_query("SELECT * FROM packages WHERE id=%s", (pid,))
    if not pkg:
        return jsonify({'error': 'Not found'}), 404
    p = pkg[0]
    for f in ['itinerary','hotels','transport','other_charges']:
        if p[f]:
            try:
                p[f] = json.loads(p[f])
            except:
                pass
    return jsonify(p)

@app.route('/api/packages/<int:pid>', methods=['PUT'])
@jwt_required()
def update_package(pid):
    data = request.get_json()
    db_execute("""
        UPDATE packages SET tour_name=%s, itinerary=%s, hotels=%s, transport=%s,
            other_charges=%s, base_price=%s, discount=%s, final_price=%s, notes=%s
        WHERE id=%s
    """, (data.get('tour_name',''), json.dumps(data.get('itinerary',[])),
          json.dumps(data.get('hotels',[])), json.dumps(data.get('transport',{})),
          json.dumps(data.get('other_charges',[])),
          data.get('base_price',0), data.get('discount',0), data.get('final_price',0),
          data.get('notes',''), pid))
    return jsonify({'message': 'Updated'})

# ─── BOOKINGS ─────────────────────────────────────────────────
def next_booking_id():
    year = datetime.now().year
    row = db_query("SELECT COUNT(*) as cnt FROM bookings WHERE YEAR(created_at)=%s", (year,))
    n = (row[0]['cnt'] if row else 0) + 1
    return f"BOOKING-{year}-{n:05d}"

@app.route('/api/leads/<int:lid>/book', methods=['POST'])
@jwt_required()
def create_booking(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    booking_id = next_booking_id()
    bid = db_execute("""
        INSERT INTO bookings (booking_id, lead_id, user_id, total_amount, discount, 
            final_amount, advance_paid, balance, payment_method, payment_date, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (booking_id, lid, identity['id'],
          data.get('total_amount',0), data.get('discount',0), data.get('final_amount',0),
          data.get('advance_paid',0), data.get('balance',0),
          data.get('payment_method','Cash'), data.get('payment_date', datetime.now().date()),
          data.get('notes','')))
    db_execute("UPDATE leads SET status='Booked' WHERE id=%s", (lid,))
    
    if data.get('advance_paid',0) > 0:
        db_execute("""
            INSERT INTO payments (booking_id, amount, payment_method, payment_date, notes)
            VALUES (%s,%s,%s,%s,'Advance payment')
        """, (bid, data['advance_paid'], data.get('payment_method','Cash'),
              data.get('payment_date', datetime.now().date())))
    
    db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'CREATE_BOOKING','booking',%s,%s)",
               (identity['id'], bid, f"Created booking {booking_id}"))
    return jsonify({'id': bid, 'booking_id': booking_id, 'message': 'Booking created'}), 201

@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    identity = json.loads(get_jwt_identity())
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    
    where = ""
    params = []
    if identity['role'] == 'staff':
        where = "WHERE b.user_id=%s"
        params.append(identity['id'])
    
    total = db_query(f"SELECT COUNT(*) as cnt FROM bookings b {where}", params)
    total = total[0]['cnt'] if total else 0
    
    bookings = db_query(f"""
        SELECT b.*, l.customer_name, l.mobile, l.tour_name, l.travel_date, u.full_name as staff_name
        FROM bookings b 
        LEFT JOIN leads l ON b.lead_id=l.id 
        LEFT JOIN users u ON b.user_id=u.id
        {where} ORDER BY b.created_at DESC LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    return jsonify({'bookings': bookings or [], 'total': total})

@app.route('/api/bookings/<int:bid>/payment', methods=['POST'])
@jwt_required()
def add_payment(bid):
    data = request.get_json()
    pid = db_execute("""
        INSERT INTO payments (booking_id, amount, payment_method, payment_date, notes)
        VALUES (%s,%s,%s,%s,%s)
    """, (bid, data['amount'], data.get('payment_method','Cash'),
          data.get('payment_date', datetime.now().date()), data.get('notes','')))
    
    # Update balance
    booking = db_query("SELECT * FROM bookings WHERE id=%s", (bid,))[0]
    paid = db_query("SELECT SUM(amount) as total FROM payments WHERE booking_id=%s", (bid,))
    total_paid = paid[0]['total'] or 0
    balance = booking['final_amount'] - total_paid
    db_execute("UPDATE bookings SET advance_paid=%s, balance=%s WHERE id=%s",
               (total_paid, balance, bid))
    return jsonify({'id': pid, 'message': 'Payment added'})

# ─── DASHBOARD / REPORTS ──────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    identity = json.loads(get_jwt_identity())
    today = datetime.now().date()
    
    if identity['role'] == 'staff':
        uid = identity['id']
        stats = {
            'my_leads': (db_query("SELECT COUNT(*) as cnt FROM leads WHERE assigned_to=%s", (uid,)) or [{'cnt':0}])[0]['cnt'],
            'new_leads': (db_query("SELECT COUNT(*) as cnt FROM leads WHERE assigned_to=%s AND status='New Lead'", (uid,)) or [{'cnt':0}])[0]['cnt'],
            'followups_today': (db_query("SELECT COUNT(*) as cnt FROM followups WHERE user_id=%s AND DATE(followup_date)=%s AND status='Pending'", (uid, today)) or [{'cnt':0}])[0]['cnt'],
            'overdue': (db_query("SELECT COUNT(*) as cnt FROM followups WHERE user_id=%s AND DATE(followup_date)<%s AND status='Pending'", (uid, today)) or [{'cnt':0}])[0]['cnt'],
            'bookings': (db_query("SELECT COUNT(*) as cnt FROM bookings WHERE user_id=%s", (uid,)) or [{'cnt':0}])[0]['cnt'],
            'revenue': (db_query("SELECT SUM(final_amount) as total FROM bookings WHERE user_id=%s", (uid,)) or [{'total':0}])[0]['total'] or 0,
        }
    else:
        stats = {
            'total_leads': (db_query("SELECT COUNT(*) as cnt FROM leads") or [{'cnt':0}])[0]['cnt'],
            'new_leads_today': (db_query("SELECT COUNT(*) as cnt FROM leads WHERE DATE(created_at)=%s", (today,)) or [{'cnt':0}])[0]['cnt'],
            'followups_today': (db_query("SELECT COUNT(*) as cnt FROM followups WHERE DATE(followup_date)=%s AND status='Pending'", (today,)) or [{'cnt':0}])[0]['cnt'],
            'overdue': (db_query("SELECT COUNT(*) as cnt FROM followups WHERE DATE(followup_date)<%s AND status='Pending'", (today,)) or [{'cnt':0}])[0]['cnt'],
            'bookings_today': (db_query("SELECT COUNT(*) as cnt FROM bookings WHERE DATE(created_at)=%s", (today,)) or [{'cnt':0}])[0]['cnt'],
            'total_bookings': (db_query("SELECT COUNT(*) as cnt FROM bookings") or [{'cnt':0}])[0]['cnt'],
            'revenue_today': (db_query("SELECT SUM(final_amount) as total FROM bookings WHERE DATE(created_at)=%s", (today,)) or [{'total':0}])[0]['total'] or 0,
            'total_revenue': (db_query("SELECT SUM(final_amount) as total FROM bookings") or [{'total':0}])[0]['total'] or 0,
            'lead_status_counts': db_query("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status") or [],
            'recent_leads': db_query("""
                SELECT l.lead_id, l.id, l.customer_name, l.mobile, l.tour_name, l.status, l.created_at, u.full_name as assigned_name
                FROM leads l LEFT JOIN users u ON l.assigned_to=u.id ORDER BY l.created_at DESC LIMIT 10""") or [],
            'staff_performance': db_query("""
    SELECT 
        u.full_name,
        COALESCE(l.leads,0) as leads,
        COALESCE(c.calls,0) as calls,
        COALESCE(b.bookings,0) as bookings,
        COALESCE(b.revenue,0) as revenue
    FROM users u

    LEFT JOIN (
        SELECT assigned_to, COUNT(*) as leads
        FROM leads
        GROUP BY assigned_to
    ) l ON l.assigned_to = u.id

    LEFT JOIN (
        SELECT user_id, COUNT(*) as calls
        FROM conversations
        GROUP BY user_id
    ) c ON c.user_id = u.id

    LEFT JOIN (
        SELECT user_id,
               COUNT(*) as bookings,
               SUM(final_amount) as revenue
        FROM bookings
        GROUP BY user_id
    ) b ON b.user_id = u.id

    WHERE u.role='staff' 
    AND u.is_active=1

    ORDER BY revenue DESC
""") or [],
        }
        
        # Monthly trend
        stats['monthly_bookings'] = db_query("""
            SELECT DATE_FORMAT(created_at, '%Y-%m') as month, 
                COUNT(*) as bookings, SUM(final_amount) as revenue
            FROM bookings WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY month ORDER BY month
        """) or []

    return jsonify(stats)

@app.route('/api/search', methods=['GET'])
@jwt_required()
def search():
    identity = json.loads(get_jwt_identity())
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    s = f"%{q}%"
    
    where_extra = ""
    params = [s, s, s, s, s]
    if identity['role'] == 'staff':
        where_extra = "AND l.assigned_to=%s"
        params.append(identity['id'])
    
    results = db_query(f"""
        SELECT l.id, l.lead_id, l.customer_name, l.mobile, l.tour_name, l.status, l.created_at
        FROM leads l
        WHERE (l.customer_name LIKE %s OR l.mobile LIKE %s OR l.alt_mobile LIKE %s 
               OR l.tour_name LIKE %s OR l.lead_id LIKE %s)
        {where_extra}
        ORDER BY l.created_at DESC LIMIT 20
    """, params)
    return jsonify(results or [])

@app.route('/api/export/leads', methods=['GET'])
@jwt_required()
def export_leads():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    
    import csv
    import io
    from flask import Response
    
    leads = db_query("""
        SELECT l.lead_id, l.customer_name, l.mobile, l.alt_mobile, l.email, l.city,
            l.tour_name, l.travel_date, l.adults, l.children,
            l.hotel_category, l.meal_plan, l.vehicle_type,
            l.lead_source, l.status, l.enquiry_date, u.full_name as assigned_to,
            l.created_at
        FROM leads l LEFT JOIN users u ON l.assigned_to=u.id
        ORDER BY l.created_at DESC
    """)
    
    output = io.StringIO()
    if leads:
        writer = csv.DictWriter(output, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=leads_export.csv'}
    )

@app.route('/api/export/bookings', methods=['GET'])
@jwt_required()
def export_bookings():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    
    import csv, io
    from flask import Response
    
    bookings = db_query("""
        SELECT b.booking_id, l.customer_name, l.mobile, l.tour_name, l.travel_date,
            b.total_amount, b.discount, b.final_amount, b.advance_paid, b.balance,
            b.payment_method, b.payment_date, u.full_name as staff, b.created_at
        FROM bookings b
        LEFT JOIN leads l ON b.lead_id=l.id
        LEFT JOIN users u ON b.user_id=u.id
        ORDER BY b.created_at DESC
    """)
    output = io.StringIO()
    if bookings:
        writer = csv.DictWriter(output, fieldnames=bookings[0].keys())
        writer.writeheader()
        writer.writerows(bookings)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bookings_export.csv'}
    )

@app.route('/api/staff/performance', methods=['GET'])
@jwt_required()
def staff_performance():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    
    perf = db_query("""
SELECT 
    u.id,
    u.full_name,
    u.username,

    COALESCE(l.total_leads,0) as total_leads,
    COALESCE(l.new_leads,0) as new_leads,
    COALESCE(l.converted,0) as converted,
    COALESCE(l.lost,0) as lost,

    COALESCE(c.total_calls,0) as total_calls,

    COALESCE(b.bookings,0) as bookings,
    COALESCE(b.revenue,0) as revenue

FROM users u

LEFT JOIN (
    SELECT 
        assigned_to,
        COUNT(*) as total_leads,
        COUNT(CASE WHEN status='New Lead' THEN 1 END) as new_leads,
        COUNT(CASE WHEN status='Booked' THEN 1 END) as converted,
        COUNT(CASE WHEN status='Lost' THEN 1 END) as lost
    FROM leads
    GROUP BY assigned_to
) l ON l.assigned_to = u.id

LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as total_calls
    FROM conversations
    GROUP BY user_id
) c ON c.user_id = u.id

LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as bookings,
        SUM(final_amount) as revenue
    FROM bookings
    GROUP BY user_id
) b ON b.user_id = u.id

WHERE u.role='staff'
AND u.is_active=1

ORDER BY revenue DESC
""")
    return jsonify(perf or [])

@app.route('/api/activity', methods=['GET'])
@jwt_required()
def get_activity():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    
    logs = db_query("""
        SELECT a.*, u.full_name FROM activity_logs a 
        LEFT JOIN users u ON a.user_id=u.id
        ORDER BY a.created_at DESC LIMIT 100
    """)
    return jsonify(logs or [])

if __name__ == '__main__':
    app.run(port=5055, debug=True)