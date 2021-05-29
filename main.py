import asyncio
import concurrent.futures
import os
import signal
import sys
from time import sleep

from auto_play import play
from player_eye import dispatch


def handler(signum, frame):
    print('SIGINT for PID=', os.getpid())


def init():
    signal.signal(signal.SIGINT, handler)


async def main(g_exe):

    await asyncio.gather(
        play("left_up"),
        play("left_down"),
        dispatch(g_exe),
    )

if __name__ == "__main__":
    g_exe = concurrent.futures.ProcessPoolExecutor(
        max_workers=4, initializer=init)

    try:
        asyncio.run(main(g_exe))
    except KeyboardInterrupt:
        print('ctrl + c')
    finally:
        g_exe.shutdown()
