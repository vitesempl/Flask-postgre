from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from werkzeug.security import generate_password_hash, check_password_hash
from secrets import choice
import string

import json

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:111097@localhost/users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'

db = SQLAlchemy(app)

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    print("Loading user", user_id)
    return db.session.query(Users).filter(Users.id == user_id).scalar()


class Users(db.Model, UserMixin):
    #__tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(50), unique=True)
    phone = db.Column(db.BigInteger, unique=True)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<users {self.id}>"

    def hash_password(self, psw):
        self.password_hash = generate_password_hash(psw)

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
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(50), nullable=True)
    lname = db.Column(db.String(50), nullable=True)
    patr = db.Column(db.String(50), nullable=True)
    birthday = db.Column(db.DateTime, default=None, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f"<profiles {self.id}>"


@app.route('/')
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

        print(email, phone, login, psw)
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
        except:
            db.session.rollback()
            print('Ошибка добавления в БД')

            flash("Bad user information! Try again.", "error")

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
                print("Wrong password")
                flash("Неверный пароль", "error")
        else:
            print("Wrong login")
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

    ncommits = 0
    nerrors = 0

    if request_data:
        users_data = []
        bad_logins = []
        for person in request_data:
            if not('login' in person):
                print('Not enough information, login missing!')
                nerrors += 1
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
                        bad_logins.append(login)
                        print('Логин уже существует')
                        continue
                    elif db.session.query(db.exists().where(Users.email == email)).scalar() and email is not None:
                        bad_logins.append(login)
                        print('e-mail уже существует')
                        continue
                    elif db.session.query(db.exists().where(Users.phone == phone)).scalar() and phone is not None:
                        bad_logins.append(login)
                        print('Телефон уже существует')
                        continue
                    else:
                        u = Users(email=email, phone=phone,
                                  login=login)
                        psw = u.set_password()
                        print("{} {} {} {} {} {} {} {}".format(fname, lname, patr, bd, email, phone, login, psw))
                        try:
                            db.session.add(u)
                            db.session.flush()

                            p = Profiles(lname=lname, fname=fname,
                                         patr=patr, birthday=bd,
                                         user_id=u.id)
                            db.session.add(p)
                            db.session.commit()

                            ncommits += 1
                            user_info = {'login': login, 'password': psw}
                            users_data.append(user_info)
                        except:
                            db.session.rollback()
                            print('Error database add')
                            nerrors += 1
                            continue
                else:
                    bad_logins.append(login)
                    print('Not enough information! User with login', login, 'wasn\'t created')
                    continue

        if len(users_data) == 0:
            return Response('Bad request! Users haven\'t been created.', 400, mimetype='text/plain')
        else:
            users_json = json.dumps(users_data)
            return Response(users_json, 200, mimetype='application/json')
        # return "Successfull commits: " + str(ncommits) + "\nError objects: " + str(nerrors)


@app.errorhandler(404)
def pageNot(error):
    return redirect(url_for('index'))


if __name__ == '__main__':
    db.drop_all()
    db.create_all()
    app.run(debug=True)

