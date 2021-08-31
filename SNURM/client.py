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
    parser.add_argument("action")
    parser.add_argument("--cmd", default="")
    parser.add_argument("--id", default="")
    parser.add_argument("--env", default="")
    args = parser.parse_args()

    path = Path().resolve().as_posix()

    if args.action == "add":
        assert args.cmd != ""
        msg = POST_req(
            {"action": args.action, "cmd": args.cmd, "path": path, "env": args.env}
        )
        print(json.dumps(msg["result"]))

    elif args.action == "cancel":
        assert args.id != ""
        msg = POST_req({"action": args.action, "id": args.id})
        print(json.dumps(msg["result"]))

    elif args.action == "kill":
        msg = POST_req({"action": args.action})
        print(json.dumps(msg["result"]))

    elif args.action == "list":
        msg = GET_req("")
        jobs = msg["result"]
        if len(jobs) > 0:
            status(jobs)
        else:
            print("No Jobs scheduled.")
