from __main__ import app, db, login_manager, Users, Profiles

from flask import render_template, request, redirect, url_for, flash, Response
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime

import json

from secrets import choice
import string


@login_manager.user_loader
def load_user(user_id):
    print("Loading user", user_id)
    return db.session.query(Users).filter(Users.id == user_id).scalar()


@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template("index.html", title="Главная", user=current_user)
    else:
        return render_template("index.html", title="Главная")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        # Проверка корректности введенных данных
        try:
            # hash = generate_password_hash(request.form['psw'])
            u = Users(email=request.form.get('email'), phone=request.form.get('phone'),
                      login=request.form.get('login'))
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
        except:
            db.session.rollback()
            print('Ошибка добавления в БД')

    return render_template("register.html", title="Регистрация")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        psw = request.form.get('psw')

        if db.session.query(db.exists().where(Users.login == login)).scalar():
            user = db.session.query(Users).filter(Users.login == login).scalar()

            if user.check_password(psw):
                print("Вход успешен, здравствуйте,", login+'!')
                flash("Вы успешно вошли", "success")
                login_user(user)
                return redirect(url_for('profile'))
            else:
                print("Wrong password")
                flash("Неверный пароль", "error")
        else:
            print("Wrong login")
            flash("Неверный логин", "error")

    return render_template("login.html", title="Авторизация")


@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    user_info = db.session.query(Profiles).filter(Profiles.user_id == current_user.id).scalar()
    return render_template("profile.html", title="Профиль", user=current_user, profile=user_info)


@app.route('/logout', methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/useradd', methods=["POST"])
def useradd():
    request_data = request.get_json()

    ncommits = 0
    nerrors = 0

    # For generate password
    char_classes = (string.ascii_lowercase,
                    string.ascii_uppercase,
                    string.digits)
    char = lambda: choice(choice(char_classes))

    print(request_data)
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

                    psw = ''.join([char() for _ in range(12)])

                    print("{} {} {} {} {} {} {} {}".format(fname, lname, patr, bd, email, phone, login, psw))
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
                        u.set_password(psw)

                        p = Profiles(lname=lname, fname=fname,
                                     patr=patr, birthday=bd,
                                     user_id=u.id)
                        try:
                            db.session.add(u)
                            db.session.flush()

                            db.session.add(p)
                            db.session.commit()

                            ncommits += 1
                            user_info = {'login': login, 'password': psw}
                            users_data.append(user_info)
                        except:
                            db.session.rollback()
                            print('Ошибка добавления в БД')
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