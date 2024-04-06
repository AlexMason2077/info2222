'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, jsonify, render_template, request, abort, url_for
from flask_socketio import SocketIO
import db
import secrets

# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__)

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

# don't remove this!!
import socket_routes

# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    return render_template("login.jinja")

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)

    username = request.json.get("username")
    password = request.json.get("password")

    user =  db.get_user(username)
    if user is None:
        return "Error: User does not exist!"

    if user.password != password:
        return "Error: Password does not match!"

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
    password = request.json.get("password")

    if db.get_user(username) is None:
        db.insert_user(username, password)
        return url_for('home', username=username)
    return "Error: User already exists!"

# handler when a "404" error happens
@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.jinja'), 404

# home page, where the messaging app is
@app.route("/home")
def home():
    if request.args.get("username") is None:
        abort(404)
    return render_template("home.jinja", username=request.args.get("username"))


@app.route("/send_friend_request", methods=["POST"])
def send_request():
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400
    if 'sender' not in data or 'receiver' not in data:
        return jsonify({"error": "Missing 'sender' or 'receiver' in data"}), 400
    
    # 在调用db函数之前和之后添加更多的错误检查和日志输出，以确定问题所在
    print(data)
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


if __name__ == '__main__':
    #db.view_tables()
    #db.print_all_friend_requests()
    #db.print_all_friends()
    #db.get_all_messages()
    #db.print_table_names()
    socketio.run(app, host='0.0.0.0', port=8999, debug=True)

    # db.drop_room_info_table()
    # db.get_all_messages()
    # print(db.get_messages_by_room_id(4))
