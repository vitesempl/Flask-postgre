from flask import Flask, render_template, request, redirect, url_for, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from sqlalchemy import exc
from sqlalchemy_utils import database_exists, create_database

from werkzeug.security import generate_password_hash, check_password_hash
from secrets import choice
import string

import json

import pandas as pd

from datetime import datetime
from dateutil import parser

import sys

database_url = "postgresql+psycopg2://postgres:111097@localhost/users"
if not database_exists(database_url):
    create_database(database_url)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'e56b0e9364067f9bf44a56e17c3c5ac3a598bf68'

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


db = SQLAlchemy(app)

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    print("Loading user id:", user_id)
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
    error = None
    if request.method == 'POST':
        # Проверка корректности введенных данных
        email = request.form.get('email')
        phone = request.form.get('phone')
        login = request.form.get('login')

        birthday = request.form.get('birthday')
        if birthday:
            bd = parser.parse(birthday).strftime("%Y-%m-%d %H:%M")
        else:
            bd = None

        # Проверка корректности введенных данных
        if db.session.query(db.exists().where(Users.login == login)).scalar():
            error = 'Error! Login is already in the database.'
        elif db.session.query(db.exists().where(Users.email == email)).scalar() and email is not None:
            error = 'Error! E-mail is already in the database.'
        elif db.session.query(db.exists().where(Users.phone == phone)).scalar() and phone is not None:
            error = 'Error! Phone is already in the database.'
        else:
            u = Users(email=email, phone=phone,
                      login=login)
            psw = request.form.get('psw')
            u.hash_password(psw)

            try:
                db.session.add(u)
                db.session.flush()

                p = Profiles(lname=request.form.get('lname'), fname=request.form.get('fname'),
                             patr=request.form.get('patr'), birthday=bd,
                             user_id=u.id)
                db.session.add(p)
                db.session.commit()

                login_user(u)

                return redirect(url_for('profile'))
            except exc.DataError as e:
                db.session.rollback()
                error = 'Database DataError! ' + e.args[0]
            except:
                db.session.rollback()
                error = 'Database unexpected error!'

    return render_template("register.html", title="Sign in", error=error)


@app.route('/login', methods=["GET", "POST"])
def login():
    error = None

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
                error = "Неверный пароль"
        else:
            # print("Wrong login")
            error = "Неверный логин"

    return render_template("login.html", title="Log in", error=error)


@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    user_info = db.session.query(Profiles).filter(Profiles.user_id == current_user.id).scalar()

    codes = db.session.query(ResCodes).all()
    bu = db.session.query(BadUsers).all()

    return render_template("profile.html", title="Profile",
                           user=current_user, profile=user_info, codes=codes, bad_users=bu)


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
            elif len(person['login']) == 0:
                bad_logins.append([num, None, 'Not enough information, login is empty!'])
                continue
            else:
                login = person['login']
                if ('first_name' in person and 'last_name' in person and
                    'patronymic' in person and ('email' in person or 'phone' in person)):
                    # required attributes
                    fname = person['first_name']
                    lname = person['last_name']
                    patr = person['patronymic']
                    if len(fname) == 0 and len(lname) == 0 and len(patr) == 0:
                        bad_logins.append([num, login, 'Not enough information, full name is missing!'])
                        continue

                    if 'email' in person:
                        email = person['email']
                        if len(email) == 0:
                            email = None
                    else:
                        email = None

                    if 'phone' in person:
                        phone = person['phone']
                        try:
                            phone = int(phone)
                        except ValueError as e:
                            bad_logins.append([num, login, 'Error! Phone is not integer!'])
                            continue
                    else:
                        phone = None

                    if email is None and phone is None:
                        bad_logins.append([num, login, 'Not enough information, email and phone missing!'])
                        continue

                    # optional attributes
                    if 'birthday' in person:
                        birthday = person['birthday']
                        if len(birthday) > 0:
                            try:
                                bd = parser.parse(birthday).strftime("%Y-%m-%d %H:%M")
                            except:
                                print("Data parse error!")
                                bd = None
                        else:
                            bd = None
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
                        except exc.DataError as e:
                            db.session.rollback()
                            bad_logins.append([num, login, 'Database DataError! '+e.args[0]])
                            continue
                        except:
                            db.session.rollback()
                            bad_logins.append([num, login, 'Database unexpected error!'])
                            continue
                else:
                    bad_logins.append([num, login, 'Error! Not enough information, '
                                                   'login, name, email or phone are missing!'])
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
                res = "All users have been created ({} of {} users)".format(str(len(users_data)),
                                                                            str(len(request_data)))

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
        res = "Bad request! JSON file is empty or broken."
        code = ResCodes(code=400, method="POST", description=res)
        code.db_commit()

        return Response(res, 400, mimetype='text/plain')


def to_dict(row):
    if row is None:
        return None

    rtn_dict = dict()
    keys = row.__table__.columns.keys()
    for key in keys:
        rtn_dict[key] = getattr(row, key)
    return rtn_dict


def exportdata():
    data1, data2 = ResCodes.query.all(), BadUsers.query.all()
    codes_list = [to_dict(item) for item in data1]
    bad_users_list = [to_dict(item) for item in data2]
    df1 = pd.DataFrame(codes_list)
    df2 = pd.DataFrame(bad_users_list)

    return df1, df2


@app.route('/useradd/export/excel', methods=['GET'])
@login_required
def exportexcel():
    df1, df2 = exportdata()

    filename = app.config['UPLOAD_FOLDER'] + "stats_useradd_rescodes.xlsx"

    writer = pd.ExcelWriter(filename)
    df1.to_excel(writer, sheet_name='Response status codes')
    df2.to_excel(writer, sheet_name='Bad request users')
    writer.save()

    return send_file(filename)


@app.route('/useradd/export/txt', methods=['GET'])
@login_required
def exporttxt():
    df1, df2 = exportdata()

    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 200)

    filename = app.config['UPLOAD_FOLDER'] + "stats_useradd_rescodes.txt"

    with open(filename, 'w') as f:
        f.write(df1.__repr__())
        f.write('\n\n')
        f.write(df2.__repr__())

    return send_file(filename)


@app.errorhandler(404)
def pageNot(error):
    return redirect(url_for('index'))


if __name__ == '__main__':
    db.drop_all()
    db.create_all()
    app.run(debug=True)

