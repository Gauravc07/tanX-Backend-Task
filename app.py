from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from datetime import timedelta
from collections import defaultdict
import os
import websocket
import json
import threading
import time
import smtplib

app = Flask(__name__)

subscriptions = defaultdict(int)
WEB_SOCKET = None

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+mysqlconnector://newuser:newpassword@localhost/new_database')
print("Database URL set to:", os.environ.get('DATABASE_URL'))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

jwt = JWTManager(app)
db = SQLAlchemy(app)

BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin = db.Column(db.String(10), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='created')

def getActiveAlerts():
    return Alert.query.filter(Alert.status == 'created')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not all(key in data for key in ['username', 'password', 'email']):
        return jsonify({'message': 'All fields are required: username, password, and email'}), 400

    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({'message': 'This username is already in use. Please choose another one.'}), 400

    new_user = User(
        username=data['username'],
        password=data['password'],
        email=data['email']
    )
    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Error occurred while creating the account. Please try again later.'}), 500

    return jsonify({'message': 'Registration completed successfully. You can now log in.'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if user and user.password == data['password']:
        access_token = create_access_token(identity=user.id)
        return jsonify({'message': 'Login successful!', 'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Incorrect username or password'}), 401

@app.route('/alerts/create', methods=['POST'])
@jwt_required()
def create_alert():
    data = request.get_json()
    if 'coin' not in data or 'target_price' not in data:
        return jsonify({'message': 'Both coin and target_price are required'}), 400

    current_user_id = get_jwt_identity()
    existing_alert = Alert.query.filter_by(user_id=current_user_id, coin=data['coin']).first()

    if existing_alert:
        if existing_alert.status == 'deleted':
            existing_alert.status = 'created'
            db.session.commit()
            return jsonify({'message': 'Alert has been reactivated successfully'}), 200
        else:
            return jsonify({'message': 'An alert for this coin is already present'}), 400

    new_alert = Alert(user_id=current_user_id, coin=data['coin'], target_price=data['target_price'])
    db.session.add(new_alert)
    db.session.commit()

    unsubscribeFromSocket(list(subscriptions.keys()))
    subscriptions[data["coin"].lower() + "usdt@kline_1m"] += 1

    print("\t\tCurrent subscriptions : ", subscriptions)
    sendToSocket(list(subscriptions.keys()))

    return jsonify({'message': 'Alert created successfully'}), 201

@app.route('/alerts/delete/real/<int:alert_id>', methods=['DELETE'])
@jwt_required()
def delete_alert_deleteRow(alert_id):
    current_user_id = get_jwt_identity()
    alert = Alert.query.filter_by(id=alert_id, user_id=current_user_id).first()

    if alert:
        db.session.delete(alert)
        db.session.commit()
        return jsonify({'message': 'Alert has been removed from the database successfully'}), 200
    else:
        return jsonify({'message': 'Alert not found or you are not authorized to delete it'}), 404

@app.route('/alerts', methods=['GET'])
@jwt_required()
def get_user_alerts():
    current_user_id = get_jwt_identity()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    status_filter = request.args.get('status', type=str)

    alerts_query = Alert.query.filter_by(user_id=current_user_id, status='created' if not status_filter else status_filter)
    alerts = alerts_query.paginate(page=page, per_page=per_page, error_out=False)

    if not alerts.items:
        return jsonify({'message': 'No alerts found for this user'}), 404

    alert_list = [{
        'id': alert.id,
        'coin': alert.coin,
        'target_price': alert.target_price,
        'status': alert.status
    } for alert in alerts.items]

    response_headers = {
        'X-Total-Count': alerts.total,
        'X-Total-Pages': alerts.pages,
        'X-Current-Page': alerts.page,
        'X-Per-Page': per_page
    }

    return jsonify({'alerts': alert_list}), 200, response_headers

@app.route('/alerts/<status>', methods=['GET'])
@jwt_required()
def get_user_alerts_by_status(status):
    current_user_id = get_jwt_identity()
    valid_statuses = ['created', 'deleted', 'triggered']
    if status not in valid_statuses:
        return jsonify({'message': 'Invalid status. Available statuses: created, deleted, triggered'}), 400

    alerts = Alert.query.filter_by(user_id=current_user_id, status=status).all()

    if not alerts:
        return jsonify({'message': f'No alerts with status "{status}" found for this user'}), 404

    alert_list = [{
        'id': alert.id,
        'coin': alert.coin,
        'target_price': alert.target_price,
        'status': alert.status
    } for alert in alerts]

    return jsonify({'alerts': alert_list})

SOCK_URL = "wss://stream.binance.com/ws"

def unsubscribeFromSocket(lst):
    WEB_SOCKET.send(
        json.dumps({"method": "UNSUBSCRIBE", "params": lst, "id": 312})
    )

def sendToSocket(lst):
    WEB_SOCKET.send(
        json.dumps({"method": "SUBSCRIBE", "params": lst, "id": 1})
    )

def connect_to_smtp_server():
    try:
        s = smtplib.SMTP('smtp.office365.com', 587)
        s.starttls()
        s.login("cointargetalert@outlook.com", "Outlook99")
        return s
    except smtplib.SMTPException as e:
        print("SMTP Connection Error:", str(e))
        return None

def send_email(user_email, coin_name, smtp_email_obj):
    SUBJECT = 'Target Alert'
    TEXT = f'Dear User, \n The coin {coin_name} that you set for alert has reached its target.\n Thank you.'
    message = f'Subject: {SUBJECT}\n\n{TEXT}'
    smtp_email_obj.sendmail("cointargetalert@outlook.com", user_email, message)
    smtp_email_obj.quit()

s = connect_to_smtp_server()

def on_message(ws, message):
    data = json.loads(message)
    reqMsg = {"coin": data["s"][:-4].upper(), "price": float(data["k"]["c"])}

    with app.app_context():
        satisfyingAlerts = Alert.query.filter(Alert.status == 'created', Alert.coin == reqMsg["coin"], 
                        Alert.target_price <= reqMsg["price"]).all()

        userDetails = []
        oldSubscriptions = subscriptions.copy()

        for alert in satisfyingAlerts:
            userDetails.append({ 'email': User.query.filter(User.id == alert.user_id).first().email,
                "coin": reqMsg["coin"], "price": reqMsg["price"] })

            key = reqMsg["coin"].lower() + "usdt@kline_1m"
            if subscriptions[key] == 1:
                del subscriptions[key]
            else:
                subscriptions[key] -= 1

            alert.status = 'triggered'
            first_dict = userDetails[0]
            email_value = first_dict['email']
            coin_name = first_dict['coin']
            send_email(email_value, coin_name, s)
            print("\t\tAlerts Triggered : ", userDetails)
        
        if satisfyingAlerts:
            db.session.commit()
        
        if oldSubscriptions.keys() != subscriptions.keys():
            unsubscribeFromSocket(list(oldSubscriptions.keys()))
            sendToSocket(list(subscriptions.keys()))

def on_close(ws, close_status_code, close_msg):
    print("### WebSocket connection closed ###")
