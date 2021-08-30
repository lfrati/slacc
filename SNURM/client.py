import argparse
import json
import time
from http.client import HTTPConnection
from pathlib import Path
from utils import status


def POST_req(obj):
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


def GET_req(path):
    c = HTTPConnection(args.addr, args.port)
    c.connect()
    c.request(
        "GET",
        path,
    )
    response_bytes = c.getresponse().read()
    response_string = response_bytes.decode("utf-8")
    return json.loads(response_string)


if __name__ == "__main__":
    global args

    parser = argparse.ArgumentParser(description="Interact with job scheduling.")
    parser.add_argument("--addr", default="localhost")
    parser.add_argument("--port", default=12345)
    parser.add_argument("--action", required=True)
    parser.add_argument("--body", default="")
    args = parser.parse_args()

    path = Path().resolve().as_posix()

    if args.action == "test":

        print("Testing errors")
        print(POST_req({"body": "This is  a test"}))
        print(POST_req({"action": "error", "body": "sleep 4"}))

        print("Sending jobs")
        msg = POST_req(
            {"action": "add", "body": "ping -c 3 www.google.com", "path": path}
        )
        print(msg)
        msg = POST_req(
            {"action": "add", "body": "ping -c 4 www.google.com", "path": path}
        )
        print(msg)
        msg = POST_req(
            {"action": "add", "body": "ping -c 2 www.google.com", "path": path}
        )
        print(msg)
        to_kill = msg["result"]["id"]
        msg = POST_req(
            {"action": "add", "body": "ping -c 7 www.google.com", "path": path}
        )
        print(msg)
        time.sleep(0.5)

        print("Checking status of jobs")
        msg = GET_req("")
        jobs = msg["result"]
        status(jobs)

        print(f"Cancelling scheduled job {to_kill}")
        print(POST_req({"action": "cancel", "body": to_kill, "path": path}))

        print("Checking status of jobs")
        msg = GET_req("")
        jobs = msg["result"]
        status(jobs)

        print("Killing current job")
        print(POST_req({"action": "kill", "body": "", "path": ""}))

        print("Checking status of jobs")
        msg = GET_req("")
        jobs = msg["result"]
        status(jobs)

    if args.action == "add":
        assert args.body != ""
        msg = POST_req({"action": args.action, "body": args.body, "path": path})
        print(msg["result"])

    if args.action == "list":
        msg = GET_req("")
        if len(msg["result"]) > 0:
            status(msg)
        else:
            print("No Jobs scheduled.")
