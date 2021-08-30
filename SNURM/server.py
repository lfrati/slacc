import json
import subprocess as sub
from datetime import datetime, timedelta
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer, HTTPStatus
from queue import Queue
from threading import Thread, Lock
from time import time
import os

queue = Queue()
running = None
proc = None
q_lock = Lock()
counter_file = "counter.txt"
log_file = "history.log"

DEBUG = os.getenv("DEBUG", None) is not None


def get_id():
    with open("counter.txt", "r+") as f:
        val = int(f.read())
        val += 1
        f.seek(0)
        f.write(str(val))
        return val


class State(Enum):
    QUEUED = 1
    RUNNING = 2
    ENDED = 3
    CANCELLED = 4
    KILLED = 5


class Job:
    def __init__(self, cmd, path):
        self.queued = time()
        self.cmd = cmd  # no need to split if shell=True in Popen
        self.state = State.QUEUED
        self.launch_time = datetime.now()
        self.path = path
        self.id = get_id()
        self.log_path = os.path.join(self.path, f"job-{self.id}.out")

    def run(self):
        global proc
        global q_lock

        with open(self.log_path, "a") as log:
            self.start = time()
            self.state = State.RUNNING
            if DEBUG:
                print("Launching", self)
            proc = sub.Popen(
                f"cd {self.path}\n" + self.cmd, stdout=log, stderr=log, shell=True
            )
            proc.wait()
            self.end = time()

            if self.state == State.KILLED:
                log.write("=== JOB KILLED ===")
                if DEBUG:
                    print("Killed", self)
            else:
                self.state = State.ENDED
                self.record()
                if DEBUG:
                    print("Finished", self)
            log.flush()

    def record(self):
        print("Logging ", self.info())
        with open("history.log", "a") as h:
            h.write(json.dumps(self.info()) + "\n")

    def info(self):

        if self.state == State.RUNNING:
            now = time()
            elapsed = str(timedelta(seconds=now - self.start))

        elif self.state == State.ENDED:
            elapsed = str(timedelta(seconds=self.end - self.start))

        else:  # QUEUED, KILLED, CANCELLED
            elapsed = str(timedelta(seconds=0))

        return {
            "id": self.id,
            "cmd": self.cmd,
            "elapsed": elapsed,
            "creation": self.launch_time.strftime("%Y/%m/%d-%H:%M:%S"),
            "state": self.state.name,
            "path": self.log_path,
        }

    def __repr__(self):
        return f"Job {self.id} '{self.cmd}'"


class MainLoop(Thread):
    def run(self):
        global queue
        global running
        while True:
            job = queue.get()
            # DANGER ZONE job is not queued nor running
            q_lock.acquire()
            queue.task_done()
            if job.state != State.CANCELLED:
                running = job
                q_lock.release()

                job.run()

                q_lock.acquire()
                running = None
                q_lock.release()
            else:
                q_lock.release()
                if DEBUG:
                    print(f"Discarding job {job.id} '{job}'")


class MyRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global q_lock
        if self.headers["Content-type"] == "application/json":
            content_len = int(self.headers["Content-length"])
            msg_bytes = self.rfile.read(content_len)
            msg_str = msg_bytes.decode("utf-8")
            msg = json.loads(msg_str)
            try:
                action = msg["action"]
                body = msg["body"]
                path = msg["path"]
            except KeyError as e:
                reply = {"result": "", "error": f"Missing {e} field."}
                self.send(reply)
                return

            if action == "add":
                job = Job(body, path)
                queue.put(job)
                if DEBUG:
                    print("Added", str(job), "to queue.")
                    print(self.status())
                reply = {"result": job.info(), "error": ""}

            elif action == "cancel":
                try:
                    to_cancel = int(body)
                except ValueError as e:
                    reply = {"result": "", "error": f"Wrong ID format. {e}"}
                else:
                    if DEBUG:
                        print(f"Canceling {to_cancel}")
                    q_lock.acquire()
                    cancelled = None
                    for job in queue.queue:
                        if job.id == to_cancel:
                            cancelled = job
                            job.state = State.CANCELLED
                    q_lock.release()
                    if cancelled is not None:
                        if DEBUG:
                            print(self.status())
                        reply = {
                            "result": f"{cancelled.id}",
                            "error": "",
                        }
                    else:
                        reply = {"result": "", "error": "Job not found."}
            elif action == "cancel_all":
                count = 0
                q_lock.acquire()
                for job in queue.queue:
                    if job.state != State.CANCELLED:
                        job.state = State.CANCELLED
                        count += 1
                q_lock.release()
                if count == 0:
                    reply = {"result": f"No jobs to cancel.", "error": ""}
                else:
                    reply = {"result": f"Cancelled {count} jobs", "error": ""}
            elif action == "kill":
                global running
                global proc
                if running is not None and proc is not None:
                    proc.kill()
                    running.state = State.KILLED
                    reply = {
                        "result": f"Killed {running}",
                        "error": "",
                    }
                    running = None
                    proc = None
                else:
                    reply = {"result": f"Nothing to kill.", "error": ""}

            else:
                reply = {"result": "", "error": "Unrecognized action"}

            self.send(reply)

    def do_GET(self):
        # Ignoring self.path
        jobs = []
        if running is not None:
            jobs.append(running.info())
        for job in queue.queue:
            jobs.append(job.info())
        reply = {"result": jobs, "error": ""}
        self.send(reply)

    def status(self):
        if queue.qsize() == 0:
            msg = "Queue: No jobs."
        else:
            msg = "Queue:\n" + "\n".join([str(job) for job in queue.queue])
        return msg

    def send(self, msg):

        msg_str = json.dumps(msg)
        msg_bytes = msg_str.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", len(msg_bytes))
        self.end_headers()
        self.wfile.write(msg_bytes)


t = MainLoop()
t.daemon = True
t.start()

try:
    server = HTTPServer(("", 12345), MyRequestHandler)
    server.serve_forever()
except KeyboardInterrupt:
    print(" Shutting server down.")
    server.socket.close()
