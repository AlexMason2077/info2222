'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, jsonify, render_template, request, abort, url_for
from flask_socketio import SocketIO
import db
import secrets
from models import RequestStatus

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
    friends = ["nihao"]    
    return render_template("home.jinja", username=request.args.get("username"), friends=friends)

@app.route("/send_friend_request", methods=["POST"])
def send_request():
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400
    if 'sender' not in data or 'receiver' not in data:
        return jsonify({"error": "Missing 'sender' or 'receiver' in data"}), 400
    
    result = db.send_friend_request(data['sender'], data['receiver'])
    return jsonify({"message": result})


@app.route("/update_friend_request", methods=["POST"])
def update_request():
    data = request.json
    if not data or 'request_id' not in data or 'status' not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    try:
        new_status = RequestStatus(data['status'])
    except ValueError:
        return jsonify({"error": "Invalid status value"}), 400
    
    result = db.update_friend_request(data['request_id'], new_status)
    return jsonify(result)

# 假设这是处理加入聊天室请求的 Flask 路由
@app.route("/join_chatroom", methods=["POST"])
def join_chatroom():
    data = request.json
    username1 = data['username1']
    username2 = data['username2']

    if not db.are_friends(username1, username2):
        return jsonify({"error": "You must be friends to join the same chatroom."}), 403

    # 加入聊天室的逻辑...



if __name__ == '__main__':
    #socketio.run(app, host='0.0.0.0', port=8999, allow_unsafe_werkzeug=True)
    socketio.run(app, host='0.0.0.0', port=8999, debug=True)
    
