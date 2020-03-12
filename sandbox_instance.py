import asyncio
import aiofiles
import os
from .utils import enSureDir, rmdir
from .utils import log


class SandboxInstance:
    def __init__(
        self, pid, cgroup, stdinFIFO, stdoutFIFO, stderrFIFO, stdinFIFOName, stdoutFIFOName, stderrFIFOName, endedCallback=None,
    ):
        self.pid = pid
        self.cgroup = cgroup
        self.stdinFIFO = stdinFIFO
        self.stdoutFIFO = stdoutFIFO
        self.stderrFIFO = stderrFIFO
        self.stdinFIFOName = stdinFIFOName
        self.stdoutFIFOName = stdoutFIFOName
        self.stderrFIFOName = stderrFIFOName
        self.initialized = False
        self.initialized = False
        self.initializedFuture = asyncio.Future()
        self.isEnded = False
        self.endedCallback = endedCallback
        self.endedFuture = asyncio.Future()
        self.stdoutContent = None
        self.stderrContent = None
        self.isCleaned = False

    def __del__(self):
        if not self.isCleaned:
            asyncio.create_task(self.cleanUp())

    async def openFIFO(self):
        self.stdinFIFO, self.stdoutFIFO, self.stderrFIFO = await asyncio.gather(
            self.stdinFIFO, self.stdoutFIFO, self.stderrFIFO
        )

    async def initialize(self):
        await asyncio.gather(self.openFIFO())
        self.initialized = True
        self.initializedFuture.set_result(None)

    async def cleanUp(self):
        # log(f"Clean up sandbox instance [PID: {self.pid}, CGROUP: {self.cgroup}]")
        self.isCleaned = True
        await asyncio.gather(
            self.stdinFIFO.close(), self.stdoutFIFO.close(), self.stderrFIFO.close()
        )
        os.unlink(self.stdinFIFOName)
        os.unlink(self.stdoutFIFOName)
        os.unlink(self.stderrFIFOName)

    async def _end(self, result):
        log(f"Sandbox instance [PID: {self.pid}, CGROUP: {self.cgroup}] ended")
        self.isEnded = True
        self.endedFuture.set_result(result)
        if self.endedCallback:
            asyncio.create_task(self.endedCallback(result))

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
        try:
            await self.thaw()
        except:
            pass
        try:
            os.kill(self.pid, 9)
        except:
            log(f"{self.pid} not found")
        finally:
            log(f"force {self.pid} stop done")
            return await self.endedFuture

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

    async def readCgroupProperty(self, controllerName, propertyName):
        async with aiofiles.open(
            f"/sys/fs/cgroup/{controllerName}/{self.cgroup}/{propertyName}", mode="r"
        ) as f:
            return await f.read()

    async def readCgroupProperty2(self, controllerName, propertyName, subProperty):
        async with aiofiles.open(
            f"/sys/fs/cgroup/{controllerName}/{self.cgroup}/{propertyName}", mode="r"
        ) as f:
            s = await f.read()
            return dict(line.split() for line in s.split("\n") if line)

    async def getMemUsage(self):
        try:
            memUsageWithCache = int(
                await self.readCgroupProperty(
                    "memory", "memory.memsw.max_usage_in_bytes"
                )
            )
            cacheUsage = int(
                (await self.readCgroupProperty2("memory", "memory.stat", "cache"))[
                    "cache"
                ]
            )
            return memUsageWithCache - cacheUsage
        except OSError:
            await self.endedFuture
            return self.endedFuture["memory"]

    async def getCpuTimeUsage(self):
        try:
            actualCpuTime = int(
                await self.readCgroupProperty("cpuacct", "cpuacct.usage")
            )
            return actualCpuTime
        except OSError:
            await self.endedFuture
            return self.endedFuture["time"]
