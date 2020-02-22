import asyncio
import aiofiles
import os
from .utils import enSureDir, rmdir
from .utils import log


class SandboxInstance:
    def __init__(
        self, pid, cgroup, stdinFIFO, stdoutFIFO, stderrFIFO, endedCallback=None,
    ):
        self.pid = pid
        self.cgroup = cgroup
        self.stdinFIFO = stdinFIFO
        self.stdoutFIFO = stdoutFIFO
        self.stderrFIFO = stderrFIFO
        self.initialized = False
        self.initializedFuture = asyncio.Future()
        self.isEnded = False
        self.endedCallback = endedCallback
        self.endedFuture = asyncio.Future()
        self.stdoutContent = None
        self.stderrContent = None

    def __del__(self):
        asyncio.create_task(self.cleanUp())

    async def openFIFO(self):
        self.stdinFIFO, self.stdoutFIFO, self.stderrFIFO = await asyncio.gather(
            self.stdinFIFO, self.stdoutFIFO, self.stderrFIFO
        )

    async def initialize(self):
        await asyncio.gather(self.openFIFO(), self.addFreezerCgroup())
        self.initialized = True
        self.initializedFuture.set_result(None)

    async def cleanUp(self):
        # log(f"Clean up sandbox instance [PID: {self.pid}, CGROUP: {self.cgroup}]")
        await asyncio.gather(
            self.stdinFIFO.close(), self.stdoutFIFO.close(), self.stderrFIFO.close()
        )

    async def _end(self, result):
        log(f"Sandbox instance [PID: {self.pid}, CGROUP: {self.cgroup}] ended")
        self.isEnded = True
        self.endedFuture.set_result(result)
        if self.endedCallback:
            self.endedCallback(result)

    def waitForStop(self):
        return self.endedFuture

    async def getStdoutContent(self):
        if not self.stdoutContent:
            self.stdoutContent = await self.stdoutFIFO.read()
        return self.stdoutContent

    async def getStderrContent(self):
        if not self.stderrContent:
            self.stderrContent = await self.stderrFIFO.read()
        return self.stderrContent

    async def forceStop(self):
        os.kill(self.pid, 9)
        return await self.endedFuture

    async def addFreezerCgroup(self):
        try:
            async with aiofiles.open(
                f"/sys/fs/cgroup/freezer/{self.cgroup}/tasks", mode="w"
            ) as f:
                await f.write(str(self.pid))
        except OSError:
            pass

    async def freeze(self):
        if self.isEnded:
            return
        try:
            async with aiofiles.open(
                f"/sys/fs/cgroup/freezer/{self.cgroup}/freezer.state", mode="w"
            ) as f:
                await f.write("FROZEN")
        except OSError:
            pass

    async def thaw(self):
        if self.isEnded:
            return
        try:
            async with aiofiles.open(
                f"/sys/fs/cgroup/freezer/{self.cgroup}/freezer.state", mode="w"
            ) as f:
                await f.write("THAWED")
        except OSError:
            pass
