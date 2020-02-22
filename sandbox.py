import socketio
import asyncio
import logging
import signal
import traceback
import os
from uuid import uuid1
from .utils import openWriteFIFO, openReadFIFO, log
from .sandbox_instance import SandboxInstance

instance_map = {}
fifoDir = "/tmp/simple-sandbox-wrapper/"
sio = None


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

    async def startedCallback(pid, cgroup):
        log(f"Receive startSandbox request [{uuid}] response")
        instance = SandboxInstance(
            pid,
            cgroup,
            stdinFIFO,
            stdoutFIFO,
            stderrFIFO,
            endedCallback,
        )
        instance_map[uuid] = instance
        await instance.initialize()
        log(f"Sandbox instance [PID: {pid}, CGROUP: {cgroup}] created")
        fut.set_result(instance)

    log(f"Send startSandbox request [{uuid}] to daemon")
    await sio.emit("startSandbox", {
        "uuid": uuid,
        "args": startArgs
    },
                   callback=startedCallback)


def startSandbox(startArgs, endedCallback=None):
    fut = asyncio.Future()
    asyncio.create_task(startSandboxCoro(fut, startArgs, endedCallback))
    return fut


async def sandboxEnded(uuid, result):
    log(f"Receive sandboxEnded signal [{uuid}]")
    if uuid in instance_map:
        await instance_map[uuid
                           ].initializedFuture  # enSure instance initalized
        await instance_map[uuid]._end(result)
        del instance_map[uuid]


async def connect(url="http://localhost:5283"):
    global sio
    sio = socketio.AsyncClient()
    await sio.connect(url)
    sio.on("sandboxEnded", handler=sandboxEnded)


async def ensureConnected():
    if not sio:
        await connect()


signaled = False


def on_signal():
    global signaled
    # if signaled:
    # log("Duplicate signals, ignoring")

    signaled = True
    # log("Signaled, stopping")

    try:
        asyncio.create_task(sio.disconnect())
    except Exception as e:
        traceback.print_exc()
        exit(-1)
