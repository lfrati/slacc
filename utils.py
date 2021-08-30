def rpad(s, N):
    spaces = " " * (N - len(s))
    return s + spaces


def lpad(s, N):
    spaces = " " * (N - len(s))
    return spaces + s


def status(jobs):
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
