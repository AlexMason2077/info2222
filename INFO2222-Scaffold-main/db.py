'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import and_, create_engine, MetaData, or_, Table
from sqlalchemy.orm import Session
from models import *  
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

# for hash and salt
from bcrypt import gensalt, hashpw, checkpw

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
        user_online = UserOnline(username=username,is_online=False)
        session.add(user)
        session.add(user_online)
        session.commit()

# gets a user from the database
def get_user(username: str):
    with Session(engine) as session:
        return session.get(User, username)
    
def get_online_user(username: str):
    with Session(engine) as session:
        return session.get(UserOnline, username)

# add roominfo record to the database
def insert_room(room_id: int, user_a: str, user_b: str):
    with Session(engine) as session:
        room_info = RoomInfo(room_id=room_id, user_a=user_a, user_b=user_b)
        session.add(room_info)
        try:
            session.commit()
            print(f"Room {room_id} created with users {user_a} and {user_b}.")
        except Exception as e:
            session.rollback()  # rollback if error occurs
            print(f"Failed to insert room info: {e}")
        finally:
            session.close()  # ensure the session is properly closed 

def find_room_id_by_users(user_a: str, user_b: str) -> int:
    with Session(engine) as session:
        # use or_ to construct logical OR conditions
        room_info = session.query(RoomInfo).filter(
            or_(
                (RoomInfo.user_a == user_a) & (RoomInfo.user_b == user_b),
                (RoomInfo.user_a == user_b) & (RoomInfo.user_b == user_a)
            )
        ).first()

        if room_info is not None:
            return room_info.room_id
        
        return None

def find_free_room_id():
    with Session(engine) as session:
        # get all existing room IDs, sorted in ascending order
        existing_ids = session.query(RoomInfo.room_id).order_by(RoomInfo.room_id).all()
        existing_ids = [id[0] for id in existing_ids]  # convert the result to a single list of numbers

        # find the first available ID
        free_id = 1
        while free_id in existing_ids:
            free_id += 1

        return free_id

def insert_message(room_id: int, sender: str, content: str):
    with Session(engine) as session:
        # create a message instance
        message = Message(room_id=room_id, sender=sender, content=content)
        
        # add the instance to the session
        session.add(message)
        
        # commit the sessino to the database
        try:
            session.commit()
            print(f"Message added: {sender}: {content} in room {room_id}")
        except Exception as e:
            #roll back if error
            session.rollback()
            print(f"Failed to insert message: {e}")
        finally:
            # close the session
            session.close()

def get_all_messages():
    with Session(engine) as session:
        # query all records in the messages table
        messages = session.query(Message).all()

        # list to store all message information
        all_messages = []

        # Iterate through each message record and collect its detailed information
        for message in messages:
            message_info = (message.id, message.room_id, message.sender, message.content)
            all_messages.append(message_info)

            print(f"ID: {message.id}, Room ID: {message.room_id}, Sender: {message.sender}, Content: {message.content}")

        # Return a list of detailed information for all messages
        return all_messages

def get_messages_by_room_id(room_id: int) -> list:
    with Session(engine) as session:
        # query all messages for the specified room_id
        messages = session.query(Message.sender, Message.content).filter(Message.room_id == room_id).all()

        # messages is already a list containing many tuples, each tuple containing (sender, content)
        return messages


#################################################################################
# functions below 
#################################################################################

def drop_all_tables(database_url: str):
    engine = create_engine(database_url)

    metadata = MetaData()

    metadata.reflect(bind=engine)

    metadata.drop_all(engine)

    print("all tables have been successfully deleted.")

def print_all_users():
    with Session(engine) as session:
        # query all records in the user table
        users = session.query(User).all()
        # Iterate through each user object and print its detailed information
        for user in users:
            print(f"Username: {user.username}, , Salt: {user.salt}, Password: {user.password}")


def get_all_room_info():
    with Session(engine) as session:
        # query all records in the roominfo table
        rooms = session.query(RoomInfo).all()

        for room in rooms:
            print(f"Room ID: {room.room_id}, User A: {room.user_a}, User B: {room.user_b}")
        
        return rooms

def drop_room_info_table():
    with engine.begin() as connection:
        # directly delete the roominfo table
        RoomInfo.__table__.drop(bind=engine, checkfirst=True)
        print("RoomInfo tabSle has been dropped.")

def view_tables():
    # database connection string
    database_url = "sqlite:///database/main.db"

    # create a database engine
    engine = create_engine(database_url)

    # create a metadataobject
    metadata = MetaData()

    # Load information for all tables using reflection
    metadata.reflect(bind=engine)

    # iterat through all tables, print table names and the name and type of each
    for table_name in metadata.tables:
        print(f"Table: {table_name}")
        # get table object
        table = metadata.tables[table_name]
        # print column information
        for column in table.c:
            print(f"  Column: {column.name}, Type: {column.type}")
        print("")  # empty line for separating different tables


##############################################################################
# friend request
##############################################################################

def send_friend_request(sender_username: str, receiver_username: str):
    print(f"sender:{sender_username}")
    print(f"receiver:{receiver_username}")
    with Session(engine) as session:
        # check if the recipient exists
        receiver = session.get(User, receiver_username)
        print(receiver)
        if not receiver:
            return "Receiver does not exist."
        
         # check if a friend request has already been sent
        existing_request = session.query(FriendRequest).filter(
        (FriendRequest.sender_id == sender_username) & 
        (FriendRequest.receiver_id == receiver_username) & 
        (FriendRequest.status.in_([RequestStatus.PENDING.value, RequestStatus.APPROVED.value]))
        ).first()
        if existing_request:
            return "Friend request already sent or already friends."

        # create and save a new friend request
        new_request = FriendRequest(sender_id=sender_username, receiver_id=receiver_username, status=RequestStatus.PENDING.value)
        session.add(new_request)
        try:
            session.commit()
            print("Friend request successfully added.")
        except Exception as e:
            print(f"Failed to insert friend request: {e}")
            session.rollback()
        session.commit()
        
        return "Friend request sent successfully."


def add_friend(user_username, friend_username):
    with Session(engine) as session:
        # check if they are already friends
        existing_friendship = session.query(Friendship).filter(
            ((Friendship.user_username == user_username) & (Friendship.friend_username == friend_username)) |
            ((Friendship.user_username == friend_username) & (Friendship.friend_username == user_username))
        ).first()
        
        if existing_friendship:
            return "Already friends."
        
        # add friendship
        friendship = Friendship(user_username=user_username, friend_username=friend_username)
        session.add(friendship)
        session.commit()
        return "Friend added successfully."
    

def remove_friend(user_username, friend_username):
    with Session(engine) as session:
        friendship = session.query(Friendship).filter(
            ((Friendship.user_username == user_username) & (Friendship.friend_username == friend_username)) |
            ((Friendship.user_username == friend_username) & (Friendship.friend_username == user_username))
        ).first()
        if friendship:
            session.delete(friendship)
            session.commit()
            return True
        return False

def can_join_chatroom(username1, username2):
    # use SQLALchemy session to query the friendship table
    with Session() as session:
        friendship = session.query(Friendship).filter(
            ((Friendship.user_username == username1) & (Friendship.friend_username == username2)) |
            ((Friendship.user_username == username2) & (Friendship.friend_username == username1))
        ).first()
        return bool(friendship)  # return true if the friendship is found

def get_friend_requests_for_user(username: str):
    with Session(engine) as session:
        # query all friend requests sent to the specified user
        friend_requests = session.query(FriendRequest).filter(
            or_(
                FriendRequest.receiver_id == username,
                FriendRequest.sender_id == username
            ),
            FriendRequest.status == RequestStatus.PENDING.value
        ).all()
        return friend_requests



def are_friends(user1: str, user2: str):
    with Session(engine) as session:
        # check if the two users are friends
        friendship = session.query(Friendship).filter(
            or_(
                and_(Friendship.user_username == user1, Friendship.friend_username == user2),
                and_(Friendship.user_username == user2, Friendship.friend_username == user1)
            )
        ).first()
        return friendship is not None
    
def print_all_friend_requests():
    with Session(engine) as session:
        friend_requests = session.query(FriendRequest).all()
        print("All Friend Requests:")
        for request in friend_requests:
            print(f"ID: {request.id}, Sender: {request.sender_id}, Receiver: {request.receiver_id}, Status: {request.status}")
from sqlalchemy.engine.reflection import Inspector

def print_table_names():
    inspector = Inspector.from_engine(engine)
    table_names = inspector.get_table_names()
    print("All table names in the database:")
    for name in table_names:
        print(name)


def update_friend_request_status(request_id: int, new_status: str):
    with Session(engine) as session:
        try:
            # find the friend request record by ID
            friend_request = session.query(FriendRequest).filter(FriendRequest.id == request_id).first()
            if not friend_request:
                return False, "Friend request not found."

            # update the status
            friend_request.status = new_status
            if new_status == "approved":
                # check a friendship
                exists = session.query(Friendship).filter_by(user_username=friend_request.sender_id, friend_username=friend_request.receiver_id).first()
                if not exists:
                    new_friendship1 = Friendship(user_username=friend_request.sender_id, friend_username=friend_request.receiver_id)
                    new_friendship2 = Friendship(user_username=friend_request.receiver_id, friend_username=friend_request.sender_id)
                    session.add(new_friendship1)
                    session.add(new_friendship2)
                    print(f"We are friends!!!!!!!: {new_friendship1.user_username} <--> {new_friendship2.user_username}")
            
            session.commit()
            return True, "Friend request status updated successfully."
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating friend request status: {e}")
            return False, "Error occurred during the update."

def get_friends_for_user(username: str):
    online_user = get_online_user(username)
    print(username)
    print(online_user.get_online())
    online_user.set_online(True)
    with Session(engine) as session:
        # check friendship
        friendships = session.query(Friendship).filter(
            (Friendship.user_username == username)
        ).all()

        # extract the friend's username
        friends_usernames = [friendship.friend_username for friendship in friendships]
        friends = []
        for friend_username in friends_usernames:
            friend = session.query(UserOnline).filter(UserOnline.username == friend_username).first()
            if friend:
                #friend.set_online(True)
                friends.append({"username": friend.username,'is_online': friend.is_online})
        print("Friends and their online status:", friends)
        return friends

def print_all_friends():
    with Session(engine) as session:
        # retrieve all users
        users = session.query(User).all()

        # for each user, print their list of friends
        for user in users:
            print(f"User {user.username}'s friends:")
            # call the get_friends_for_user function to retrieve the list of friends
            friends = get_friends_for_user(user.username)
            print(friends)
            if friends:
                for friend in friends:
                    print(f"  - {friend['username']} ")
            else:
                print("  - No friends")
            print("\n")

