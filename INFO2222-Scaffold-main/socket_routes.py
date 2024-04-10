'''
socket_routes
file containing all the routes related to socket.io
'''


from flask_socketio import join_room, emit, leave_room
from flask import request
import time

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room

import db

room = Room()



# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
    join_room(int(room_id))


    emit("incoming", {"content": f"{username} has connected", "color": "green", "type": "system"}, to=int(room_id))

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return

    emit("incoming", {"content": f"{username} has disconnected", "color": "red", "type": "system"}, to=int(room_id))


# send message event handler
@socketio.on("send")
def send(username, message, room_id):
    # 假设所有通过这个函数发送的消息默认为"text"类型，除非指定了其他类型
    emit("incoming", {
        "content": f"{username}: {message}", 
        "color": "black", 
        "type": "text"
    }, to=room_id)
    
    # 在数据库插入消息时包含消息类型
    db.insert_message(room_id, username, message)

    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):
    print("start join_room")
    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"

    # Check if they are friends!
    users = db.get_friends_for_user(sender_name)
    usernames = [user['username'] for user in users]  # 使用列表推导式提取所有 'username' 的值

    if not (receiver_name in usernames):
        return f"{receiver_name} is not your friend, please send a request🥰"

    room_id_current = room.get_room_id(receiver_name)

    if room_id_current is not None:
        room.join_room(sender_name, room_id_current)
        join_room(room_id_current)
        # emit to everyone in the room except the sender
        emit("incoming", {"content": f"{sender_name} has joined the room.", "color": "green", "type": "system"}, to=room_id_current, include_self=False)
        
        # emit only to the sender
        emit("incoming", {"content": f"{sender_name} has joined the room. Now talking to {receiver_name}.", "color": "green", "type": "system"})
        return room_id_current


    # if the user isn't inside of any room, 
    # perhaps this user has recently left a room
    # or is simply a new user looking to chat with someone

    # it will not create if the room exists

    room_id_current = room.create_room(sender_name, receiver_name)

    join_room(room_id_current)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"), to=room_id_current)

    return room_id_current

@socketio.on("GetHistoryMessages")
def GetHisoryMessages(sender_name, receiver_name):
    # 查找两个用户间的房间ID
    room_id_stored = db.find_room_id_by_users(sender_name, receiver_name)
    if room_id_stored:
        messages_list = []  # 初始化一个空列表来收集消息
        # 获取房间ID对应的所有消息
        for e in db.get_messages_by_room_id(room_id_stored):
            # 构建每条消息的内容
            message_content = f"{e[0]}: {e[1]}"
            # 将构建的消息内容添加到列表中
            messages_list.append({
                "content": message_content, 
                "color": "black", 
                "type": "text"
            })

        # 使用单个emit发送整个消息列表
        emit("incoming_messages_list", {"messages": messages_list}, to=room_id_stored)


# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    emit("incoming", {"content": f"{username} has left the room.", "color": "red", "type": "system"}, to=room_id)
    leave_room(room_id)
    room.leave_room(username)
