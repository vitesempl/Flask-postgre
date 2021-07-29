import requests
import json
from os import listdir


def post_json(file):
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = ""

    response = requests.post('http://127.0.0.1:5000/useradd', json=data)
    print("Code:", response.status_code)
    print("Output:", response.headers.get('Content-Type'))

    if response.status_code == 200:
        json_response = json.loads(response.content)
        for user in json_response:
            print(user)
    elif response.status_code == 400:
        print(response.content.decode("utf-8"))


path = "json_examples/"
for json_file in listdir(path):
    post_json(path+json_file)

#post_json(path+"error_example_11.json")