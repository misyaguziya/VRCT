import json
import datetime

def save_json(path, key, value):
    with open(path, "r") as fp:
        json_data = json.load(fp)
    json_data[key] = value
    with open(path, "w") as fp:
        json.dump(json_data, fp, indent=4)

def print_textbox(textbox, message):
    now = datetime.datetime.now()
    now = now.strftime('%H:%M:%S')
    textbox.configure(state='normal')
    textbox.insert("end", f"[{now}]{message}\n")
    textbox.configure(state='disabled')
    textbox.see("end")