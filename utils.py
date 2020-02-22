import logging
import asyncio
import aiofiles
import os

logger = logging.getLogger("Sandbox")


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
    # logger.info(string)
    print(string)
