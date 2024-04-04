'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import *

from pathlib import Path

# creates the database directory
Path("database") \
    .mkdir(exist_ok=True)

# "database/main.db" specifies the database file
# change it if you wish
# turn echo = True to display the sql output
engine = create_engine("sqlite:///database/main.db", echo=False)

# initializes the database
Base.metadata.create_all(engine)

# inserts a user to the database
def insert_user(username: str, password: str):
    with Session(engine) as session:
        user = User(username=username, password=password)
        session.add(user)
        session.commit()

# gets a user from the database
def get_user(username: str):
    with Session(engine) as session:
        return session.get(User, username)


def insert_friendship(user_id: str, friend_id: str, room_id: int):
    with Session(engine) as session:
        friendship = Friendship(user_id=user_id, friend_id=friend_id, room_id=room_id)
        session.add(friendship)
        session.commit()


def get_user_friendships(username: str):
    with Session(engine) as session:
        friendships = session.query(Friendship).filter((Friendship.user_id == username) | (Friendship.friend_id == username)).all()
        return [(friendship.friend_id if friendship.user_id == username else friendship.user_id, friendship.room_id) for friendship in friendships]


def get_users_in_room(room_id: int):
    with Session(engine) as session:
        friendships = session.query(Friendship).filter(Friendship.room_id == room_id).all()
        users = set([friendship.user_id for friendship in friendships] + [friendship.friend_id for friendship in friendships])
        return list(users)


def create_chat_room(user1, user2):
    
    existing_room = get_users_in_room(user1, user2)
    if existing_room:
        #print(f"Existing room_id: {existing_room}")
        return existing_room 
    
 
    room_id = Room().create_room(user1, user2)  
    insert_friendship(user1, user2, room_id)  
    #print(f"Newly created room_id: {room_id}")
    return room_id

def get_user_friends(username: str):
    with Session(engine) as session:
        # This is just a sample logic
        friendships = session.query(Friendship).filter((Friendship.user_id == username) | (Friendship.friend_id == username)).all()
        friends = [f.friend_id if f.user_id == username else f.user_id for f in friendships]
        return friends