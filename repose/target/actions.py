from queue import Queue
import sys
import threading
import time
from typing import Any


queue: Queue[list[Any]] = Queue()


class ThreadedMethod(threading.Thread):
    def __init__(self, queue) -> None:
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self) -> None:
        while True:
            try:
                (method, parameter) = self.queue.get(timeout=10)
            except BaseException:
                return

            try:
                method(*parameter)
            except BaseException:
                raise
            finally:
                try:
                    self.queue.task_done()
                except ValueError:
                    pass  # already removed by ctrl+c


class RunCommand:
    def __init__(self, targets, command: dict[str, str] | str) -> None:
        self.targets = targets
        self.command = command

    def run(self) -> None:
        lock = threading.Lock()

        try:
            for target in self.targets:
                thread = ThreadedMethod(queue)
                thread.daemon = True
                thread.start()
                if isinstance(self.command, dict):
                    queue.put([self.targets[target].run, [self.command[target], lock]])
                elif isinstance(self.command, str):
                    queue.put([self.targets[target].run, [self.command, lock]])

            while queue.unfinished_tasks:
                spinner(lock)

            queue.join()

        except KeyboardInterrupt:
            print("stopping command queue, please wait.")
            try:
                while queue.unfinished_tasks:
                    spinner(lock)
            except KeyboardInterrupt:
                for target in self.targets:
                    try:
                        self.targets[target].connection.close_session()
                    except Exception:
                        pass
                try:
                    thread.queue.task_done()
                except ValueError:
                    pass

            queue.join()
            raise


def spinner(lock=None) -> None:
    """simple spinner to show some process"""

    for pos in ["|", "/", "-", "\\"]:
        if lock is not None:
            lock.acquire()

        try:
            sys.stdout.write(f"processing... [{pos}]\r")
            sys.stdout.flush()
        finally:
            if lock is not None:
                lock.release()

        time.sleep(0.1)
