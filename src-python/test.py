import sys
import json
import time

def main():
    received_data = sys.stdin.readline().strip()
    received_data = json.loads(received_data)

    with open('process.log', 'a') as f:
        f.write(f"received_data: {received_data}\n")

    if received_data:
        response_data = {
            "status": "ok",
            "id": received_data["id"],
            "data": received_data["data"],
        }
        response = json.dumps(response_data)
        time.sleep(2)
        print(response, flush=True)


    # with open('process.log', 'a') as f:
    #     f.write(f"Received data: {received_data}\n")
    #     f.write(f"Response: {response}\n")

    # # 標準出力に結果を出力
    # for i in range(10):
    #     print(str(i), flush=True)
    #     time.sleep(1)

if __name__ == "__main__":
    try:
        print(json.dumps({"init_key_from_py": "Initialization from Python."}), flush=True)
        while True:
            main()
    except Exception:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)