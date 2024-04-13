'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, jsonify, render_template, request, abort, url_for ,redirect, session
from flask_socketio import SocketIO
import db
import secrets
from bcrypt import gensalt, hashpw, checkpw
from functools import wraps
from sqlalchemy.orm import aliased

# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

from flask_session import Session  # 导入 Session
# Flask 应用配置
app.config['SESSION_TYPE'] = 'filesystem'  # session 数据存储在文件系统
app.config['SESSION_FILE_DIR'] = 'session_files'  # 存储 session 文件的目录
app.config['SESSION_PERMANENT'] = False  # session 的持久性
app.config['SESSION_USE_SIGNER'] = True  # 启用 session 的签名
Session(app)  # 初始化应用以使用 Flask-Session


# don't remove this!!
import socket_routes


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            # 如果用户未登录，可以重定向到登录页面，或返回错误响应
            return redirect(url_for('login'))
            # 或者返回错误响应
            # return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

@app.route('/logout')
def logout():
    # 清除会话
    session.clear()
    # 重定向到登录页面
    return redirect(url_for('index'))

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():

    if not request.is_json:
        abort(404)


    username = request.json.get("username")
    hashedPassword = request.json.get("password") # has been hashed once

    print(f"[DEBUG]: Hash({username} entered password): {hashedPassword}") # DEBUG PURPOSE
    
    user =  db.get_user(username)

    if user is None:
        return "Error: User does not exist!🤡"

    if not checkpw(hashedPassword.encode('utf-8'), user.password):
        return "Error: Password does not match!🤡"

    # 用户登录验证成功后
    session['username'] = username  # 存储用户名到 session

    return url_for('home', username=request.json.get("username"))

# handles a get request to the signup page
@app.route("/signup")
def signup():
    return render_template("signup.jinja")

# handles a post request when the user clicks the signup button
@app.route("/signup/user", methods=["POST"])
def signup_user():
    if not request.is_json:
        abort(404)
    username = request.json.get("username")
    hashedPassword = request.json.get("password")

    if db.get_user(username) is None:
        print(f"[DEBUG]: {username}'s password encrpted once at jinja: {hashedPassword}")
        db.insert_user(username, hashedPassword) # will be hashed again in this function
        session['username'] = username  # 用户注册成功后，存储用户名到 session
        return url_for('home', username=username)

    return "Error: User already exists!"

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

# home page, where the messaging app is
@app.route("/home")
@login_required
def home():
    if request.args.get("username") is None:
        abort(404)
    return render_template("home.jinja", username=request.args.get("username"))

@app.route("/api/sensitive_data")
@login_required
def sensitive_data():
    # 处理敏感数据请求
    return jsonify({"data": "sensitive information"})


#============================================================================
# FRIEND

@app.route("/send_friend_request", methods=["POST"])
def send_request():
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400
    if 'sender' not in data or 'receiver' not in data:
        return jsonify({"error": "Missing 'sender' or 'receiver' in data"}), 400
    
    # 在调用db函数之前和之后添加更多的错误检查和日志输出，以确定问题所在
    print(data)
    sender = data['sender']
    receiver = data['receiver']
    
    if sender == receiver:
        return jsonify({"error": "Cannot send friend request to yourself."}),400
    
    if db.are_friends(sender,receiver):
        return jsonify({"error": "You are already friends!"}),400
    result = db.send_friend_request(data['sender'], data['receiver'])
    if not result:
        return jsonify({"error": "An error occurred while processing your request"}), 400
    
    return jsonify({"message": result})

@app.route('/get_friend_requests')
def get_friend_requests():
    current_user = request.args.get('username')
    if not current_user:
        return jsonify({"error": "Missing username parameter"}), 400
    
    try:
        friend_requests = db.get_friend_requests_for_user(current_user)
        return jsonify([{
            "id": fr.id,
            "sender": fr.sender_id,
            "receiver": fr.receiver_id,
            "status": fr.status
        } for fr in friend_requests])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/update_friend_request", methods=["POST"])
def update_friend_request():
    data = request.get_json()
    print(data)  # 打印接收到的数据，看是否符合预期
    if not data or 'request_id' not in data or 'status' not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    request_id = data['request_id']
    new_status = data['status']
    
    try:
        # 在这里添加更多的日志输出，如果有异常，输出异常信息
        result = db.update_friend_request_status(request_id, new_status)
        print("Update successful")  # 如果成功，输出成功信息
        socketio.emit('friend_request_update', {'message': 'Update your friend requests list'})
        return jsonify({"message": "Friend request updated successfully."})
    except Exception as e:
        print(f"Error: {e}")  # 输出错误信息
        return jsonify({"error": str(e)}), 500


@app.route("/get_friends")
def get_friends():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400

    friends = db.get_friends_for_user(username)
    return jsonify(friends)

#============================================================================
# Public key receive and store

@app.route('/upload_public_key', methods=['POST'])
def upload_public_key():
    # 从POST请求数据中获取公钥
    username = request.json['username']
    public_key = request.json['publicKey']
    
    # 在这里处理公钥，例如存储到数据库中或进行其他操作
    print(f"[DEBUG] Received {username}'s {public_key}")
    db.insert_public_key(username,public_key)
    return 'Public key received successfully'

@app.route('/getPublicKey', methods=['POST'])
def get_public_key():
    # 尝试从请求体中获取username
    data = request.get_json()
    username = data.get('username')  # 使用get方法安全地访问字典键

    if not username:
        # 如果没有提供username或者username为空
        return jsonify({"error": "Missing or empty username parameter"}), 400

    try:
        public_key = db.get_public_key(username)
        if public_key:
            return jsonify({"public_key": public_key})
        else:
            # 如果找不到公钥
            return jsonify({"error": "Public key not found"}), 404
    except Exception as e:
        # 如果查询过程中发生了异常
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # db.view_tables()
    # db.print_all_friend_requests()
    # db.approve_friend_request(2)
    # db.print_all_friends()
    # db.get_all_messages()
    # db.print_table_names()
    # db.drop_all_tables("sqlite:///database/main.db")

    socketio.run(app, host='0.0.0.0', port=8999, debug=True, ssl_context=('./certs/server.crt', './certs/server.key'))

    # db.print_all_users()
    # print(db.get_messages_by_room_id(4))
    # print(db.get_messages_by_room_id(4))
