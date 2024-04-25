'''
socket_routes
file containing all the routes related to socket.io
'''

from flask_socketio import join_room, emit, leave_room
from functools import wraps
from flask import request, session
import time

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room,User

import db

room = Room()


def authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):

        if 'username' not in session:
            disconnect() 
            return  
        else:
            return f(*args, **kwargs)  
    return wrapped


# when the client connects to a socket
# this event is emitted when the io() function is called in JS
@socketio.on('connect')
@authenticated_only
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
    user = db.get_online_user(username)
    if user is None:
        emit('error', {'message': 'User not found'})
        return
    else:
        user.set_online(True)
        print(user.get_online())
        print("111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111")
        #session.commit()
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
    user = db.get_online_user(username)
    if user is None:
        emit('error', {'message': 'User not found'})
        return
    else:
        user.set_online(False)
        print(user.get_online())
        print("22222222222222222222222222222222222222222222222222222222222222222222222222")
    emit("incoming", {"content": f"{username} has disconnected", "color": "red", "type": "system"}, to=int(room_id))


@socketio.on("send")
@authenticated_only
def send(username, message, room_id):
    users_in_room = room.get_users_in_room(room_id)

    if len(users_in_room) < 2:
        emit("error", {"message": "2 users both need to be online"}, to=request.sid)
        return 

    emit("incoming", {
        "content": f"{username}: {message}", 
        "color": "black", 
        "type": "text"
    }, to=room_id)
    
    # include the message type when inserting a message into the database
    db.insert_message(room_id, username, message)

    return
    
# join room event handler
# sent when the user joins a room
@socketio.on("join")
@authenticated_only
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
@authenticated_only
def GetHisoryMessages(sender_name, receiver_name):
    room_id_stored = db.find_room_id_by_users(sender_name, receiver_name)
    if room_id_stored:
        messages_list = [] 

        for e in db.get_messages_by_room_id(room_id_stored):
            message_content = f"{e[0]}: {e[1]}"
            messages_list.append({
                "content": message_content, 
                "color": "black", 
                "type": "text"
            })

        emit("incoming_messages_list", {"messages": messages_list}, to=request.sid)


# leave room event handler
@socketio.on("leave")
@authenticated_only
def leave(username, room_id):
    emit("incoming", {"content": f"{username} has left the room.", "color": "red", "type": "system"}, to=room_id)
    leave_room(room_id)
    room.leave_room(username)


@socketio.on('friend_request_sent')
def handle_friend_request_sent(data):
    print("Friend request sent from:", data['sender'], "to:", data['receiver'])
    # Here you can broadcast to specific rooms or globally as needed
    print("Emitting friend_request_update event")
    socketio.emit('friend_request_update', {'message': 'Update your friend requests list'})
