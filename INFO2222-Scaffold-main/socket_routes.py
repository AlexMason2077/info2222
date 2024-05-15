'''
socket_routes
file containing all the routes related to socket.io
'''

from flask_socketio import join_room, emit, leave_room
from functools import wraps
from flask import request, session
from sqlalchemy.orm import Session
import time

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room,User,GroupUser,GroupMessage,GroupChat

import db

room = Room()





# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
def connect():
    with Session(db.engine) as session:
        username = request.cookies.get("username")
        room_id = request.cookies.get("room_id")
        if room_id is None or username is None:
            return
        user = session.query(db.UserOnline).filter_by(username=username).first()
        if user is None:
            emit('error', {'message': 'User not found'})
            return
        user.is_online = True
        session.commit()
        join_room(int(room_id))
        emit("incoming", (f"{username} has connected","green"), to=int(room_id))

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    with Session(db.engine) as session:
        username = request.cookies.get("username")
        room_id = request.cookies.get("room_id")
        if room_id is None or username is None:
            return
        user = session.query(db.UserOnline).filter_by(username=username).first()
        if user is None:
            emit('error', {'message': 'User not found'})
            return
        user.is_online = False
        session.commit()
        leave_room(room_id)
        emit("incoming", (f"{username} has disconnected", "red"), to=int(room_id))



@socketio.on('send')
def handle_send_message(sender, message, room_id):
    db.insert_message(room_id, sender, message)
    emit('incoming', {'sender': sender, 'message': message}, room=room_id)
# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):
    #print("start join_room")

    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"

    # Check if they are friends!
    users = db.get_friends_for_user(sender_name)
    usernames = [user['username'] for user in users]  

    if not (receiver_name in usernames):
        return f"{receiver_name} is not your friend, please send a request🥰"

    room_id_current = db.find_room_id_by_users(sender_name,receiver_name)

    print(room_id_current)

    if room_id_current is not None:

        room.join_room(sender_name, room_id_current)

        join_room(room_id_current)
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.","green"), to=room_id_current, include_self=False)
        
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"))

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
    room_id_stored = db.find_room_id_by_users(sender_name, receiver_name)
    if room_id_stored:
        messages_list = db.get_messages_by_room_id(room_id_stored)
        emit("incoming_messages_list", {"messages": [{"sender": msg.sender, "content": msg.content} for msg in messages_list]}, to=request.sid)
        print(messages_list)

# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    emit("incoming", (f"{username} has left the room.", "red"), to=room_id)
    leave_room(room_id)
    room.leave_room(username)


@socketio.on('friend_request_sent')
def handle_friend_request_sent(data):
    print("Friend request sent from:", data['sender'], "to:", data['receiver'])
    # Here you can broadcast to specific rooms or globally as needed
    print("Emitting friend_request_update event")
    emit('friend_request_update', {'message': 'Update your friend requests list'})
    print("done")

##############################################################################
# group chat
##############################################################################

@socketio.on("send_group_message")
def handle_group_message(data):
    print("send group message")
    group_id = data.get('group_id')
    sender = data.get('sender')
    message = data.get('message')


    if not db.is_user_in_group(sender, group_id):
        emit("error", {"error": "You are not a member of this group."}, room=request.sid)
        return
    db.insert_group_message(group_id, sender, message)
    print(message)

    room_id = group_id + 10000  # 群组ID加上10000
    emit("incoming_group_message", {"sender": sender, "message": message}, room=room_id)


@socketio.on("GetGroupHistoryMessages")
def get_group_history_messages(data):
    group_id = data.get('group_id')
    messages = db.get_group_messages(group_id)
    room_id = group_id + 10000  # 群组ID加上10000
    messages_data = [{"sender": msg.sender, "content": msg.content} for msg in messages]
    emit("incoming_group_messages_list", {"messages": messages_data}, room=room_id)


@socketio.on("join_group")
def join_group(data):
    group_id = data.get('group_id')
    username = data.get('username')

    user = db.get_user(username)
    if user is None:
        return {"error": "Unknown user!"}

    if not db.is_user_in_group(username, group_id):
        emit("error", {"error": "You are not a member of this group."}, room=request.sid)
        return

    # groups = db.get_groups_for_user(username)
    # group_ids = [group['id'] for group in groups]

    # if group_id not in group_ids:
    #     return {"error": "You are not a member of this group."}

    room_id = group_id + 10000  # 群组ID加上10000
    join_room(room_id)

    emit("clear_messages", room=room_id)

    # 发送用户加入群组的消息给群组中的其他用户，但不包括自己

    # 发送历史消息给加入群组的用户
    messages = db.get_group_messages(group_id)
    #messages_data = [{"sender": msg.sender, "content": msg.content} for msg in messages]
    #emit("incoming_group_messages_list", {"messages": messages_data}, room=room_id)
    
    #emit("incoming_group_message", {"sender": username, "message": "has joined the room."}, room=room_id)

    return {"group_id": group_id, "message": f"{username} has joined the room."}