import argparse
import json
import time
from pathlib import Path

from SNURM_utils import status, GET_req, POST_req


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
            {"action": args.action, "cmd": args.cmd, "path": path, "env": args.env},
            args.addr,
            args.port,
        )
        print(json.dumps(msg["result"]))

    elif args.action == "cancel":
        assert args.id != ""
        msg = POST_req({"action": args.action, "id": args.id}, args.addr, args.port)
        print(json.dumps(msg["result"]))

    elif args.action == "kill":
        msg = POST_req({"action": args.action}, args.addr, args.port)
        print(json.dumps(msg["result"]))

    elif args.action == "list":
        msg = GET_req("", args.addr, args.port)
        jobs = msg["result"]
        if len(jobs) > 0:
            status(jobs)
        else:
            print("No Jobs scheduled.")
