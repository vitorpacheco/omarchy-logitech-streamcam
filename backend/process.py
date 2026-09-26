"""Bounded subprocess execution for the fixed, trusted V4L2 tool."""
import os
from os import read
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

STDOUT_LIMIT = 256 * 1024
STDERR_LIMIT = 16 * 1024
ENVIRONMENT = {"PATH": "/usr/bin", "LANG": "C", "LC_ALL": "C"}


class OutputLimitError(Exception):
    pass


def trusted_v4l2():
    path = Path('/usr/bin/v4l2-ctl').resolve(strict=True)
    for entry in (path, *path.parents):
        info = entry.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise FileNotFoundError('Untrusted v4l2-ctl installation')
    if not stat.S_ISREG(path.stat().st_mode) or not os.access(path, os.X_OK):
        raise FileNotFoundError('v4l2-ctl is not executable')
    return str(path)


def _exited(process):
    # Keep the leader unreaped until group cleanup, preventing PGID reuse.
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def _cleanup(process):
    try:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if _exited(process) is None:
            time.sleep(0.1)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    finally:
        process.wait()
        process.stdout.close()
        process.stderr.close()


def run_bounded(argv, timeout=8, stdout_limit=STDOUT_LIMIT, stderr_limit=STDERR_LIMIT):
    deadline = time.monotonic() + timeout
    if timeout <= 0:
        raise subprocess.TimeoutExpired(argv, timeout)
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=dict(ENVIRONMENT), start_new_session=True)
    output = [bytearray(), bytearray()]
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, timeout)
                for key, _ in selector.select(remaining):
                    index = key.data
                    limit = (stdout_limit, stderr_limit)[index]
                    chunk = read(key.fileobj.fileno(), min(65536, limit - len(output[index]) + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    elif len(output[index]) + len(chunk) > limit:
                        raise OutputLimitError('Subprocess output limit exceeded')
                    else:
                        output[index].extend(chunk)
            while (status := _exited(process)) is None:
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(argv, timeout)
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            code = status.si_status if status.si_code == os.CLD_EXITED else -status.si_status
            return subprocess.CompletedProcess(argv, code, *(data.decode('utf-8', errors='replace') for data in output))
    finally:
        _cleanup(process)
