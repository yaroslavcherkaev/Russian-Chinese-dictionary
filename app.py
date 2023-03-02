from flask import Flask, render_template, request, make_response, jsonify
import requests
from bkrs import Bkrs

application = Flask(__name__)

@application.route("/")
def hello():
    return render_template('index.html')

@application.route("/getword", methods=['GET'], strict_slashes=False)
def getword():
    word = request.args.get("word")
    res = Bkrs(word)
    res = res.get_words()
    if res and res['type'] != 'error':
        response = jsonify(res)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    else:
        response = make_response("Record not found", 400)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

if __name__ == "__main__":
   application.run(host='0.0.0.0')
