from flask import Flask, render_template, request, redirect, url_for, g, session, current_app, flash
import functools
import pymysql

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
            return redirect(url_for('login'))
        with connection.cursor() as cursor:
            sql = "SELECT role FROM users WHERE username = %s;"
            cursor.execute(sql, username)
            role = cursor.fetchone()[0]
        if role == 'user' or role == 'admin':
            return view(**kwargs)

        return redirect(url_for('login'))

    return wrapped_view


def admin(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        username = session.get('username')
        if username is None:
            return redirect(url_for('login'))
        with connection.cursor() as cursor:
            sql = "SELECT role FROM users WHERE username = %s;"
            cursor.execute(sql, session['username'])
            role = cursor.fetchone()[0]
        if role == 'admin':
            return view(**kwargs)

        return redirect(url_for('login'))

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


@app.route('/login', methods=("GET", "POST"))
def login():
    if request.method == "POST":
        with connection.cursor() as cursor:
            sql = "SELECT password FROM users WHERE username = %s;"
            username = request.form['username'].strip()
            cursor.execute(sql, username)
            user_password = cursor.fetchone()
            if user_password is None:
                return redirect(url_for('index'))
            if user_password[0] == request.form['password']:
                session.clear()
                session['username'] = username
                return redirect(url_for('index'))

    return render_template("login.html")


@app.route('/logout', methods=("GET", "POST"))
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/', methods=["GET"])
@user
def index():
    people = []
    with connection.cursor() as cursor:
        sql = "SELECT * FROM peopledata ORDER BY id DESC;"
        cursor.execute(sql)
        result = cursor.fetchall()
        for person in result:
            people.append(Person(person))

    return render_template('index.html', people=people, username=session.get('username'))


@app.route('/admin_index', methods=("GET", "POST"))
@admin
def admin_index():
    people = []
    with connection.cursor() as cursor:
        sql = "SELECT * FROM peopledata ORDER BY id DESC;"
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

if __name__ == '__main__':
    app.run()
