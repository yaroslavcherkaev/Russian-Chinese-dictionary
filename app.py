# -*- coding: utf-8 -*-
import requests
import bs4
from flask import Flask, render_template, request, make_response, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import datetime
from base64 import b64encode
from hashlib import sha256
from hmac import HMAC
from urllib.parse import urlparse, parse_qsl, urlencode
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

try:
    application = Flask(__name__)
    limiter = Limiter(
        get_remote_address,
        app=application,
        default_limits=["500 per day", "100 per hour"],
        storage_uri="memory://",
    )
except Exception as e:
    with open("textlog.txt", "a") as file:
        file.write('\nOn method get_word: '+ str(e))


application.config['MYSQL_HOST'] = ''
application.config['MYSQL_USER'] = ''
application.config['MYSQL_PASSWORD'] = ''
application.config['MYSQL_DB'] = ''
CORS(application)
mysql = MySQL(application)


def is_valid(query: dict, secret: str) -> bool:
    """

    Check VK Apps signature

    :param dict query: Словарь с параметрами запуска
    :param str secret: Секретный ключ приложения ("Защищённый ключ")
    :returns: Результат проверки подписи
    :rtype: bool

    """
    if not query.get("sign"):
        return False

    vk_subset = sorted(
        filter(
            lambda key: key.startswith("vk_"),
            query
        )
    )

    if not vk_subset:
        return False

    ordered = {k: query[k] for k in vk_subset}

    hash_code = b64encode(
        HMAC(
            secret.encode(),
            urlencode(ordered, doseq=True).encode(),
            sha256
        ).digest()
    ).decode("utf-8")

    if hash_code[-1] == "=":
        hash_code = hash_code[:-1]

    fixed_hash = hash_code.replace('+', '-').replace('/', '_')
    return query.get("sign") == fixed_hash


client_secret_my = ''

"""
language detection
Returns:
1: russian
2: chinese
3: pinyin (?) how to implement?
4: Something went wrong
"""


def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(response.text)
        return response.text
    except(requests.RequestException, ValueError):
        return None


def is_ru(word) -> bool:
    alphabet_ru = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя- !?,')
    for char in word:
        if char not in alphabet_ru:
            return False
    return True


def is_eng(word) -> bool:
    alphabet_eng = set('abcdefghijklmnopqrstuvwxyz ')
    for char in word:
        if char not in alphabet_eng:
            return False
        return True


def check_lang(word):
    len_word = len(word)
    len_valid = 100
    if len_word > len_valid:
        return 4
    if is_ru(word):
        return 1
    elif is_eng(word):
        return 3
    else:
        return 2

@application.errorhandler(429)
def ratelimit_handler(e):
    return make_response(
            jsonify(error=f"ratelimit exceeded {e.description}")
            , 429
    )

@application.route("/")
@limiter.limit("10/second", override_defaults=False)
def hello():
    return "Hello World!"


"""
GET запрос. получение слова из баз данных словаря. Определяет язык параметра, затем совершает поиск по бд, 
если нет результатов совершает поиск через LIKE и отправляет их вместо ответа. 
Если вообще ничего, то ответ что ничего нет.
"""


@application.route("/get_word", methods=['GET'], strict_slashes=False)
@limiter.limit("10/second", override_defaults=False)
def get_word():
    token = request.headers.get('Authorization')
    query_valid = dict(
        parse_qsl(
            token,
            keep_blank_values=True
        )
    )
    status = is_valid(query=query_valid, secret=client_secret_my)
    if status:
        query_params = dict(
            parse_qsl(
                urlparse(request.url).query,
                keep_blank_values=True
            )
        )
        word = query_params["word"].lower()
        check_type = check_lang(word)
        if check_type == 1:
            try:
                cursor = mysql.connection.cursor()
                cursor.execute('SET NAMES utf8mb4')
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute("SET character_set_connection=utf8mb4")
                cursor.execute(''' SELECT * FROM word_ru WHERE ru LIKE %s''', (word,))
                res = cursor.fetchall()
                mysql.connection.commit()
                cursor.close()
                if len(res) <= 0:
                    response = make_response("Bad Request: Record not found", 404)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
                else:
                    response = {
                        "type": "RU",
                        "user_word": str(res[0][1]),
                        "ch": str(res[0][2])
                    }
                    response = jsonify(response)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
            except Exception as e:
                with open("textlog.txt", "a") as file:
                    file.write('\nOn method get_word: '+ str(e))
                response = make_response("Bad Request", 400)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response
        elif check_type == 2:
            try:
                cursor = mysql.connection.cursor()
                cursor.execute('SET NAMES utf8mb4')
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute("SET character_set_connection=utf8mb4")
                cursor.execute(''' SELECT * FROM word_ch WHERE ch LIKE %s''', (word,))
                res = cursor.fetchall()
                mysql.connection.commit()
                cursor.close()
                if len(res) <= 0:
                    response = make_response("Bad Request: Record not found", 404)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
                else:
                    response = {
                        "type": "CH",
                        "user_word": str(res[0][1]),
                        "py": str(res[0][3]),
                        "ru": str(res[0][2])
                    }
                    response = jsonify(response)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
            except Exception as e:
                with open("textlog.txt", "a") as file:
                    file.write('\nOn method get_word: '+ str(e))
                response = make_response("Bad Request", 400)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response
        elif check_type == 3:
            try:
                cursor = mysql.connection.cursor()
                cursor.execute('SET NAMES utf8mb4')
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute("SET character_set_connection=utf8mb4")
                cursor.execute(''' SELECT * FROM word_ch WHERE py LIKE %s''', (str(word),))
                res_only = cursor.fetchall()
                cursor.execute(''' SELECT * FROM word_ch WHERE py LIKE %s''', (str(word + '_ %'), ))
                res_more = cursor.fetchall()

                mysql.connection.commit()
                cursor.close()
                if (len(res_only) == 0) and (len(res_more) == 0):
                    response = make_response("Bad Request: Record not found", 404)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
                else:
                    if len(res_only) != 0 and len(res_more) != 0:
                        res = res_only + res_more
                    elif len(res_only) == 0:
                        res = res_more
                    else:
                        res = res_only
                    response = {
                        "type": "PY",
                        "list": [],
                    }
                    for row in res:
                        response["list"].append(
                            {
                            "type": "PY",
                            "ch": str(row[1]),
                            "py": str(row[2]),
                            "ru": str(row[3])
                            }
                        )
                    response = jsonify(response)
                    response.headers.add("Access-Control-Allow-Origin", "*")
                    return response
            except Exception as e:
                with open("textlog.txt", "a") as file:
                    file.write('\nOn method get_word: '+ str(e))
                response = make_response("Bad Request", 400)
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response
        else:
            with open("textlog.txt", "a") as file:
                file.write('\nOn method get_word: '+ str(e))
            response = make_response("Unrecognised language", 400)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
    else:
        with open("textlog.txt", "a") as file:
            file.write('\nOn method get_word: '+ str(e))
        response = make_response("Unauthorized ", 401)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


"""
GET запрос. получение избранных слов из баз данных. 
"""


@application.route("/get_fav_words", methods=['GET'], strict_slashes=False)
@limiter.limit("10/second", override_defaults=False)
def get_fav_words():
    token = request.headers.get('Authorization')
    query_valid = dict(
        parse_qsl(
            token,
            keep_blank_values=True
        )
    )
    status = is_valid(query=query_valid, secret=client_secret_my)
    if status:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(''' SELECT word FROM fav_words WHERE id = %s ORDER BY date DESC''',
                           (int(query_valid["vk_user_id"]),))
            res = cursor.fetchall()
            mysql.connection.commit()
            cursor.close()
            response = []
            for row in res:
                response.append(row[0])
            response = jsonify(response)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
        except Exception as e:
            with open("textlog.txt", "a") as file:
                file.write('\nOn method get_fav_word: '+ str(e))
            response = make_response("Bad Request: Record not found", 404)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
    else:
        response = make_response("Unauthorized ", 401)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


"""
POST запрос. удаление избранного слова из баз данных. 
"""


@application.route("/del_fav_word", methods=['POST'], strict_slashes=False)
@limiter.limit("10/second", override_defaults=False)
def del_word():
    token = request.headers.get('Authorization')
    query_valid = dict(
        parse_qsl(
            token,
            keep_blank_values=True
        )
    )
    status = is_valid(query=query_valid, secret=client_secret_my)
    if status:
        try:
            data = request.json
            word = data.get("word")
            id = query_valid["vk_user_id"]
            cursor = mysql.connection.cursor()
            cursor.execute('''DELETE FROM fav_words WHERE id = %s AND word = %s''', (int(id), word))
            mysql.connection.commit()
            cursor.close()
            response = make_response("Word deleted from fav", 201)
            return response
        except Exception as e:
            with open("textlog.txt", "a") as file:
                file.write('\nOn method del_fav_word: '+ str(e) + ' with data: ' + str(word))
            response = make_response("Bad Request", 400)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
    else:
        response = make_response("Unauthorized ", 401)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


"""
POST запрос. добавление избранного слова в базы данных. 
"""


@application.route("/add_fav_word", methods=['POST'], strict_slashes=False)
@limiter.limit("10/second", override_defaults=False)
def add_fav_word():
    token = request.headers.get('Authorization')
    query_valid = dict(
        parse_qsl(
            token,
            keep_blank_values=True
        )
    )
    status = is_valid(query=query_valid, secret=client_secret_my)
    if status:
        try:
            data = request.json
            word = data.get("word")
            now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            now_format = now.strftime('%Y-%m-%d %H:%M:%S')
            id = query_valid["vk_user_id"]
            try:
                cursor = mysql.connection.cursor()
                cursor.execute('''SELECT ru FROM word_ru WHERE ru = %s UNION SELECT ch FROM word_ch WHERE ch = %s''', (str(word), str(word) ))
                is_in_dict = cursor.fetchall()
                mysql.connection.commit()
                cursor.close()
            except Exception as e:
                with open("textlog.txt", "a") as file:
                    file.write('\nOn method add_fav_word: '+ str(e) + ' with data: ' + str(word))
                response = make_response("Bad Request", 400)
                response.headers.add("Access-Control-Allow-Origin", "*")
            if len(is_in_dict) !=0:
                cursor = mysql.connection.cursor()
                cursor.execute('''INSERT INTO fav_words VALUES(%s,%s,%s)''', (int(id), str(word), now_format))
                response = make_response("Word added to fav", 201)
                mysql.connection.commit()
                cursor.close()
                return response
            else:
                response = make_response("Bad Request", 400)
                response.headers.add("Access-Control-Allow-Origin", "*")
                mysql.connection.commit()
                cursor.close()
                return response
        except Exception as e:
            with open("textlog.txt", "a") as file:
                file.write('\nOn method add_fav_word: '+ str(e) + ' with data: ' + str(word))
            response = make_response("Bad Request", 400)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
    else:
        response = make_response("Unauthorized ", 401)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


        
        
@application.route("/send_feedback", methods=['POST'], strict_slashes=False)
@limiter.limit("10/second", override_defaults=False)
def send_feedback():
    token = request.headers.get('Authorization')
    query_valid = dict(
        parse_qsl(
            token,
            keep_blank_values=True
        )
    )
    status = is_valid(query=query_valid, secret=client_secret_my)
    if status:
        try:
            data = request.json
            id = query_valid["vk_user_id"]
            word = data.get('word')
            message = data.get('message')
            with open("feedback.txt", "a") as file:
                file.write('\nPerson: '+ str(id) + '\nOn word: ' + str(word) + '\nMessage: ' + str(message) + '\n\n')
            response = make_response("Feedback was sent", 201)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
        except Exception as e:
            with open("textlog.txt", "a") as file:
                file.write('\nOn method add_fav_word: '+ str(e) + ' with data: ' + str(word))
            response = make_response("Bad Request", 400)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response
    else:
        response = make_response("Unauthorized ", 401)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
        

    



if __name__ == "__main__":
   application.run(host='0.0.0.0')
