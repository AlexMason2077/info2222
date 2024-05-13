'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''

from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime  # 导入 datetime

from typing import Dict
from enum import Enum as PyEnum
import db

# data models
class Base(DeclarativeBase):
    pass

# inherit from a Base, this is a fucking table in db
# model to store user information
class User(Base):
    __tablename__ = "user"
    
    # looks complicated but basically means
    # I want a username column of type string,
    # and I want this column to be my primary key
    # then accessing john.username -> will give me some data of type string
    # in other words we've mapped the username Python object property to an SQL column of type String 
    username: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String) 
    
class UserOnline(Base):
    __tablename__ = "user_online"
    username = Column(String, primary_key=True)
    is_online = Column(Boolean, default=False,nullable=False)
    def set_online(self, online: bool):
        """Method to update user's online status."""
        self.is_online = online
    def get_online(self):
        return self.is_online

# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        pass
    
    def get(self):
        return db.find_free_room_id()

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.dict: Dict[str, int] = {}

    def create_room(self, sender: str, receiver: str) -> int:
        # try to find this room by 2 uses
        room_id = db.find_room_id_by_users(sender,receiver)
        if not room_id:
            room_id = self.counter.get()
            db.insert_room(room_id,sender,receiver)

        self.dict[sender] = room_id
        self.dict[receiver] = room_id
        return room_id
    
    def join_room(self,  sender: str, room_id: int) -> int:
        self.dict[sender] = room_id

    def leave_room(self, user):
        if user not in self.dict.keys():
            return
        del self.dict[user]

    def get_users_in_room(self, room_id: int) -> list[str]:
        return [user for user, r_id in self.dict.items() if r_id == room_id]


class RoomInfo(Base):
    __tablename__ = "RoomInfo"

    room_id = Column(Integer, primary_key=True)
    user_a = Column(String)
    user_b = Column(String)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer)
    sender = Column(String)
    content = Column(String)


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    publish_date = Column(DateTime, nullable=False)
    
    # 正确位置在类定义内部
    comments = relationship("Comment", order_by="Comment.id", back_populates="article")

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    commenter = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    comment_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    article = relationship("Article", back_populates="comments")

##############################################################################
# friend request
##############################################################################

class RequestStatus(PyEnum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class FriendRequest(Base):
    __tablename__ = 'friend_request'
    id = Column(Integer, primary_key=True)
    sender_id = Column(String, ForeignKey('user.username'))
    receiver_id = Column(String, ForeignKey('user.username'))
    status = Column(String)

class Friendship(Base):
    __tablename__ = 'friendship'
    user_username = Column(String,primary_key=True)
    friend_username = Column(String,primary_key=True)
