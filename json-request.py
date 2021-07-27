import requests
import json


def post_json(file):
    path = "json_examples/" + file
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    response = requests.post('http://127.0.0.1:5000/useradd', json=data)
    print("Code:", response.status_code)

    if response.status_code == 200:
        json_response = json.loads(response.content)
        print("Output:", response.headers.get('Content-Type'))
        for user in json_response:
            print(user)
    elif response.status_code == 400:
        print(response.content.decode("utf-8"))


post_json('example_one.json')
post_json('example_array_one.json')
post_json('example_array_many.json')