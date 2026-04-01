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
        cursor = conn.cursor(dictionary=True, buffered=True)
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
        raise   # 🔥 THIS IS THE FIX


def db_execute(sql, params=None):
    return db_query(sql, params, fetch=False)


def db_query2(sql, params=None, fetch=True):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            last_id = cursor.lastrowid
            if not last_id:
                cursor.execute("SELECT LAST_INSERT_ID() AS id")
                row = cursor.fetchone()
                last_id = row['id'] if row else None
            result = last_id
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f"Query Error: {e}")
        if conn:
            conn.close()
        return None

def db_execute2(sql, params=None):
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

    row = db_query("""
        SELECT lead_id FROM leads
        WHERE lead_id LIKE %s
        ORDER BY id DESC LIMIT 1
    """, (f"LEAD-{year}-%",))

    if row and row[0]['lead_id']:
        last_id = row[0]['lead_id']
        last_num = int(last_id.split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f"LEAD-{year}-{next_num:05d}"

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

    where = ["l.is_deleted=0"]
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
    try:
        identity = json.loads(get_jwt_identity())
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        # ─── REQUIRED FIELDS ─────────────────────────────
        if not data.get('customer_name') or not data.get('mobile'):
            return jsonify({'error': 'customer_name and mobile are required'}), 400

        # ─── GENERATE LEAD ID ────────────────────────────
        lead_id = next_lead_id()

        # ─── DATE HANDLING ───────────────────────────────
        from datetime import datetime

        travel_date = data.get('travel_date')
        if travel_date:
            try:
                travel_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
            except:
                return jsonify({'error': 'Invalid travel_date format (use YYYY-MM-DD)'}), 400

        enquiry_date = data.get('enquiry_date')
        if enquiry_date:
            try:
                enquiry_date = datetime.strptime(enquiry_date, "%Y-%m-%d").date()
            except:
                return jsonify({'error': 'Invalid enquiry_date format (use YYYY-MM-DD)'}), 400
        else:
            enquiry_date = datetime.now().date()

        # ─── ENUM SAFE VALUES ────────────────────────────
        hotel_category = data.get('hotel_category')
        if hotel_category not in ['Budget','Deluxe','Premium']:
            hotel_category = 'Budget'

        meal_plan = data.get('meal_plan')
        if meal_plan not in ['CP','MAP','AP','EP']:
            meal_plan = 'MAP'

        vehicle_type = data.get('vehicle_type')
        if vehicle_type not in ['Sedan','SUV','Innova','Tempo Traveller','Mini Bus','Bus']:
            vehicle_type = 'Sedan'

        lead_source = data.get('lead_source')
        if lead_source not in ['Call','Website','WhatsApp','Referral','Walk-in','Other']:
            lead_source = 'Call'

        status = data.get('status')
        if status not in ['New Lead','Follow-up','Negotiation','Booked','Lost']:
            status = 'New Lead'

        # ─── ASSIGNED USER VALIDATION ────────────────────
        assigned_to = data.get('assigned_to') or identity['id']

        user_check = db_query("SELECT id FROM users WHERE id=%s", (assigned_to,))
        if not user_check:
            return jsonify({'error': f'Invalid assigned_to user id: {assigned_to}'}), 400

        # ─── INSERT ──────────────────────────────────────
        lid = db_execute("""
            INSERT INTO leads (
                lead_id, customer_name, mobile, alt_mobile, email, city,
                tour_name, travel_date, pickup_location, drop_location,
                adults, children, hotel_category, meal_plan,
                vehicle_type, lead_source, assigned_to, status, enquiry_date, notes
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            lead_id,
            data.get('customer_name'),
            data.get('mobile'),
            data.get('alt_mobile'),
            data.get('email'),
            data.get('city'),
            data.get('tour_name'),
            travel_date,
            data.get('pickup_location'),
            data.get('drop_location'),
            data.get('adults', 1),
            data.get('children', 0),
            hotel_category,
            meal_plan,
            vehicle_type,
            lead_source,
            assigned_to,
            status,
            enquiry_date,
            data.get('notes')
        ))

        if not lid:
            return jsonify({'error': 'Insert failed (DB error)'}), 500

        # ─── LOG ACTIVITY ────────────────────────────────
        db_execute("""
            INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s,'CREATE_LEAD','lead',%s,%s)
        """, (identity['id'], lid, f"Created lead {lead_id}"))

        return jsonify({
            'id': lid,
            'lead_id': lead_id,
            'message': 'Lead created successfully'
        }), 201

    except Exception as e:
        print("CREATE LEAD ERROR:", str(e))
        return jsonify({'error': str(e)}), 500


# @app.route('/api/leads', methods=['POST'])
# @jwt_required()
# def create_lead():
#     identity = json.loads(get_jwt_identity())
#     data = request.get_json()
#     lead_id = next_lead_id()
    
#     lid = db_execute("""
#         INSERT INTO leads (lead_id, customer_name, mobile, alt_mobile, email, city,
#             tour_name, travel_date, pickup_location, drop_location,
#             adults, children, hotel_category, meal_plan,
#             vehicle_type, lead_source, assigned_to, status, enquiry_date, notes)
#         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#     """, (
#         lead_id, data.get('customer_name'), data.get('mobile'), data.get('alt_mobile',''),
#         data.get('email',''), data.get('city',''), data.get('tour_name'),
#         data.get('travel_date'), data.get('pickup_location',''), data.get('drop_location',''),
#         data.get('adults',1), data.get('children',0),
#         data.get('hotel_category','Budget'), data.get('meal_plan','MAP'),
#         data.get('vehicle_type','Sedan'), data.get('lead_source','Call'),
#         data.get('assigned_to', identity['id']),
#         data.get('status','New Lead'), data.get('enquiry_date', datetime.now().date()),
#         data.get('notes','')
#     ))
#     db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'CREATE_LEAD','lead',%s,%s)",
#                (identity['id'], lid, f"Created lead {lead_id}"))
#     return jsonify({'id': lid, 'lead_id': lead_id, 'message': 'Lead created'}), 201




# @app.route('/api/leads/<int:lid>', methods=['GET'])
# @jwt_required()
# def get_lead(lid):
#     identity = json.loads(get_jwt_identity())
#     lead = db_query("""
#         SELECT l.*, u.full_name as assigned_name 
#         FROM leads l LEFT JOIN users u ON l.assigned_to=u.id 
#         WHERE l.id=%s""", (lid,))
#     if not lead:
#         return jsonify({'error': 'Not found'}), 404
#     lead = lead[0]
    
#     if identity['role'] == 'staff' and lead['assigned_to'] != identity['id']:
#         return jsonify({'error': 'Forbidden'}), 403

#     convs = db_query("""
#         SELECT c.*, u.full_name as staff_name FROM conversations c 
#         LEFT JOIN users u ON c.user_id=u.id WHERE c.lead_id=%s ORDER BY c.created_at DESC""", (lid,))
    
#     followups = db_query("""
#         SELECT f.*, u.full_name as staff_name FROM followups f 
#         LEFT JOIN users u ON f.user_id=u.id WHERE f.lead_id=%s ORDER BY f.followup_date ASC""", (lid,))
    
#     packages = db_query("SELECT * FROM packages WHERE lead_id=%s ORDER BY created_at DESC", (lid,))
#     booking = db_query("SELECT * FROM bookings WHERE lead_id=%s", (lid,))
    
#     # Check same mobile history
#     history = db_query("""
#         SELECT id, lead_id, customer_name, tour_name, status, created_at 
#         FROM leads WHERE mobile=%s AND id!=%s ORDER BY created_at DESC LIMIT 5""",
#         (lead['mobile'], lid))

#     lead['conversations'] = convs or []
#     lead['followups'] = followups or []
#     lead['packages'] = packages or []
#     lead['booking'] = booking[0] if booking else None
#     lead['history'] = history or []
#     return jsonify(lead)


@app.route('/api/leads/<int:lid>', methods=['GET'])
@jwt_required()
def get_lead(lid):
    identity = json.loads(get_jwt_identity())
    lead = db_query("""
        SELECT l.*, u.full_name as assigned_name 
        FROM leads l LEFT JOIN users u ON l.assigned_to=u.id 
        WHERE l.id=%s AND l.is_deleted=0""", (lid,))
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
    
    # ✅ Parse JSON string columns in each package
    if packages:
        for pkg in packages:
            for f in ['itinerary', 'hotels', 'transport', 'other_charges']:
                if pkg.get(f) and isinstance(pkg[f], str):
                    try:
                        pkg[f] = json.loads(pkg[f])
                    except:
                        pkg[f] = [] if f != 'transport' else {}

    booking = db_query("SELECT * FROM bookings WHERE lead_id=%s", (lid,))
    booking_obj = booking[0] if booking else None

    # ✅ Fetch payments using booking id
    if booking_obj:
        payments = db_query(
            "SELECT * FROM payments WHERE booking_id=%s ORDER BY payment_date DESC",
            (booking_obj['id'],)
        )
    else:
        payments = []

    # ✅ Fetch WhatsApp logs
    whatsapp_logs = db_query("""
        SELECT w.*, u.full_name as staff_name 
        FROM whatsapp_logs w 
        LEFT JOIN users u ON w.user_id=u.id 
        WHERE w.lead_id=%s 
        ORDER BY w.created_at DESC""", (lid,))

    # ✅ Fetch pinned notes
    pinned_notes = db_query(
        "SELECT * FROM lead_notes WHERE lead_id=%s ORDER BY created_at DESC", (lid,))

    # Check same mobile history
    history = db_query("""
        SELECT id, lead_id, customer_name, tour_name, status, created_at 
        FROM leads WHERE mobile=%s AND id!=%s ORDER BY created_at DESC LIMIT 5""",
        (lead['mobile'], lid))

    lead['conversations']  = convs or []
    lead['followups']      = followups or []
    lead['packages']       = packages or []
    lead['booking']        = booking_obj
    lead['payments']       = payments or []
    lead['whatsapp_logs']  = whatsapp_logs or []
    lead['pinned_notes']   = pinned_notes or []
    lead['history']        = history or []
    return jsonify(lead)

# @app.route('/api/leads/<int:lid>', methods=['DELETE'])
# @jwt_required()
# def delete_lead(lid):
#     identity = json.loads(get_jwt_identity())
#     if identity['role'] not in ('admin', 'manager'):
#         return jsonify({'error': 'Forbidden — only admin/manager can delete leads'}), 403
    
#     lead = db_query("SELECT lead_id FROM leads WHERE id=%s", (lid,))
#     if not lead:
#         return jsonify({'error': 'Not found'}), 404
#     lead_id_str = lead[0]['lead_id']
    
#     # Cascade: delete child records first (FK safety for tables without ON DELETE CASCADE)
#     db_execute("DELETE FROM followups WHERE lead_id=%s", (lid,))
#     db_execute("DELETE FROM conversations WHERE lead_id=%s", (lid,))
#     db_execute("DELETE FROM packages WHERE lead_id=%s", (lid,))
#     db_execute("DELETE FROM whatsapp_logs WHERE lead_id=%s", (lid,))
#     db_execute("DELETE FROM lead_notes WHERE lead_id=%s", (lid,))
    
#     # Delete payments tied to this lead's booking
#     booking = db_query("SELECT id FROM bookings WHERE lead_id=%s", (lid,))
#     if booking:
#         db_execute("DELETE FROM payments WHERE booking_id=%s", (booking[0]['id'],))
#     db_execute("DELETE FROM bookings WHERE lead_id=%s", (lid,))
    
#     db_execute("DELETE FROM leads WHERE id=%s", (lid,))
    
#     db_execute(
#         "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'DELETE_LEAD','lead',%s,%s)",
#         (identity['id'], lid, f"Deleted lead {lead_id_str}")
#     )
#     return jsonify({'message': f'Lead {lead_id_str} deleted'})



@app.route('/api/leads/<int:lid>', methods=['DELETE'])
@jwt_required()
def delete_lead(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden — only admin/manager can delete leads'}), 403
    
    lead = db_query("SELECT lead_id FROM leads WHERE id=%s AND is_deleted=0", (lid,))
    if not lead:
        return jsonify({'error': 'Not found'}), 404
    lead_id_str = lead[0]['lead_id']
    
    db_execute(
        "UPDATE leads SET is_deleted=1, deleted_at=NOW(), deleted_by=%s WHERE id=%s",
        (identity['id'], lid)
    )
    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'SOFT_DELETE_LEAD','lead',%s,%s)",
        (identity['id'], lid, f"Soft-deleted lead {lead_id_str}")
    )
    return jsonify({'message': f'Lead {lead_id_str} moved to trash'})

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

# @app.route('/api/leads/<int:lid>/assign', methods=['POST'])
# @jwt_required()
# def assign_lead(lid):
#     identity = json.loads(get_jwt_identity())
#     if identity['role'] not in ('admin','manager'):
#         return jsonify({'error': 'Forbidden'}), 403
#     data = request.get_json()
#     db_execute("UPDATE leads SET assigned_to=%s WHERE id=%s", (data['assigned_to'], lid))
#     db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ASSIGN_LEAD','lead',%s,%s)",
#                (identity['id'], lid, f"Assigned lead {lid} to user {data['assigned_to']}"))
#     return jsonify({'message': 'Assigned'})


@app.route('/api/leads/<int:lid>/assign', methods=['POST'])
@jwt_required()
def assign_lead(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    new_assigned = data.get('assigned_to')
    notes        = data.get('notes', '')

    if not new_assigned:
        return jsonify({'error': 'assigned_to is required'}), 400

    # Get current assignee before updating
    current = db_query("SELECT assigned_to FROM leads WHERE id=%s", (lid,))
    if not current:
        return jsonify({'error': 'Lead not found'}), 404
    old_assigned = current[0]['assigned_to']

    # Update the lead
    db_execute("UPDATE leads SET assigned_to=%s WHERE id=%s", (new_assigned, lid))

    # Log the assignment history
    db_execute("""
        INSERT INTO lead_assignments (lead_id, assigned_from, assigned_to, assigned_by, notes)
        VALUES (%s, %s, %s, %s, %s)
    """, (lid, old_assigned, new_assigned, identity['id'], notes))

    # Log activity
    db_execute("""
        INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
        VALUES (%s,'REASSIGN_LEAD','lead',%s,%s)
    """, (identity['id'], lid, f"Reassigned lead {lid} from user {old_assigned} to {new_assigned}"))

    return jsonify({'message': 'Assigned'})


# New route — fetch assignment history for a lead
@app.route('/api/leads/<int:lid>/assignments', methods=['GET'])
@jwt_required()
def get_lead_assignments(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    logs = db_query("""
        SELECT
            la.*,
            uf.full_name  AS from_name,
            ut.full_name  AS to_name,
            ub.full_name  AS by_name
        FROM lead_assignments la
        LEFT JOIN users uf ON la.assigned_from = uf.id
        LEFT JOIN users ut ON la.assigned_to   = ut.id
        LEFT JOIN users ub ON la.assigned_by   = ub.id
        WHERE la.lead_id = %s
        ORDER BY la.created_at DESC
    """, (lid,))
    return jsonify(logs or [])











# ─── CONVERSATIONS ────────────────────────────────────────────
# @app.route('/api/leads/<int:lid>/conversations', methods=['POST'])
# @jwt_required()
# def add_conversation(lid):
#     identity = json.loads(get_jwt_identity())
#     data = request.get_json()
#     cid = db_execute("""
#         INSERT INTO conversations (lead_id, user_id, summary, call_result, call_type, next_followup_date)
#         VALUES (%s,%s,%s,%s,%s,%s)
#     """, (lid, identity['id'], data.get('summary',''), data.get('call_result',''),
#           data.get('call_type','Outgoing'), data.get('next_followup_date')))
    
#     if data.get('next_followup_date'):
#         db_execute("""
#             INSERT INTO followups (lead_id, user_id, followup_date, notes, status)
#             VALUES (%s,%s,%s,%s,'Pending')
#         """, (lid, identity['id'], data['next_followup_date'], data.get('summary','')))

#     if data.get('status_update'):
#         db_execute("UPDATE leads SET status=%s WHERE id=%s", (data['status_update'], lid))

#     # db_execute("INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ADD_CONVERSATION','lead',%s,%s)",
#     #            (identity['id'], lid, f"Added conversation to lead {lid}"))

#     cid = db_execute("""
#       INSERT INTO conversations (lead_id, user_id, summary, call_result, call_type,
#           next_followup_date, call_duration)
#       VALUES (%s,%s,%s,%s,%s,%s,%s)
#   """, (lid, identity['id'], data.get('summary',''), data.get('call_result',''),
#         data.get('call_type','Outgoing'), data.get('next_followup_date'),
#         data.get('call_duration')))
#     return jsonify({'id': cid, 'message': 'Conversation added'}), 201


@app.route('/api/leads/<int:lid>/conversations', methods=['POST'])
@jwt_required()
def add_conversation(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()

    cid = db_execute("""
        INSERT INTO conversations
            (lead_id, user_id, summary, call_result, call_type, next_followup_date)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        lid,
        identity['id'],
        data.get('summary', ''),
        data.get('call_result', ''),
        data.get('call_type', 'Outgoing'),
        data.get('next_followup_date')
    ))

    if data.get('next_followup_date'):
        db_execute("""
            INSERT INTO followups (lead_id, user_id, followup_date, notes, status)
            VALUES (%s,%s,%s,%s,'Pending')
        """, (lid, identity['id'], data['next_followup_date'], data.get('summary', '')))

    if data.get('status_update'):
        db_execute("UPDATE leads SET status=%s WHERE id=%s", (data['status_update'], lid))

    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ADD_CONVERSATION','lead',%s,%s)",
        (identity['id'], lid, f"Added conversation to lead {lid}")
    )
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
    elif filter_type == 'upcoming':
        where.append("DATE(f.followup_date)>%s")
        params.append(tomorrow)

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
    try:
        identity = json.loads(get_jwt_identity())
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        # Validate lead exists
        lead = db_query2("SELECT id FROM leads WHERE id=%s AND is_deleted=0", (lid,))
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        # Check no duplicate booking
        existing = db_query2("SELECT id, booking_id FROM bookings WHERE lead_id=%s", (lid,))
        if existing:
            return jsonify({
                'error': f"Booking already exists for this lead: {existing[0]['booking_id']}"
            }), 409

        booking_id = next_booking_id()

        total_amount  = float(data.get('total_amount',  0) or 0)
        discount      = float(data.get('discount',      0) or 0)
        final_amount  = float(data.get('final_amount',  0) or 0)
        advance_paid  = float(data.get('advance_paid',  0) or 0)
        balance       = float(data.get('balance',       0) or 0)
        payment_method = data.get('payment_method', 'Cash')
        notes          = data.get('notes', '')

        payment_date = data.get('payment_date')
        if payment_date:
            try:
                payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
            except:
                payment_date = datetime.now().date()
        else:
            payment_date = datetime.now().date()

        print(f"[BOOKING] Inserting booking {booking_id} for lead {lid}")

        bid = db_execute2("""
            INSERT INTO bookings (booking_id, lead_id, user_id, total_amount, discount,
                final_amount, advance_paid, balance, payment_method, payment_date, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            booking_id, lid, identity['id'],
            total_amount, discount, final_amount,
            advance_paid, balance,
            payment_method, payment_date, notes
        ))

        print(f"[BOOKING] db_execute returned bid={bid}")

        if not bid:
            return jsonify({'error': 'Database insert failed — bid is None'}), 500

        # Update lead status
        db_execute2("UPDATE leads SET status='Booked' WHERE id=%s", (lid,))

        # Record advance payment if any
        if advance_paid > 0:
            pid = db_execute2("""
                INSERT INTO payments (booking_id, amount, payment_method, payment_date, notes)
                VALUES (%s,%s,%s,%s,%s)
            """, (bid, advance_paid, payment_method, payment_date, 'Advance payment'))
            print(f"[BOOKING] Payment inserted pid={pid}")

        # Activity log
        db_execute2("""
            INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
            VALUES (%s,'CREATE_BOOKING','booking',%s,%s)
        """, (identity['id'], bid, f"Created booking {booking_id} for lead {lid}"))

        print(f"[BOOKING] Done — booking_id={booking_id}, bid={bid}")

        return jsonify({
            'id':         bid,
            'booking_id': booking_id,
            'message':    'Booking created successfully'
        }), 201

    except Exception as e:
        import traceback
        print(f"[BOOKING ERROR] {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500



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

# @app.route('/api/bookings/<int:bid>/payment', methods=['POST'])
# @jwt_required()
# def add_payment(bid):
#     data = request.get_json()
#     pid = db_execute("""
#         INSERT INTO payments (booking_id, amount, payment_method, payment_date, notes)
#         VALUES (%s,%s,%s,%s,%s)
#     """, (bid, data['amount'], data.get('payment_method','Cash'),
#           data.get('payment_date', datetime.now().date()), data.get('notes','')))
    
#     # Update balance
#     booking = db_query("SELECT * FROM bookings WHERE id=%s", (bid,))[0]
#     paid = db_query("SELECT SUM(amount) as total FROM payments WHERE booking_id=%s", (bid,))
#     total_paid = paid[0]['total'] or 0
#     balance = booking['final_amount'] - total_paid
#     db_execute("UPDATE bookings SET advance_paid=%s, balance=%s WHERE id=%s",
#                (total_paid, balance, bid))
#     return jsonify({'id': pid, 'message': 'Payment added'})

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









# ══════════════════════════════════════════════════════════════
# NEW ROUTES — paste these into app.py before the final
#   if __name__ == '__main__': block
# ══════════════════════════════════════════════════════════════

# ─── EXTENDED LEAD DETAIL (includes payments, whatsapp, notes) ────────────
# Replace / augment the existing GET /api/leads/<lid> route so it also
# returns payments, whatsapp_logs and pinned_notes.
# FIND the line that reads:
#   lead['history'] = history or []
#   return jsonify(lead)
# ADD these lines just before return jsonify(lead):

#   payments = db_query("SELECT * FROM payments WHERE booking_id=(SELECT id FROM bookings WHERE lead_id=%s LIMIT 1) ORDER BY payment_date DESC", (lid,))
#   whatsapp_logs = db_query("SELECT w.*, u.full_name as staff_name FROM whatsapp_logs w LEFT JOIN users u ON w.user_id=u.id WHERE w.lead_id=%s ORDER BY w.created_at DESC", (lid,))
#   pinned_notes = db_query("SELECT * FROM lead_notes WHERE lead_id=%s ORDER BY created_at DESC", (lid,))
#   lead['payments'] = payments or []
#   lead['whatsapp_logs'] = whatsapp_logs or []
#   lead['pinned_notes'] = pinned_notes or []

# ─── WHATSAPP LOGS ────────────────────────────────────────────
@app.route('/api/leads/<int:lid>/whatsapp', methods=['POST'])
@jwt_required()
def log_whatsapp(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    if not data.get('message','').strip():
        return jsonify({'error': 'Message required'}), 400
    wid = db_execute(
        "INSERT INTO whatsapp_logs (lead_id, user_id, message) VALUES (%s,%s,%s)",
        (lid, identity['id'], data['message'].strip())
    )
    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'WHATSAPP_LOG','lead',%s,%s)",
        (identity['id'], lid, f"WhatsApp logged for lead {lid}")
    )
    return jsonify({'id': wid, 'message': 'Logged'}), 201


# ─── PINNED NOTES ────────────────────────────────────────────
@app.route('/api/leads/<int:lid>/notes', methods=['POST'])
@jwt_required()
def add_note(lid):
    identity = json.loads(get_jwt_identity())
    data = request.get_json()
    if not data.get('note','').strip():
        return jsonify({'error': 'Note text required'}), 400
    nid = db_execute(
        "INSERT INTO lead_notes (lead_id, user_id, note, color) VALUES (%s,%s,%s,%s)",
        (lid, identity['id'], data['note'].strip(), data.get('color', 'yellow'))
    )
    return jsonify({'id': nid, 'message': 'Note added'}), 201


@app.route('/api/notes/<int:nid>', methods=['DELETE'])
@jwt_required()
def delete_note(nid):
    identity = json.loads(get_jwt_identity())
    # Staff can only delete their own notes; admin/manager can delete any
    note = db_query("SELECT * FROM lead_notes WHERE id=%s", (nid,))
    if not note:
        return jsonify({'error': 'Not found'}), 404
    note = note[0]
    if identity['role'] == 'staff' and note['user_id'] != identity['id']:
        return jsonify({'error': 'Forbidden'}), 403
    db_execute("DELETE FROM lead_notes WHERE id=%s", (nid,))
    return jsonify({'message': 'Deleted'})


# ─── EXTENDED PAYMENTS (reference_no field) ──────────────────
# The existing /api/bookings/<bid>/payment route needs one small
# update: store the optional reference_no.
# REPLACE the existing add_payment route with this:

@app.route('/api/bookings/<int:bid>/payment', methods=['POST'])
@jwt_required()
def add_payment(bid):
    data = request.get_json()
    pid = db_execute("""
        INSERT INTO payments (booking_id, amount, payment_method, payment_date, reference_no, notes)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (bid, data['amount'], data.get('payment_method','Cash'),
          data.get('payment_date', datetime.now().date()),
          data.get('reference_no', ''),
          data.get('notes','')))

    # Recalculate advance_paid & balance
    booking = db_query("SELECT * FROM bookings WHERE id=%s", (bid,))[0]
    paid = db_query("SELECT SUM(amount) as total FROM payments WHERE booking_id=%s", (bid,))
    total_paid = paid[0]['total'] or 0
    balance = booking['final_amount'] - total_paid
    db_execute("UPDATE bookings SET advance_paid=%s, balance=%s WHERE id=%s",
               (total_paid, balance, bid))

    identity = json.loads(get_jwt_identity())
    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'ADD_PAYMENT','booking',%s,%s)",
        (identity['id'], bid, f"Payment ₹{data['amount']} added to booking {bid}")
    )
    return jsonify({'id': pid, 'balance': balance, 'message': 'Payment added'})


# ─── CONVERSATIONS with call_duration ────────────────────────
# The existing add_conversation route needs to store call_duration.
# REPLACE the INSERT line inside add_conversation with:
#
#   cid = db_execute("""
#       INSERT INTO conversations (lead_id, user_id, summary, call_result, call_type,
#           next_followup_date, call_duration)
#       VALUES (%s,%s,%s,%s,%s,%s,%s)
#   """, (lid, identity['id'], data.get('summary',''), data.get('call_result',''),
#         data.get('call_type','Outgoing'), data.get('next_followup_date'),
#         data.get('call_duration')))


# ══════════════════════════════════════════════════════════════
# DATABASE MIGRATION — run these SQL statements once
# ══════════════════════════════════════════════════════════════
MIGRATION_SQL = """
-- WhatsApp message log
CREATE TABLE IF NOT EXISTS whatsapp_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    lead_id     INT NOT NULL,
    user_id     INT NOT NULL,
    message     TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Pinned notes per lead
CREATE TABLE IF NOT EXISTS lead_notes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    lead_id     INT NOT NULL,
    user_id     INT NOT NULL,
    note        TEXT NOT NULL,
    color       VARCHAR(20) DEFAULT 'yellow',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Add call_duration column to conversations (if not exists)
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS call_duration INT DEFAULT NULL COMMENT 'Duration in minutes';

-- Add reference_no column to payments (if not exists)
ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS reference_no VARCHAR(100) DEFAULT '' COMMENT 'UTR / cheque / transaction ref';
"""
# To apply: run each statement above in your MySQL client, or
# call db_execute() for each one at app startup.







@app.route('/api/tour-categories', methods=['GET'])
@jwt_required()
def get_tour_categories():
    cats = db_query("""
        SELECT tc.*,
               COUNT(DISTINCT ts.id) as subcat_count,
               COUNT(DISTINCT l.id)  as lead_count
        FROM tour_categories tc
        LEFT JOIN tour_subcategories ts ON ts.category_id = tc.id AND ts.is_active = 1
        LEFT JOIN leads l ON l.tour_category_id = tc.id
        GROUP BY tc.id
        ORDER BY tc.sort_order ASC, tc.name ASC
    """)
    if not cats:
        return jsonify([])
 
    # Attach subcategories
    for cat in cats:
        subs = db_query(
            "SELECT * FROM tour_subcategories WHERE category_id=%s ORDER BY sort_order ASC, name ASC",
            (cat['id'],)
        )
        cat['subcategories'] = subs or []
 
    return jsonify(cats)
 
 
@app.route('/api/tour-categories/<int:cid>', methods=['GET'])
@jwt_required()
def get_tour_category(cid):
    cat = db_query("SELECT * FROM tour_categories WHERE id=%s", (cid,))
    if not cat:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(cat[0])
 
 
@app.route('/api/tour-categories', methods=['POST'])
@jwt_required()
def create_tour_category():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    if not data.get('name','').strip():
        return jsonify({'error': 'Name required'}), 400
    cid = db_execute("""
        INSERT INTO tour_categories (name, description, icon, color, sort_order, is_active)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        data['name'].strip(),
        data.get('description',''),
        data.get('icon','fa-map-marked-alt'),
        data.get('color','#F97316'),
        data.get('sort_order', 0),
        data.get('is_active', 1)
    ))
    db_execute(
        "INSERT INTO activity_logs (user_id, action, details) VALUES (%s,'CREATE_TOUR_CATEGORY',%s)",
        (identity['id'], f"Created tour category: {data['name']}")
    )
    return jsonify({'id': cid, 'message': 'Category created'}), 201
 
 
@app.route('/api/tour-categories/<int:cid>', methods=['PUT'])
@jwt_required()
def update_tour_category(cid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    db_execute("""
        UPDATE tour_categories
        SET name=%s, description=%s, icon=%s, color=%s, sort_order=%s, is_active=%s
        WHERE id=%s
    """, (
        data.get('name','').strip(),
        data.get('description',''),
        data.get('icon','fa-map-marked-alt'),
        data.get('color','#F97316'),
        data.get('sort_order', 0),
        data.get('is_active', 1),
        cid
    ))
    return jsonify({'message': 'Updated'})
 
 
@app.route('/api/tour-categories/<int:cid>', methods=['DELETE'])
@jwt_required()
def delete_tour_category(cid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    # Remove sub-categories first (FK safety)
    db_execute("DELETE FROM tour_subcategories WHERE category_id=%s", (cid,))
    db_execute("DELETE FROM tour_categories WHERE id=%s", (cid,))
    return jsonify({'message': 'Deleted'})
 
 
@app.route('/api/tour-categories/<int:cid>/leads', methods=['GET'])
@jwt_required()
def get_category_leads(cid):
    leads = db_query("""
        SELECT l.id, l.lead_id, l.customer_name, l.mobile, l.tour_name, l.status, l.created_at
        FROM leads l
        WHERE l.tour_category_id = %s
        ORDER BY l.created_at DESC
        LIMIT 100
    """, (cid,))
    return jsonify(leads or [])
 
 
# ─── TOUR SUB-CATEGORIES ─────────────────────────────────────
 
@app.route('/api/tour-categories/<int:cid>/subcategories', methods=['POST'])
@jwt_required()
def create_subcategory(cid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    if not data.get('name','').strip():
        return jsonify({'error': 'Name required'}), 400
    sid = db_execute("""
        INSERT INTO tour_subcategories
            (category_id, name, description, duration_days, duration_nights,
             starting_price, tags, sort_order, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        cid,
        data['name'].strip(),
        data.get('description',''),
        data.get('duration_days'),
        data.get('duration_nights'),
        data.get('starting_price'),
        data.get('tags',''),
        data.get('sort_order', 0),
        data.get('is_active', 1)
    ))
    return jsonify({'id': sid, 'message': 'Sub-category created'}), 201
 
 
@app.route('/api/tour-subcategories/<int:sid>', methods=['GET'])
@jwt_required()
def get_subcategory(sid):
    sub = db_query("SELECT * FROM tour_subcategories WHERE id=%s", (sid,))
    if not sub:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(sub[0])
 
 
@app.route('/api/tour-subcategories/<int:sid>', methods=['PUT'])
@jwt_required()
def update_subcategory(sid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    db_execute("""
        UPDATE tour_subcategories
        SET name=%s, description=%s, duration_days=%s, duration_nights=%s,
            starting_price=%s, tags=%s, sort_order=%s, is_active=%s
        WHERE id=%s
    """, (
        data.get('name','').strip(),
        data.get('description',''),
        data.get('duration_days'),
        data.get('duration_nights'),
        data.get('starting_price'),
        data.get('tags',''),
        data.get('sort_order', 0),
        data.get('is_active', 1),
        sid
    ))
    return jsonify({'message': 'Updated'})
 
 
@app.route('/api/tour-subcategories/<int:sid>', methods=['DELETE'])
@jwt_required()
def delete_subcategory(sid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    db_execute("DELETE FROM tour_subcategories WHERE id=%s", (sid,))
    return jsonify({'message': 'Deleted'})
 
 
# ══════════════════════════════════════════════════════════════
# 3. DATABASE MIGRATION — run once in MySQL
# ══════════════════════════════════════════════════════════════
MIGRATION_SQL = """
-- Tour Categories table
CREATE TABLE IF NOT EXISTS tour_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    icon        VARCHAR(60)  DEFAULT 'fa-map-marked-alt',
    color       VARCHAR(20)  DEFAULT '#F97316',
    sort_order  INT          DEFAULT 0,
    is_active   TINYINT(1)   DEFAULT 1,
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
 
-- Tour Sub-Categories table
CREATE TABLE IF NOT EXISTS tour_subcategories (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    category_id     INT          NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    duration_days   INT          DEFAULT NULL,
    duration_nights INT          DEFAULT NULL,
    starting_price  DECIMAL(10,2) DEFAULT NULL,
    tags            VARCHAR(500) DEFAULT '',
    sort_order      INT          DEFAULT 0,
    is_active       TINYINT(1)   DEFAULT 1,
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES tour_categories(id) ON DELETE CASCADE
);
 
-- Link leads to a tour category (optional — for "View Leads" feature)
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS tour_category_id INT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tour_subcategory_id INT DEFAULT NULL;
 
-- Seed default categories matching your 4 requirements
INSERT INTO tour_categories (name, description, icon, color, sort_order) VALUES
('Taxi Service',       'Local and outstation taxi, airport transfers, corporate cabs', 'fa-taxi',           '#F59E0B', 1),
('Nepal Tour Package', 'Full Nepal tour packages — Kathmandu, Pokhara, Chitwan, etc.', 'fa-mountain',       '#10B981', 2),
('UP Tour Package',    'Uttar Pradesh pilgrim and leisure tours — Ayodhya, Kashi, Mathura, Agra', 'fa-place-of-worship', '#3B82F6', 3),
('Customise Tour',     'Custom itinerary tours built as per customer requirements',    'fa-sliders-h',      '#8B5CF6', 4);
 
-- Seed sample sub-categories for each
-- Taxi Service
INSERT INTO tour_subcategories (category_id, name, duration_days, starting_price, tags) VALUES
((SELECT id FROM tour_categories WHERE name='Taxi Service'), 'Local City Taxi',      1, 800,   'City, Local'),
((SELECT id FROM tour_categories WHERE name='Taxi Service'), 'Outstation One-Way',   1, 1500,  'Outstation'),
((SELECT id FROM tour_categories WHERE name='Taxi Service'), 'Outstation Round Trip',2, 2500,  'Outstation, Round Trip'),
((SELECT id FROM tour_categories WHERE name='Taxi Service'), 'Airport Transfer',     1, 1200,  'Airport'),
((SELECT id FROM tour_categories WHERE name='Taxi Service'), 'Corporate Monthly',    30,15000, 'Corporate');
 
-- Nepal Tour
INSERT INTO tour_subcategories (category_id, name, duration_days, duration_nights, starting_price, tags) VALUES
((SELECT id FROM tour_categories WHERE name='Nepal Tour Package'), 'Kathmandu Darshan',         4, 3, 8500,  'Kathmandu, Pashupatinath'),
((SELECT id FROM tour_categories WHERE name='Nepal Tour Package'), 'Kathmandu + Pokhara',       6, 5, 14000, 'Kathmandu, Pokhara'),
((SELECT id FROM tour_categories WHERE name='Nepal Tour Package'), 'Nepal Grand Tour',          8, 7, 18000, 'Kathmandu, Pokhara, Chitwan'),
((SELECT id FROM tour_categories WHERE name='Nepal Tour Package'), 'Muktinath Yatra',           6, 5, 22000, 'Muktinath, Religious'),
((SELECT id FROM tour_categories WHERE name='Nepal Tour Package'), 'Pashupatinath Special',     4, 3, 9000,  'Pashupatinath, Religious');
 
-- UP Tour
INSERT INTO tour_subcategories (category_id, name, duration_days, duration_nights, starting_price, tags) VALUES
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Ayodhya Darshan',              2, 1, 3500,  'Ayodhya, Ram Mandir'),
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Kashi Vishwanath Yatra',       3, 2, 5500,  'Varanasi, Kashi'),
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Prayagraj Triveni Sangam',     2, 1, 4000,  'Prayagraj, Sangam'),
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Ayodhya + Kashi + Prayagraj',  5, 4, 10500, 'Ayodhya, Kashi, Prayagraj'),
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Mathura + Vrindavan + Agra',   3, 2, 6500,  'Mathura, Vrindavan, Agra'),
((SELECT id FROM tour_categories WHERE name='UP Tour Package'), 'Char Dham UP Yatra',           7, 6, 16000, 'Badrinath, Kedarnath, Gangotri, Yamunotri');
 
-- Customise Tour
INSERT INTO tour_subcategories (category_id, name, tags) VALUES
((SELECT id FROM tour_categories WHERE name='Customise Tour'), 'Family Package',    'Family, Custom'),
((SELECT id FROM tour_categories WHERE name='Customise Tour'), 'Honeymoon Package', 'Honeymoon, Couple'),
((SELECT id FROM tour_categories WHERE name='Customise Tour'), 'Group Tour',        'Group'),
((SELECT id FROM tour_categories WHERE name='Customise Tour'), 'Pilgrimage Tour',   'Religious, Pilgrimage'),
((SELECT id FROM tour_categories WHERE name='Customise Tour'), 'Budget Tour',       'Budget');
"""


@app.route('/api/leads/trash', methods=['GET'])
@jwt_required()
def get_trash():
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    leads = db_query("""
        SELECT l.*, u.full_name as assigned_name, d.full_name as deleted_by_name
        FROM leads l
        LEFT JOIN users u ON l.assigned_to=u.id
        LEFT JOIN users d ON l.deleted_by=d.id
        WHERE l.is_deleted=1
        ORDER BY l.deleted_at DESC
    """)
    return jsonify(leads or [])


@app.route('/api/leads/<int:lid>/restore', methods=['POST'])
@jwt_required()
def restore_lead(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] not in ('admin', 'manager'):
        return jsonify({'error': 'Forbidden'}), 403
    lead = db_query("SELECT lead_id FROM leads WHERE id=%s AND is_deleted=1", (lid,))
    if not lead:
        return jsonify({'error': 'Not found or not deleted'}), 404
    db_execute(
        "UPDATE leads SET is_deleted=0, deleted_at=NULL, deleted_by=NULL WHERE id=%s", (lid,)
    )
    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'RESTORE_LEAD','lead',%s,%s)",
        (identity['id'], lid, f"Restored lead {lead[0]['lead_id']}")
    )
    return jsonify({'message': f"Lead {lead[0]['lead_id']} restored"})


@app.route('/api/leads/<int:lid>/permanent-delete', methods=['DELETE'])
@jwt_required()
def permanent_delete_lead(lid):
    identity = json.loads(get_jwt_identity())
    if identity['role'] != 'admin':
        return jsonify({'error': 'Forbidden — admin only'}), 403
    lead = db_query("SELECT lead_id FROM leads WHERE id=%s AND is_deleted=1", (lid,))
    if not lead:
        return jsonify({'error': 'Not found in trash'}), 404
    lead_id_str = lead[0]['lead_id']
    db_execute("DELETE FROM followups     WHERE lead_id=%s", (lid,))
    db_execute("DELETE FROM conversations WHERE lead_id=%s", (lid,))
    db_execute("DELETE FROM packages      WHERE lead_id=%s", (lid,))
    db_execute("DELETE FROM whatsapp_logs WHERE lead_id=%s", (lid,))
    db_execute("DELETE FROM lead_notes    WHERE lead_id=%s", (lid,))
    booking = db_query("SELECT id FROM bookings WHERE lead_id=%s", (lid,))
    if booking:
        db_execute("DELETE FROM payments WHERE booking_id=%s", (booking[0]['id'],))
    db_execute("DELETE FROM bookings WHERE lead_id=%s", (lid,))
    db_execute("DELETE FROM leads    WHERE id=%s",      (lid,))
    db_execute(
        "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) VALUES (%s,'PERMANENT_DELETE_LEAD','lead',%s,%s)",
        (identity['id'], lid, f"Permanently deleted lead {lead_id_str}")
    )
    return jsonify({'message': f'Lead {lead_id_str} permanently deleted'})


if __name__ == '__main__':
    app.run(port=5005, debug=True)