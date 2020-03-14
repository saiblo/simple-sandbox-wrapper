import logging
import asyncio
import aiofiles
import os

from functools import partial, wraps

logger = logging.getLogger("Sandbox")

def wrap(func):
    @asyncio.coroutine
    @wraps(func)
    def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return loop.run_in_executor(executor, pfunc)
    return run

mkdir = wrap(os.mkdir)
unlink = wrap(os.unlink)

def openReadFIFO(name):
    os.mkfifo(name)
    return asyncio.create_task(aiofiles.open(name, "rb"))


def openWriteFIFO(name):
    os.mkfifo(name)
    return asyncio.create_task(aiofiles.open(name, "wb"))


async def enSureDir(path):
    if not os.path.isdir(path):
        os.mkdir(path)


async def rmdir(path):
    os.rmdir(path)


def log(string):
    logger.debug(string)

