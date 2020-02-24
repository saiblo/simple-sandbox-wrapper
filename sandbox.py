import socketio
import asyncio
import logging
import signal
import traceback
import os
from uuid import uuid1
from .utils import openWriteFIFO, openReadFIFO, log
from .sandbox_instance import SandboxInstance
from .exception import StartSandboxError

instance_map = {}
fifoDir = "/tmp/simple-sandbox-wrapper/"
sio = None
connectFuture = None


async def startSandboxCoro(fut, startArgs, endedCallback):
    await ensureConnected()

    uuid = str(uuid1())

    stdinFIFOName = f"{fifoDir}{uuid}.in"
    stdoutFIFOName = f"{fifoDir}{uuid}.out"
    stderrFIFOName = f"{fifoDir}{uuid}.err"

    stdinFIFO = openWriteFIFO(stdinFIFOName)
    stdoutFIFO = openReadFIFO(stdoutFIFOName)
    stderrFIFO = openReadFIFO(stderrFIFOName)

    startArgs["cgroup"] = uuid
    startArgs["stdin"] = stdinFIFOName
    startArgs["stdout"] = stdoutFIFOName
    startArgs["stderr"] = stderrFIFOName

    async def startedCallback(result, pid, cgroup):
        if result["success"]:
            log(
                f"Receive startSandbox request [{uuid}] response. Sandbox started successfully"
            )
            instance = SandboxInstance(
                pid, cgroup, stdinFIFO, stdoutFIFO, stderrFIFO, endedCallback,
            )
            instance_map[uuid] = instance
            await instance.initialize()
            log(f"Sandbox instance [PID: {pid}, CGROUP: {cgroup}] created")
            fut.set_result(instance)
        else:
            log(
                f"Receive startSandbox request [{uuid}] response. Sandbox failed to start, reason: {result['reason']}"
            )
            stdinFIFO.cancel()
            stdoutFIFO.cancel()
            stderrFIFO.cancel()
            fut.set_exception(StartSandboxError(result["reason"]))

    log(f"Send startSandbox request [{uuid}] to daemon")
    await sio.emit(
        "startSandbox", {"uuid": uuid, "args": startArgs}, callback=startedCallback
    )


def startSandbox(startArgs, endedCallback=None):
    fut = asyncio.Future()
    asyncio.create_task(startSandboxCoro(fut, startArgs, endedCallback))
    return fut


async def sandboxEnded(uuid, result):
    log(f"Receive sandboxEnded signal [{uuid}]")
    if uuid in instance_map:
        print(result)
        await instance_map[uuid].initializedFuture  # enSure instance initalized
        await instance_map[uuid]._end(result)
        del instance_map[uuid]


async def connect(url="http://localhost:5283"):
    global sio, connectFuture
    if not sio:
        sio = socketio.AsyncClient()
        connectFuture = asyncio.Future()
    await sio.connect(url)
    connectFuture.set_result(None)
    sio.on("sandboxEnded", handler=sandboxEnded)


async def ensureConnected():
    global sio, connectFuture
    if not sio:
        sio = socketio.AsyncClient()
        connectFuture = asyncio.Future()
        await connect()
    await connectFuture

