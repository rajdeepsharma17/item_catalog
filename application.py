from flask import Flask, render_template
from flask import request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, ToDoItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "ToDo Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///todo.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    """
    This method creates anti-forgery state token.
    Returns:
        HTML Template
    """
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    This method authenticates the user using
    googleplus OAuth and validates against anti-
    forgery token.
    Returns:
        HTML Template
    """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if (stored_access_token is not None and
       gplus_id == stored_gplus_id):
        response = make_response(json.dumps('''Current user is
        already connected.'''),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius: 150px;
    -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    """
    This method creates a new user into
    the database.
    Args:
        login_session: contains user info
    Returns:
        user id
    """
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    """
    This method fetches user info from
    database against given user id.
    Args:
        user_id: Id of User
    Returns:
        User
    """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    """
    This method return user info from databse
    against given email.
    Args:
        email: Email Id
    Returns:
        user id
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    """
    This method disconnects a connected user.
    Returns:
        response
    """
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view todo Information
@app.route('/todo/<int:todo_id>/JSON')
def todoMenuJSON(todo_id):
    """
    JSON API to return todo against given
    todo id (Only for development purpose).
    Args:
        todo_id: Id of required Todo
    Returns:
        JSON
    """
    todo = session.query(ToDoItem).filter_by(id=todo_id).one()
    return jsonify(ToDo=todo.serialize)


@app.route('/todo/JSON')
def todosJSON():
    """
    JSON API to return all todos in
    databse. (Only for development purpose).
    Returns:
        JSON
    """
    todos = session.query(ToDoItem).all()
    return jsonify(Todos=[r.serialize for r in todos])


# Show all todos
@app.route('/')
@app.route('/todo/')
def showtodos():
    """
    If the user is authenticated shows all
    todos returrn Index Page otherwise.
    Returns:
        HTML Template
    """
    if 'username' not in login_session:
        return render_template('index.html')
    else:
        userId = login_session['user_id']
        todos = session.query(ToDoItem).filter_by(userId=userId)
        print(login_session['user_id'])
        return render_template('todos.html', todos=todos)

# Create a new todo


@app.route('/todo/new/', methods=['GET', 'POST'])
def newtodo():
    """
    Allows User to create new Todos.
    Returns:
        HTML Template
    """
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newtodo = ToDoItem(
            title=request.form['title'],
            userId=login_session['user_id'],
            completed=False)
        session.add(newtodo)
        flash('New todo %s Successfully Created' % newtodo.title)
        session.commit()
        return redirect(url_for('showtodos'))
    else:
        return render_template('newTodo.html')


# Edit a todo


@app.route('/todo/<int:todo_id>/edit/', methods=['GET', 'POST'])
def edittodo(todo_id):
    """
    Allows User to edit an existing
    Todo.
    Args:
        todo_id: Id of Todo to edit
    Returns:
        HTML Template
    """
    editedtodo = session.query(
        ToDoItem).filter_by(id=todo_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedtodo.userId != login_session['user_id']:
        return '''<script>function myFunction()
        {alert('You are not authorized to edit this todo.
         Please create your own todo in order to edit.');}
        </script><body onload='myFunction()''>'''
    if request.method == 'POST':
        if request.form['title']:
            editedtodo.title = request.form['title']
            editedtodo.completed = request.form['completed']
            flash('todo Successfully Edited %s' % editedtodo.title)
            return redirect(url_for('showtodos'))
    else:
        return render_template('editTodo.html', todo=editedtodo)


# Delete a todo
@app.route('/todo/<int:todo_id>/delete/', methods=['GET', 'POST'])
def deletetodo(todo_id):
    """
    Allows User to delete an existing
    Todo.
    Args:
        todo_id: Id of Todo to edit
    Returns:
        HTML Template
    """
    todoToDelete = session.query(
        ToDoItem).filter_by(id=todo_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if todoToDelete.userId != login_session['user_id']:
        return '''<script>function myFunction()
         {alert('You are not authorized to delete this todo.
         Please create your own todo in order to delete.');}
         </script><body onload='myFunction()''>'''
    if request.method == 'POST':
        session.delete(todoToDelete)
        flash('%s Successfully Deleted' % todoToDelete.title)
        session.commit()
        return redirect(url_for('showtodos', todo_id=todo_id))
    else:
        return render_template('deleteTodo.html', todo=todoToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
