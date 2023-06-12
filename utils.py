import json

def save_json(path, key, value):
    with open(path, "r") as fp:
        json_data = json.load(fp)
    json_data[key] = value
    with open(path, "w") as fp:
        json.dump(json_data, fp, indent=4)