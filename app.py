# sql injection, alapvető gombok, flashek, welcome page, error handling, qol

from functions import *
from flask import Flask, render_template, request, redirect, url_for, g, session, current_app, flash
import functools
import pymysql
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'F33811E3C49CF7F69EDC56C7AAA9B'

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    db='PhoneBook'
)


def user(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        username = session.get('username')
        if username is None:
            return redirect(url_for('welcome'))
        with connection.cursor() as cursor:
            sql = "SELECT role FROM users WHERE username = %s;"
            cursor.execute(sql, username)
            role = cursor.fetchone()[0]
        if role in ['user', 'admin']:
            session['role'] = role
            return view(**kwargs)

        return redirect(url_for('welcome'))

    return wrapped_view


def admin(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        username = session.get('username')
        if username is None:
            return redirect(url_for('welcome'))
        with connection.cursor() as cursor:
            sql = "SELECT role FROM users WHERE username = %s;"
            cursor.execute(sql, session['username'])
            role = cursor.fetchone()[0]
        if role == 'admin':
            session['role'] = role
            return view(**kwargs)

        return redirect(url_for('no_access'))

    return wrapped_view


@app.before_request
def load_current_user():
    if session.get('username') is not None:
        g.user = {'username': session['username']}
    else:
        g.user = None


class Person:
    def __init__(self, person):
        self.id = person[0]
        self.name = person[1]
        self.phone_number = person[2]
        self.city = person[3]


class User:
    def __init__(self, user):
        self.username = user[0]
        self.role = user[1]


save_form = {
    'name': '',
    'phone_number': '',
    'city': '',
    'username': '',
 }


@app.route('/login', methods=("GET", "POST"))
def login():
    global save_form
    if request.method == "POST":
        with connection.cursor() as cursor:
            sql = "SELECT password FROM users WHERE username = %s;"
            username = request.form['username'].strip()
            cursor.execute(sql, username)

            try:
                hash_in_db = cursor.fetchone()[0]
            except TypeError:
                flash('User does not exist.')
                save_form['username'] = username
                return render_template("login.html", save_form=save_form)

            hash_from_input = hashlib.md5(request.form['password'].encode()).hexdigest()
            if hash_in_db == hash_from_input:
                session.clear()
                session['username'] = username
                flash('You logged in.')
                return redirect(url_for('index'))

            else:
                flash('Password is incorrect.')

            save_form['username'] = username

    return render_template("login.html", save_form=save_form)


@app.route('/logout', methods=("GET", "POST"))
def logout():
    session.clear()
    flash('You logged out.')
    return redirect(url_for('welcome'))


@app.route('/register', methods=("GET", "POST"))
def register():
    global save_form
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_again = request.form["password_again"]
        if is_username_taken(username) and username != "":
            flash("Username is taken.")
            save_form['username'] = username
            return render_template('register.html', save_form=save_form)
        elif password != password_again:
            flash('Passwords do not match.')
            save_form['username'] = username
            return render_template('register.html', save_form=save_form)
        elif username != '' and password != '':
            hashed = hashlib.md5(password.encode()).hexdigest()
            with connection.cursor() as cursor:
                sql = "INSERT INTO `users` (`username`, `password`, `role`) VALUES (%s, %s, %s);"
                cursor.execute(sql, (username, hashed, "user"))
                connection.commit()
                session.clear()
                session['username'] = username
                flash("Register successful and you have logged in.")
                return redirect(url_for('index'))

    return render_template('register.html', save_form=save_form)


@app.route('/welcome', methods=["GET"])
def welcome():
    return render_template('welcome.html', username=session.get('username', None))


@app.route('/no_access', methods=["GET"])
def no_access():
    return render_template('no_access.html')


@app.route('/', methods=["GET", "POST"])
@user
def index():
    global save_form
    people = []
    with connection.cursor() as cursor:
        sql = "SELECT * FROM peopledata ORDER BY name, city;"
        cursor.execute(sql)
        result = cursor.fetchall()
        for person in result:
            people.append(Person(person))
    if request.method == "POST":
        if request.form.get("reset_search", False) is not False:
            save_form = {
                'name': '',
                'phone_number': '',
                'city': '',
                'username': '',
            }
            return redirect(url_for('index'))

        people = []
        name = request.form.get("name", '')
        phone_number = request.form.get("phone_number", '')
        city = request.form.get("city", '')
        save_form['name'] = name
        save_form['phone_number'] = phone_number
        save_form['city'] = city
        name = '%' + name + '%'
        phone_number = '%' + phone_number + '%'
        city = '%' + city + '%'

        with connection.cursor() as cursor:
            sql = """SELECT * FROM peopledata 
                     WHERE name LIKE %s AND phone_number LIKE %s AND city LIKE %s
                     ORDER BY name, city;"""
            cursor.execute(sql, (name, phone_number, city))
            result = cursor.fetchall()
            for person in result:
                people.append(Person(person))

    return render_template('index.html', people=people, username=session.get('username'), save_form=save_form,
                           role=session['role'])


@app.route('/admin_index', methods=("GET", "POST"))
@admin
def admin_index():
    people = []
    with connection.cursor() as cursor:
        sql = "SELECT * FROM peopledata ORDER BY name, city;"
        cursor.execute(sql)
        result = cursor.fetchall()
        for person in result:
            people.append(Person(person))

    if request.method == "POST":
        delete = request.form.get("delete", False)
        id = int(request.form.get("edit", False))

        if delete is not False:
            with connection.cursor() as cursor:
                sql = "DELETE FROM peopledata WHERE id = %s;"
                cursor.execute(sql, delete)
                connection.commit()
                return(redirect(url_for('admin_index')))
        elif id is not False:
            return(redirect(url_for('edit', id=id)))

    return (render_template('admin_index.html', people=people))


@app.route('/add', methods=("GET", "POST"))
@admin
def add():
    if request.method == "POST":
        form_data = ['']
        for name in ["name", "phone_number", "city"]:
            form_data.append(request.form[name])
        form_data = Person(form_data)

        with connection.cursor() as cursor:
            sql = "INSERT INTO `peopledata` (`id`, `name`, `phone_number`, `city`) VALUES (NULL, %s, %s, %s);"
            cursor.execute(sql, (form_data.name, form_data.phone_number, form_data.city))
            connection.commit()

    return (render_template('add.html'))


@app.route('/edit/<int:id>', methods=("GET", "POST"))
@admin
def edit(id):
    with connection.cursor() as cursor:
        sql = "SELECT * FROM `peopledata` WHERE id = %s;"
        cursor.execute(sql, id)
        result = Person(cursor.fetchone())

    if request.method == "POST":
        form_data = ['']
        for name in ["name", "phone_number", "city"]:
            form_data.append(request.form[name])
        form_data = Person(form_data)

        with connection.cursor() as cursor:
            sql = "UPDATE peopledata SET name = %s, phone_number = %s, city = %s WHERE id = %s"
            cursor.execute(sql, (form_data.name, form_data.phone_number, form_data.city, id))
            connection.commit()

        return(redirect(url_for('edit', id=id)))

    return (render_template('edit.html', person=result))


@app.route('/users', methods=("GET", "POST"))
@admin
def users():
    users = []
    with connection.cursor() as cursor:
        sql = "SELECT username, role FROM users ORDER BY role, username;"
        cursor.execute(sql)
        result = cursor.fetchall()
        for user in result:
            users.append(User(user))

    if request.method == "POST":
        delete_user = request.form.get("delete", False)
        change_role = request.form.get("edit_role", "off")
        print(change_role)

        if delete_user is not False:
            with connection.cursor() as cursor:
                sql = "DELETE FROM users WHERE username = %s;"
                cursor.execute(sql, delete_user)
                connection.commit()
                return redirect(url_for("users"))
        elif change_role is not False:
            roles = {
                "on": "admin",
                "off": "user"
            }
            with connection.cursor() as cursor:
                sql = "UPDATE users SET role = %s WHERE username = %s"
                cursor.execute(sql, (roles[change_role], request.form["role_change_username"]))
                connection.commit()
                return redirect(url_for("users"))

    return render_template("users.html", users=users)


if __name__ == '__main__':
    app.run()

