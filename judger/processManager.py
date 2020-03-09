import sys
import asyncio
import json
from simple_sandbox_wrapper import sandbox

class processManager:
    def __init__(self, startArgs):
        self.startArgs = startArgs
        self.endTag = True
        self.freezeTag = True
        self.initFuture = asyncio.Future()
        self.queue = asyncio.Queue()
        self.endFuture = asyncio.Future()
        self.sandboxInstance = None

    async def endCallback(self, result):
        self.endTag = True
        await self.initFuture
        err = await self.sandboxInstance.getStderrContent()
        self.endFuture.set_result(json.dumps(
                                  {'result': result,
                                   'stderr': err.decode()}))

    async def start(self, endCallback=None):
        self.sandboxInstance = await sandbox.startSandbox(self.startArgs, endedCallback=endCallback)
        self.initFuture.set_result('process start done!')
        print(self.sandboxInstance)
        self.endTag = False
        self.freezeTag = False

    async def end(self):
        if self.endTag:
            return
        self.endTag = True
        await self.sandboxInstance.forceStop()

    async def freeze(self):
        if self.endTag or self.freezeTag:
            return
        self.freezeTag = True
        await self.sandboxInstance.freeze()

    async def thaw(self):
        if self.endTag or not self.freezeTag:
            return
        await self.sandboxInstance.thaw()
        self.freezeTag = False

    def convertByte(self, msg):
        msgLen = len(msg)
        msgBytes = msgLen.to_bytes(4, byteorder='big', signed=True)
        msgBytes += bytes(msg, encoding='utf8')
        return msgBytes

    async def putMessage(self, msg):
        await self.queue.put(msg)

    async def getMessage(self):
        while True:
            msg = await self.queue.get()
            await self.sendMessage(msg)

    async def sendMessage(self, msg):
        await self.sandboxInstance.stdinFIFO.write(msg)
        print(f'{msg} send!')
        await self.sandboxInstance.stdinFIFO.flush()

    async def readMessage(self, len):
        msg = await self.sandboxInstance.stdoutFIFO.read(len)
        return msg