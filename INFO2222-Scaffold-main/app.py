'''
app.py contains all of the server application
this is where you'll find all of the get/post request handlers
the socket event handlers are inside of socket_routes.py
'''

from flask import Flask, jsonify, render_template, request, abort, url_for ,redirect, session
from flask_socketio import SocketIO
from datetime import datetime
import db
import secrets
from bcrypt import gensalt, hashpw, checkpw
from functools import wraps
from sqlalchemy.orm import aliased
from bleach import clean

# import logging

# this turns off Flask Logging, uncomment this to turn off Logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__,static_folder='static')

# secret key used to sign the session cookie
app.config['SECRET_KEY'] = secrets.token_hex()
socketio = SocketIO(app)

from flask_session import Session  #Session
# Flask application configuration
app.config['SESSION_TYPE'] = 'filesystem'  # session store in session_files
app.config['SESSION_FILE_DIR'] = 'session_files'  
app.config['SESSION_PERMANENT'] = False  
app.config['SESSION_USE_SIGNER'] = True  # signature of session
app.config['SESSION_COOKIE_SECURE'] = True  # can only send cookie in HTTPS 
app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScript cannot visit cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF Protection

Session(app)  


# don't remove this!!
import socket_routes

# index page
@app.route("/")
def index():
    return render_template("index.jinja")

# login page
@app.route("/login")
def login():    
    print("Hi?")
    return render_template("login.jinja")

@app.route('/logout')
def logout():
    # clear the session
    session.clear()
    # redirect to the index page
    return redirect(url_for('index'))

# handles a post request when the user clicks the log in button
@app.route("/login/user", methods=["POST"])
def login_user():
    if not request.is_json:
        abort(404)

    username = request.json.get("username")
    password = request.json.get("password") 

    #print(f"[DEBUG]: Hash({username} entered password): {hashedPassword}") # DEBUG PURPOSE
    
    user =  db.get_user(username)

    if user is None:
        return "Error: User does not exist!🤡"

    if password != user.password:
        return "Error: Password does not match!🤡"
    print("Hi1?")
    # after successful user login authentication
    session['username'] = username   # store user name into session 
    print("Hi2?")

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
    username = clean(request.json.get("username"))
    password = request.json.get("password")

    if db.get_user(username) is None:
        db.insert_user(username, password)  # 默认角色为 student，is_muted 默认为 False
        session['username'] = username  # 将用户名存储到 session 中
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
    requested_username = request.args.get("username")
    
    # # Verify the user name in session , if it same as the request one 
    # if requested_username != session.get('username'):
    #     # if inconsistent, return an error and redirect to another page
    #     abort(403)  # Forbidden access
    return render_template("home.jinja", username=request.args.get("username"))


@app.route('/knowledge')
def show_knowledge():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    articles = db.get_all_articles()  # 使用封装的函数获取所有文章
    return render_template('knowledge.jinja', username=username, articles=articles)

@app.route('/knowledge/new_article')
def new_article_form():
    username = session.get('username')  # 从会话获取用户名
    if not username:
        # 如果没有找到用户名，重定向到登录页面
        return redirect(url_for('login'))
    return render_template('new_article.jinja', username=username)

@app.route("/knowledge/new_article", methods=["POST"])
def submit_article():
    if 'username' not in session:
        abort(403)  # 用户未登录

    username = session['username']
    
    # 检查用户是否被禁言
    if is_user_muted(username):
        return jsonify({"success": False, "error": "User is muted and cannot post articles."})

    data = request.json
    title = data['title']
    content = data['content']
    author = data['author']
    publish_date = datetime.now()  # 使用当前时间作为发布日期

    # 调用之前定义的插入文章的函数
    db.insert_article(title, content, author, publish_date)

    # 返回成功消息
    return jsonify({"success": True})


@app.route('/article/<int:article_id>')
def article_detail(article_id):
    article = db.get_article_by_id(article_id)
    if article is None:
        abort(404)  
    return render_template('article_detail.jinja', article=article)

@app.route('/api/article/<int:article_id>')
def api_article_detail(article_id):
    article = db.get_article_by_id(article_id)
    if article is None:
        return jsonify({'error': 'Article not found'}), 404
    return jsonify({
        'title': article.title,
        'content': article.content,
        'author': article.author  # 确保包含作者信息
    })

@app.route('/api/articles')
def api_articles_list():
    articles = db.get_all_articles()  # 假设这个函数返回数据库中所有文章的列表
    articles_data = [{
        'id': article.id,
        'title': article.title
    } for article in articles]
    return jsonify(articles_data)

# 删除文章的 API 路由
@app.route("/api/delete_article/<article_id>", methods=["POST"])
def delete_article(article_id):
    if 'username' not in session:
        abort(403)

    username = session['username']
    if is_user_muted(username):
        return jsonify({"success": False, "error": "User is muted"})

    db.delete_article(article_id)
    return jsonify({"success": True})

# 编辑文章的 API 路由
@app.route("/api/edit_article/<article_id>", methods=["POST"])
def edit_article(article_id):
    if 'username' not in session:
        abort(403)

    username = session['username']
    if is_user_muted(username):
        return jsonify({"success": False, "error": "User is muted"})

    data = request.json
    title = data.get('title')
    content = data.get('content')

    db.edit_article(article_id, title, content)
    return jsonify({"success": True})


@app.route("/api/add_comment", methods=["POST"])
def add_comment():
    if 'username' not in session:
        abort(403)
    
    username = session['username']
    if is_user_muted(username):
        return jsonify({"success": False, "error": "User is muted"})

    data = request.json
    article_id = data.get('article_id')
    content = data.get('content')
    
    db.add_comment(article_id, username, content)
    return jsonify({"success": True})

@app.route('/api/comments/<int:article_id>')
def get_comments(article_id):
    comments = db.get_comments_by_article_id(article_id)
    return jsonify([{
        'commenter': comment.commenter,
        'content': comment.content,
        'comment_date': comment.comment_date.strftime("%Y-%m-%d %H:%M:%S")
    } for comment in comments])

@app.route("/api/get_user_status", methods=["GET"])
def get_user_status():
    if 'username' not in session:
        return jsonify({"is_muted": True})

    username = session['username']
    user = db.get_user(username)
    if user:
        return jsonify({"is_muted": user.is_muted})
    else:
        return jsonify({"is_muted": True})
#============================================================================
# FRIEND

@app.route("/send_friend_request", methods=["POST"])
def send_request():
    if 'username' not in session:
        return jsonify({"error": "Authentication required"}), 401

    sender = session['username']
    receiver = request.json.get('receiver')
    
    if not receiver:
        return jsonify({"error": "Missing 'receiver' in data"}), 400
    if not db.get_user(receiver):
        return jsonify({"error": "User does not exist!"}), 404
    if sender == receiver:
        return jsonify({"error": "Cannot send friend request to yourself."}), 400
    if db.are_friends(sender, receiver):
        return jsonify({"error": "You are already friends!"}), 400

    result = db.send_friend_request(sender, receiver)
    if result:
        return jsonify({"message": "Friend request sent successfully"})
    else:
        return jsonify({"error": "An error occurred while processing your request"}), 400


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
    print(data)
    if not data or 'request_id' not in data or 'status' not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    request_id = data['request_id']
    new_status = data['status']
    
    try:
        result = db.update_friend_request_status(request_id, new_status)
        print("Update successful") 
        socketio.emit('friend_request_update', {'message': 'Update your friend requests list'})
        return jsonify({"message": "Friend request updated successfully."})
    except Exception as e:
        print(f"Error: {e}") 
        return jsonify({"error": str(e)}), 500

@app.route("/get_friends")
def get_friends():
    username = request.args.get("username")
    user = db.get_online_user(username)
    #user.set_online(True)
    print(username)
    print(user.get_online())
    print(3333333333333333333333333333333333333333333333333)
    if not username:
        return jsonify({"error": "Missing username"}), 400

    friends = db.get_friends_for_user(username)
    return jsonify(friends)
    
# 根据用户名获取用户角色
@app.route("/get_role/<username>", methods=["GET"])
def get_role(username):
    user = db.get_user(username)
    if user:
        return {"username": user.username, "role": user.role, "is_muted": user.is_muted}
    else:
        return {"error": "User not found"}, 404

# 获取所有用户信息
@app.route("/get_all_users", methods=["GET"])
def get_all_users():
    if 'username' not in session:
        abort(403)

    current_user = db.get_user(session['username'])
    if current_user and current_user.role in ['admin', 'staff']:
        all_users = db.get_all_users()
        return jsonify([{"username": user.username, "role": user.role, "is_muted": user.is_muted} for user in all_users])
    else:
        abort(403)

# 渲染设置页面
@app.route("/settings", methods=["GET"])
def settings():
    if 'username' not in session:
        abort(403)
    
    username = session['username']
    user = db.get_user(username)
    
    if user:
        if user.role in ['admin', 'staff']:
            all_users = db.get_all_users()
        else:
            all_users = []
        return render_template('settings.jinja', user=user, username=username, all_users=all_users)
    else:
        return "Error: User not found", 404

@app.route("/toggle_mute/<username>", methods=["POST"])
def toggle_mute(username):
    if 'username' not in session:
        abort(403)

    current_user = db.get_user(session['username'])
    if current_user and current_user.role in ['admin', 'staff']:
        user = db.get_user(username)
        if user:
            if current_user.role == 'staff' and user.role != 'student':
                return jsonify({"error": "Staff can only mute students"}), 403

            mute = request.json.get('mute')
            user.is_muted = mute
            db.update_user(user)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "User not found"}), 404
    else:
        abort(403)



@app.route("/toggle_role/<username>", methods=["POST"])
def toggle_role(username):
    if 'username' not in session:
        abort(403)

    current_user = db.get_user(session['username'])
    if current_user and current_user.role == 'admin':
        user = db.get_user(username)
        if user:
            new_role = request.json.get('role')
            if new_role in ['student', 'staff']:  # 确保角色为 student 或 staff
                user.role = new_role
                db.update_user(user)
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Invalid role"}), 400
        else:
            return jsonify({"error": "User not found"}), 404
    else:
        abort(403)

def is_user_muted(username):
    user = db.get_user(username)
    return user.is_muted if user else False


#################################################################################
@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    data = request.get_json()
    if not data or 'friend_username' not in data:
        return jsonify({"error": "Missing friend_username"}), 400

    user_username = session['username']
    friend_username = data['friend_username']

    if db.remove_friend(user_username, friend_username):
        return jsonify({"message": "Friend removed successfully"})
    else:
        return jsonify({"error": "Friend could not be removed"}), 400



if __name__ == '__main__':
    # db.view_tables()
    # db.print_all_friend_requests()
    # db.approve_friend_request(2)
    # db.print_all_friends()
    # db.get_all_messages()
    # db.print_table_names()
    # db.drop_all_tables("sqlite:///database/main.db")

    # socketio.run(app, host='0.0.0.0', port=8999, debug=True, ssl_context=('./certs/server.crt', './certs/server.key'))
    socketio.run(app, host='0.0.0.0', port=8998, debug=True)
    # db.print_all_users()
    # print(db.get_messages_by_room_id(4))
    # print(db.get_messages_by_room_id(4))
