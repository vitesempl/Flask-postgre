from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import logging
from sqlalchemy import exc

from sqlalchemy_utils import database_exists, create_database

from werkzeug.security import generate_password_hash, check_password_hash
from secrets import choice
import string

import json

from datetime import datetime

database_url = "postgresql+psycopg2://postgres:111097@localhost/users"
if not database_exists(database_url):
    create_database(database_url)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'e56b0e9364067f9bf44a56e17c3c5ac3a598bf68'

db = SQLAlchemy(app)

login_manager = LoginManager(app)

handler = logging.FileHandler("test.log")  # Create the file logger
app.logger.addHandler(handler)             # Add it to the built-in logger
app.logger.setLevel(logging.DEBUG)         # Set the log level to debug


@login_manager.user_loader
def load_user(user_id):
    print("Loading user", user_id)
    return db.session.query(Users).filter(Users.id == user_id).scalar()


class Users(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(50), unique=True)
    phone = db.Column(db.BigInteger, unique=True)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<users {self.id}>"

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_password(self):
        char_classes = (string.ascii_lowercase,
                        string.ascii_uppercase,
                        string.digits)
        char = lambda: choice(choice(char_classes))
        psw = ''.join([char() for _ in range(12)])

        self.password_hash = generate_password_hash(psw)

        return psw

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profiles(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(50), nullable=True)
    lname = db.Column(db.String(50), nullable=True)
    patr = db.Column(db.String(50), nullable=True)
    birthday = db.Column(db.DateTime, default=None, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f"<profiles {self.id}>"


class ResCodes(db.Model):
    __tablename__ = 'codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=True)
    method = db.Column(db.String(10), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<codes {self.id}>"

    def db_commit(self):
        try:
            db.session.add(self)
            db.session.commit()
        except:
            db.session.rollback()


class BadUsers(db.Model):
    __tablename__ = 'bad_users'

    id = db.Column(db.Integer, primary_key=True)
    code_id = db.Column(db.Integer, db.ForeignKey('codes.id'))
    object_id = db.Column(db.Integer, nullable=True)
    login = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<bad_users {self.id}>"

    def db_commit(self):
        try:
            db.session.add(self)
            db.session.commit()
        except:
            db.session.rollback()


@app.route('/', methods=["GET"])
def index():
    if current_user.is_authenticated:
        return render_template("index.html", title="Main page", user=current_user)
    else:
        return render_template("index.html", title="Main page")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        # Проверка корректности введенных данных
        email = request.form.get('email')
        phone = request.form.get('phone')
        login = request.form.get('login')

        u = Users(email=email, phone=phone,
                  login=login)
        psw = request.form.get('psw')
        u.hash_password(psw)

        # print(email, phone, login, psw)
        try:
            db.session.add(u)
            db.session.flush()

            bd = request.form.get('birthday')
            if bd != '':
                bd = datetime.strptime(bd, "%d.%m.%Y").strftime("%Y-%m-%d %H:%M")
            else:
                bd = None

            p = Profiles(lname=request.form.get('lname'), fname=request.form.get('fname'),
                         patr=request.form.get('patr'), birthday=bd,
                         user_id=u.id)
            db.session.add(p)
            db.session.commit()

            return redirect(url_for('login', login=login))
        except exc.IntegrityError as e:
            db.session.rollback()
            flash('Error adding to database! ' + e)

    return render_template("register.html", title="Sign in")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        psw = request.form.get('psw')

        if db.session.query(db.exists().where(Users.login == login)).scalar():
            user = db.session.query(Users).filter(Users.login == login).scalar()

            if user.check_password(psw):
                # flash("Вы успешно вошли", "success")
                login_user(user)
                return redirect(url_for('profile'))
            else:
                # print("Wrong password")
                flash("Неверный пароль", "error")
        else:
            # print("Wrong login")
            flash("Неверный логин", "error")

    return render_template("login.html", title="Log in")


@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    user_info = db.session.query(Profiles).filter(Profiles.user_id == current_user.id).scalar()
    return render_template("profile.html", title="Profile", user=current_user, profile=user_info)


@app.route('/logout', methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/useradd', methods=["POST"])
def useradd():
    request_data = request.get_json()

    if isinstance(request_data, dict):
        request_data = [request_data]

    if request_data:
        users_data = []
        bad_logins = []

        num = 0
        for person in request_data:
            num += 1
            if not('login' in person):
                # print('Not enough information, login missing!')
                bad_logins.append([num, None, 'Not enough information, login missing!'])
                continue
            else:
                login = person['login']
                if ('first_name' in person and 'last_name' in person and
                    'patronymic' in person and ('email' in person or 'phone' in person)):
                    # required attributes
                    fname = person['first_name']
                    lname = person['last_name']
                    patr = person['patronymic']

                    if 'email' in person:
                        email = person['email']
                    else:
                        email = None

                    if 'phone' in person:
                        phone = person['phone']
                    else:
                        phone = None

                    # optional attributes
                    if 'birthday' in person:
                        birthday = person['birthday']
                        bd = datetime.strptime(birthday, "%d/%m/%Y").strftime("%Y-%m-%d %H:%M")
                    else:
                        bd = None

                    # Проверка корректности введенных данных
                    if db.session.query(db.exists().where(Users.login == login)).scalar():
                        bad_logins.append([num, login, 'Error! Login is already in the database.'])
                        # print('Логин уже существует')
                        continue
                    elif db.session.query(db.exists().where(Users.email == email)).scalar() and email is not None:
                        bad_logins.append([num, login, 'Error! E-mail is already in the database.'])
                        # print('e-mail уже существует')
                        continue
                    elif db.session.query(db.exists().where(Users.phone == phone)).scalar() and phone is not None:
                        bad_logins.append([num, login, 'Error! Phone is already in the database.'])
                        # print('Телефон уже существует')
                        continue
                    else:
                        u = Users(email=email, phone=phone, login=login)
                        psw = u.set_password()
                        # print("{} {} {} {} {} {} {} {}".format(fname, lname, patr, bd, email, phone, login, psw))
                        try:
                            db.session.add(u)
                            db.session.flush()

                            p = Profiles(lname=lname, fname=fname,
                                         patr=patr, birthday=bd,
                                         user_id=u.id)
                            db.session.add(p)
                            db.session.commit()

                            user_info = {'login': login, 'password': psw}
                            users_data.append(user_info)
                        except exc.IntegrityError as e:
                            db.session.rollback()
                            bad_logins.append([num, login, 'Error adding to database! '+e])
                            continue
                else:
                    bad_logins.append([num, login, 'Error! Not enough information, '
                                                   'You should fill in the fields name, email or phone!'])
                    # print('Not enough information! User with login', login, 'wasn\'t created')
                    continue

        if len(users_data) == 0:
            res = "Bad request! Users haven\'t been created."
            code = ResCodes(code=400, method="POST", description=res)
            code.db_commit()

            for u in bad_logins:
                bu = BadUsers(code_id=code.id, object_id=u[0], login=u[1], description=u[2])
                bu.db_commit()

            return Response(res, 400, mimetype='text/plain')
        else:
            if len(users_data) == len(request_data):
                res = "All users have been created."

                code = ResCodes(code=200, method="POST", description=res)
                code.db_commit()
            else:
                res = "Not all users have been created (created by {} of {} users)".format(str(len(users_data)),
                                                                                           str(len(request_data)))

                code = ResCodes(code=200, method="POST", description=res)
                code.db_commit()

                for u in bad_logins:
                    bu = BadUsers(code_id=code.id, object_id=u[0], login=u[1], description=u[2])
                    bu.db_commit()

            users_json = json.dumps(users_data)
            return Response(users_json, 200, mimetype='application/json')
    else:
        res = "Bad request! JSON file is empty."
        code = ResCodes(code=400, method="POST", description=res)
        code.db_commit()

        return Response(res, 400, mimetype='text/plain')


@app.errorhandler(404)
def pageNot(error):
    return redirect(url_for('index'))


if __name__ == '__main__':
    db.drop_all()
    db.create_all()
    app.run(debug=True)

