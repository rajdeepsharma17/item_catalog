from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))



class ToDoItem(Base):
    __tablename__ = 'menu_item'

    title = Column(String(150), nullable=False)
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    completed = Column(Boolean, default=False)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'title': self.title,
            'id': self.id,
            'userId': self.user_id,
            'completed': self.completed
        }


engine = create_engine('sqlite:///todo.db')


Base.metadata.create_all(engine)
