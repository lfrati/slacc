import argparse
import json
import time
from http.client import HTTPConnection
from pathlib import Path


def post_req(obj, args):
    c = HTTPConnection(args.addr, args.port)
    c.connect()
    encoded = json.dumps(obj).encode("utf-8")
    c.request(
        "POST",
        "/",
        body=encoded,
        headers={"Content-type": "application/json", "Content-length": len(encoded)},
    )
    response_bytes = c.getresponse().read()
    response_string = response_bytes.decode("utf-8")
    return json.loads(response_string)


def get_req(path, args):
    c = HTTPConnection(args.addr, args.port)
    c.connect()
    c.request(
        "GET",
        path,
    )
    response_bytes = c.getresponse().read()
    response_string = response_bytes.decode("utf-8")
    return json.loads(response_string)


def rpad(s, N):
    spaces = " " * (N - len(s))
    return s + spaces


def lpad(s, N):
    spaces = " " * (N - len(s))
    return spaces + s


def status(msg):
    jobs = msg["result"]
    header = (
        f"{rpad('ID',6)} │ {rpad('CMD',20)} │ {rpad('TIME',20)} │ {rpad('STATE',10)}"
    )
    print()
    print(header)
    print("─" * 7 + "┼" + "─" * 22 + "┼" + "─" * 22 + "┼" + "─" * 11)
    for job in jobs:
        ID = job["id"]
        cmd = job["cmd"]
        cmd = (cmd[: 16 - 2] + "..") if len(cmd) > 16 else cmd
        state = job["state"]
        if state == "CANCELLED":
            time = "-"
        elif state == "QUEUED":
            time = job["creation"]
        else:
            time = job["elapsed"]
        print(f"{ID:<6} │ {cmd:<20} │ {time:<20} │ {state:<10}")
    print()


def make_req(action, body):
    return {"action": action, "body": body, "path": path}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interact with job scheduling.")
    parser.add_argument("--addr", default="localhost")
    parser.add_argument("--port", default=12345)
    parser.add_argument("--action", type=str)
    parser.add_argument("--body", default="")
    args = parser.parse_args()

    path = Path().resolve().as_posix()

    if args.action == "test":

        print("Testing errors")
        print(post_req({"body": "This is  a test"}, args))
        print(post_req({"action": "error", "body": "sleep 4"}, args))

        print("Sending jobs")
        msg = post_req(
            {"action": "add", "body": "ping -c 3 www.google.com", "path": path}, args
        )
        print(msg)
        msg = post_req(
            {"action": "add", "body": "ping -c 4 www.google.com", "path": path}, args
        )
        print(msg)
        msg = post_req(
            {"action": "add", "body": "ping -c 2 www.google.com", "path": path}, args
        )
        print(msg)
        to_kill = msg["result"]["id"]
        msg = post_req(
            {"action": "add", "body": "ping -c 7 www.google.com", "path": path}, args
        )
        print(msg)
        time.sleep(0.5)

        print("Checking status of jobs")
        msg = get_req("", args)
        status(msg)

        print(f"Cancelling scheduled job {to_kill}")
        print(post_req({"action": "cancel", "body": to_kill, "path": path}, args))

        print("Checking status of jobs")
        msg = get_req("", args)
        status(msg)

        # msg = get_req("", args)
        # status(msg)
        # print(post_req({"action": "cancel_all", "body": ""}, args))

        print("Killing current job")
        print(post_req({"action": "kill", "body": "", "path": ""}, args))

        print("Checking status of jobs")
        msg = get_req("", args)
        status(msg)

    if args.action == "add":
        assert args.body != ""
        msg = post_req({"action": args.action, "body": args.body, "path": path}, args)
        print(msg["result"])

    if args.action == "list":
        msg = get_req("", args)
        if len(msg["result"]) > 0:
            status(msg)
        else:
            print("No Jobs scheduled.")
