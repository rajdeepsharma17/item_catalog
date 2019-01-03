#!/usr/bin/python
# # -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import requests

from database_setup import Base, ToDoItem, User

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
def getUsers():
    res = requests.get('https://jsonplaceholder.typicode.com/users')
    for item in res.json():
        user = User(name=item['name'], email=item['email'], picture="")
        session.add(user)
        session.commit()


# ADD dummy Todos
def getData():
    res = requests.get('https://jsonplaceholder.typicode.com/todos')
    for item in res.json():
        todo = ToDoItem(title=item['title'],
                        userId=item['userId'],
                        completed=item['completed'])
        session.add(todo)
        session.commit()


if __name__ == '__main__':
    getUsers()
    getData()
