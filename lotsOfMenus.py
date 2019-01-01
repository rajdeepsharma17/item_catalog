from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import requests

from database_setup import  Base, ToDoItem, User

engine = create_engine('sqlite:///todo.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()


def getData():
    res = requests.get('https://jsonplaceholder.typicode.com/todos')
    for item in res.json():
        todo = ToDoItem(title=item['title'], userId=item['userId'], completed=item['completed'])
        session.add(todo)
        session.commit()


getData()

