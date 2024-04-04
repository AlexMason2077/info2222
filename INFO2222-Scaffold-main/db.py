'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import *


from pathlib import Path
from sqlalchemy import or_

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

# 添加RoomInfo记录到数据库
def insert_room(room_id: int, user_a: str, user_b: str):
    with Session(engine) as session:
        room_info = RoomInfo(room_id=room_id, user_a=user_a, user_b=user_b)
        session.add(room_info)
        try:
            session.commit()
            print(f"Room {room_id} created with users {user_a} and {user_b}.")
        except Exception as e:
            session.rollback()  # 如果发生错误，则回滚
            print(f"Failed to insert room info: {e}")
        finally:
            session.close()  # 确保session被正确关闭


def find_room_id_by_users(user_a: str, user_b: str) -> int:
    with Session(engine) as session:
        # 使用or_来构建逻辑或条件
        room_info = session.query(RoomInfo).filter(
            or_(
                (RoomInfo.user_a == user_a) & (RoomInfo.user_b == user_b),
                (RoomInfo.user_a == user_b) & (RoomInfo.user_b == user_a)
            )
        ).first()

        if room_info is not None:
            return room_info.room_id
        
        return None

def send_friend_request(sender_username: str, receiver_username: str):
    with Session(engine) as session:
        # 检查接收者是否存在
        receiver = session.get(User, receiver_username)
        if not receiver:
            return "Receiver does not exist."
        
        # 检查是否已经发送了好友请求或已经是好友
        existing_request = session.query(FriendRequest).filter(
            ((FriendRequest.sender_id == sender_username) & (FriendRequest.receiver_id == receiver_username)) |
            ((FriendRequest.sender_id == receiver_username) & (FriendRequest.receiver_id == sender_username))
        ).first()

        if existing_request:
            return "Friend request already sent or already friends."

        # 创建新的好友请求
        new_request = FriendRequest(sender_id=sender_username, receiver_id=receiver_username, status=RequestStatus.PENDING.value)
        session.add(new_request)
        session.commit()
        
        return "Friend request sent successfully."


def update_friend_request(request_id: int, new_status: RequestStatus):
    with Session(engine) as session:
        friend_request = session.query(FriendRequest).filter_by(id=request_id).first()
        
        if not friend_request:
            return {"error": "Friend request not found."}
        
        friend_request.status = new_status.value
        session.commit()
        
        # 如果请求被接受，更新好友列表
        if new_status == RequestStatus.APPROVED:
            add_friend(friend_request.sender_id, friend_request.receiver_id)
        
        return {"message": "Friend request updated successfully."}


########################################################################################################################################
########################################################################################################################################


# deletes a user from the database by username
def delete_user(username: str):
    with Session(engine) as session:
        # Query the user by username
        user = session.query(User).filter_by(username=username).first()
        if user:
            # If user exists, delete it
            session.delete(user)
            session.commit()
            return True  # Indicate the user was found and deleted
        else:
            return False  # Indicate no user was found with that username


def add_friend(user_username, friend_username):
    with Session(engine) as session:
        # 检查是否已经是好友
        existing_friendship = session.query(Friendship).filter(
            ((Friendship.user_username == user_username) & (Friendship.friend_username == friend_username)) |
            ((Friendship.user_username == friend_username) & (Friendship.friend_username == user_username))
        ).first()
        
        if existing_friendship:
            return "Already friends."
        
        # 添加好友关系
        friendship = Friendship(user_username=user_username, friend_username=friend_username)
        session.add(friendship)
        session.commit()
        return "Friend added successfully."
    
def can_join_chatroom(username1, username2):
    # 使用 SQLAlchemy session 来查询 Friendship 表
    with Session() as session:
        friendship = session.query(Friendship).filter(
            ((Friendship.user_username == username1) & (Friendship.friend_username == username2)) |
            ((Friendship.user_username == username2) & (Friendship.friend_username == username1))
        ).first()
        return bool(friendship)  # 如果找到了好友关系，返回 True


def are_friends(username1, username2):
    with Session(engine) as session:
        friendship = session.query(Friendship).filter(
            ((Friendship.user_username == username1) & (Friendship.friend_username == username2)) |
            ((Friendship.user_username == username2) & (Friendship.friend_username == username1))
        ).first()
        return friendship is not None
