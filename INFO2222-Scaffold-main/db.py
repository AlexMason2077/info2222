'''
db
database file, containing all the logic to interface with the sql database
'''

from sqlalchemy import create_engine, MetaData, or_, Table
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
        salt = gensalt()
        hashed_password = hashpw(password.encode('utf-8'), salt)

        user = User(username=username, password=hashed_password,salt=salt)

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

def find_free_room_id():
    with Session(engine) as session:
        # 获取所有现有的room_id，按升序排序
        existing_ids = session.query(RoomInfo.room_id).order_by(RoomInfo.room_id).all()
        existing_ids = [id[0] for id in existing_ids]  # 将结果转换为单个数字列表

        # 寻找第一个空闲的ID
        free_id = 1
        while free_id in existing_ids:
            free_id += 1

        return free_id

def insert_message(room_id: int, sender: str, content: str):
    with Session(engine) as session:
        # 创建一个Message实例
        message = Message(room_id=room_id, sender=sender, content=content)
        
        # 添加这个实例到session
        session.add(message)
        
        # 提交session到数据库
        try:
            session.commit()
            print(f"Message added: {sender}: {content} in room {room_id}")
        except Exception as e:
            # 如果出现错误，回滚更改
            session.rollback()
            print(f"Failed to insert message: {e}")
        finally:
            # 关闭session
            session.close()

def get_all_messages():
    with Session(engine) as session:
        # 查询messages表中的所有记录
        messages = session.query(Message).all()

        # 用于存储所有消息信息的列表
        all_messages = []

        # 遍历每条消息记录，并收集其详细信息
        for message in messages:
            message_info = (message.id, message.room_id, message.sender, message.content)
            all_messages.append(message_info)

            # 如果需要在控制台打印每条消息的详细信息
            print(f"ID: {message.id}, Room ID: {message.room_id}, Sender: {message.sender}, Content: {message.content}")

        # 返回所有消息的详细信息列表
        return all_messages

def get_messages_by_room_id(room_id: int) -> list:
    with Session(engine) as session:
        # 查询指定room_id的所有消息
        messages = session.query(Message.sender, Message.content).filter(Message.room_id == room_id).all()

        # messages 已经是一个包含了很多元组的列表，每个元组包含(sender, content)
        return messages


def insert_public_key(username: str, public_key: str):
    with Session(engine) as session:
        # 创建一个Message实例
        PublicKey = PublicKeys(user_name = username, public_key = public_key)
        
        # 添加这个实例到session
        session.add(PublicKey)
        
        # 提交session到数据库
        try:
            session.commit()
            print(f"[DEBUG]: PublicKey added: {username}: {public_key}")
        except Exception as e:
            # 如果出现错误，回滚更改
            session.rollback()
            print(f"[DEBUG]: Failed to insert PublicKey: {e}")
        finally:
            # 关闭session
            session.close()

def get_public_key(username: str):
    with Session(engine) as session:
        try:
            # 查询数据库以获取给定用户名的公钥
            public_key = session.query(PublicKeys).filter_by(user_name=username).first()
            if public_key:
                return public_key.public_key
            else:
                return None
        except Exception as e:
            print(f"[DEBUG]: Failed to retrieve PublicKey: {e}")
            return None
        finally:
            session.close()


#################################################################################
# 下面是支持函数
#################################################################################

def drop_all_tables(database_url: str):
    # 创建数据库引擎
    engine = create_engine(database_url)

    # 创建元数据对象
    metadata = MetaData()

    # 反射数据库中的所有表
    metadata.reflect(bind=engine)

    # 删除所有表
    metadata.drop_all(engine)

    print("所有表已成功删除。")

def print_all_users():
    with Session(engine) as session:
        # 查询User表中的所有记录
        users = session.query(User).all()
        # 遍历每个用户对象，并打印其详细信息
        for user in users:
            print(f"Username: {user.username}, , Salt: {user.salt}, Password: {user.password}")


def get_all_room_info():
    with Session(engine) as session:
        # 查询RoomInfo表中的所有记录
        rooms = session.query(RoomInfo).all()

        # 如果需要，您可以在这里打印每个房间的信息，或者返回这些信息
        for room in rooms:
            print(f"Room ID: {room.room_id}, User A: {room.user_a}, User B: {room.user_b}")

        # 或者，如果您想返回这些记录以供进一步处理，可以这样做：
        return rooms

def drop_room_info_table():
    with engine.begin() as connection:
        # 直接删除RoomInfo表
        RoomInfo.__table__.drop(bind=engine, checkfirst=True)
        print("RoomInfo tabSle has been dropped.")

def view_tables():
    # 数据库连接字符串
    database_url = "sqlite:///database/main.db"

    # 创建数据库引擎
    engine = create_engine(database_url)

    # 创建元数据对象
    metadata = MetaData()

    # 使用反射加载所有表的信息
    metadata.reflect(bind=engine)

    # 遍历所有表，打印出表名和每列的名字及类型
    for table_name in metadata.tables:
        print(f"Table: {table_name}")
        # 获取表对象
        table = metadata.tables[table_name]
        # 打印列信息
        for column in table.c:
            print(f"  Column: {column.name}, Type: {column.type}")
        print("")  # 空行，用于分隔不同的表


##############################################################################
# friend request
##############################################################################

def send_friend_request(sender_username: str, receiver_username: str):
    print(f"sender:{sender_username}")
    print(f"receiver:{receiver_username}")
    with Session(engine) as session:
        # 检查接收者是否存在
        receiver = session.get(User, receiver_username)
        print(receiver)
        if not receiver:
            return "Receiver does not exist."
        
        # # 检查是否已经是好友
        # if are_friends(sender_username, receiver_username):
        #     return "Already friends."

        # 检查是否已经发送过好友请求
        existing_request = session.query(FriendRequest).filter(
        (FriendRequest.sender_id == sender_username) & 
        (FriendRequest.receiver_id == receiver_username) & 
        (FriendRequest.status.in_([RequestStatus.PENDING.value, RequestStatus.APPROVED.value]))
        ).first()
        if existing_request:
            return "Friend request already sent or already friends."

        # 创建并保存新的好友请求
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


def get_friend_requests_for_user(username: str):
    with Session(engine) as session:
        # 查询所有发给指定用户的好友请求
        friend_requests = session.query(FriendRequest).filter(
            FriendRequest.receiver_id == username,
            FriendRequest.status == RequestStatus.PENDING.value  # 假设我们只对“pending”的请求感兴趣
        ).all()
        return friend_requests


# def are_friends(username1, username2):
#     with Session(engine) as session:
#         friendship = session.query(Friendship).filter(
#             ((Friendship.user_username == username1) & (Friendship.friend_username == username2)) |
#             ((Friendship.user_username == username2) & (Friendship.friend_username == username1))
#         ).first()
#         return friendship is not None
    
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
            # 根据ID找到好友请求记录
            friend_request = session.query(FriendRequest).filter(FriendRequest.id == request_id).first()
            if not friend_request:
                return False, "Friend request not found."

            # 更新状态
            friend_request.status = new_status
            if new_status == "approved":
                # 检查是否已存在好友关系
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

# def approve_friend_request(request_id: int):
#     with Session(engine) as session:
#         # 找到对应的好友请求
#         friend_request = session.query(FriendRequest).filter_by(id=request_id).first()
#         print(f"found friend_request: {friend_request}")
    
#         new_friendship1 = Friendship(user_username=friend_request.sender_id, friend_username=friend_request.receiver_id)
#         new_friendship2 = Friendship(user_username=friend_request.receiver_id, friend_username=friend_request.sender_id)
#         session.add(new_friendship1)
#         session.add(new_friendship2)
#         session.commit()
#         print(f"We are friends!!!!!!!: {new_friendship1.user_username} <--> {new_friendship2.user_username}")


def get_friends_for_user(username: str):
    with Session(engine) as session:
        # 查询当前用户的好友关系
        friendships = session.query(Friendship).filter(
            (Friendship.user_username == username)
        ).all()

        # 提取好友用户名
        friends_usernames = [friendship.friend_username for friendship in friendships]

        # （可选）获取好友的详细信息，例如用户名和名字
        friends = []
        for friend_username in friends_usernames:
            friend = session.query(User).filter(User.username == friend_username).first()
            if friend:
                friends.append({"username": friend.username})
        
        return friends



def print_all_friends():
    with Session(engine) as session:
        # 获取所有用户
        users = session.query(User).all()

        # 对于每个用户，打印他们的好友列表
        for user in users:
            print(f"User {user.username}'s friends:")
            # 调用 get_friends_for_user 函数获取好友列表
            friends = get_friends_for_user(user.username)
            print(friends)
            if friends:
                for friend in friends:
                    print(f"  - {friend['username']} ")
            else:
                print("  - No friends")
            print("\n")

