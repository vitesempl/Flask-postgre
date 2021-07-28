# Flask-postgre

Технологии
---------

* Python 3.9
* PostgreSQL 13
* flask, flask_sqlalchemy, flask_login
* sqlalchemy, sqlalchemy_utils
* pandas

Cтруктура приложения
---------

* app.py - основное приложение
* json-request.py - Тестирование POST-запроса к /useradd файлами JSON
* /json_examples - Файлы JSON для тестирования регистрации пользователей
* /templates - HTML файлы
* /static/css - CSS файлы
* /uploads - Экспортируемые файлы (XLSX, TXT)

Общая структура сервиса
---------

* Для всех пользователей: 
    * */* - Главная страница
    * */login* - Модуль авторизации
    * */logout* - Выход пользователем из системы
    * */register* – Модуль регистрации
    * */useradd [POST-request only]*  - Регистрация пользователей файлом JSON
  
* Для авторизованных пользователей
    * */profile* - Информация о пользователе и вывод статистики по /useradd
    * */useradd/export/xlsx*  - Экспорт статистики по /useradd в XLSX-файл
    * */useradd/export/txt*  - Экспорт статистики по /useradd в TXT-файл
    
Формат входных данных JSON
---------
```
{
    "first_name": "fname",          // required
    "last_name": "lname",           // required
    "patronymic": "pname",          // required
    "birthday": "DD/MM/YYYY",       // not required
    "email": "email@gmail.com",     // required (and/or phone)
    "phone": "9123456789",          // required (and/or email)
    "login": "login"                // required
}
```
или
```
[
    {
        "first_name": "fname",          // required
        "last_name": "lname",           // required
        "patronymic": "pname",          // required
        "birthday": "DD/MM/YYYY",       // not required
        "email": "email1@gmail.com",    // required (and/or phone)
        "phone": "9123456789",          // required (and/or email)
        "login": "login1"               // required
    },
    {
        "first_name": "fname",          // required
        "last_name": "lname",           // required
        "patronymic": "pname",          // required
        "birthday": "DD/MM/YYYY",       // not required
        "email": "email2@gmail.com",    // required (and/or phone)
        "phone": "9987654321",          // required (and/or email)
        "login": "login2"               // required
    }
]
```

Структура базы данных
---------
### Пользователи
* users - Таблица пользователей сервиса
    * *id* - ID пользователя (PRIMARY_KEY)
    * *login* - Логин пользователя
    * *password_hash* - Пароль пользователя (SHA256)
    * *email* – E-mail пользователя
    * *phone*  - Телефон
    * *reg_date* - Дата регистрации
    

* profiles - Таблица профилей каждого пользователя
    * *id* - ID профиля (PRIMARY_KEY)
    * *fname* - Имя пользователя
    * *lname* - Фамилия пользователя
    * *patr* – Отчество пользователя
    * *birthday*  - Дата рождения
    * *user_id* - ID пользователя (FOREIGN_KEY <-> users.id)
    
### Статистика /useradd
* codes - Таблица ответов сервиса /useradd
    * *id* - ID ответа (PRIMARY_KEY)
    * *code* - Код ответа сервера
    * *method* - Метод HTTP запроса
    * *date* – Дата выполнения запроса
    * *description* - Описание ответа сервера


* bad_users - Таблица пользователей, которые не были добавлены по запросу в /useradd
    * *id* - ID профиля (PRIMARY_KEY)
    * *code_id* - ID ответа сервиса (FOREIGN_KEY <-> codes.id)
    * *object_id* - Номер объекта в JSON
    * *login* – Логин пользователя (если имелся)
    * *description* - Описание ошибки
