import asyncio
import socketio
import logging
import sandbox
import signal
import utils
import aiofiles

args = {
    "hostname": "qwq",
    "chroot": "/opt/sandbox/rootfs",
    "mounts": [
        {"src": "/opt/sandbox-test/binary", "dst": "/sandbox/binary", "limit": 0},
        {"src": "/opt/sandbox-test/working", "dst": "/sandbox/working", "limit": 0,},
        {"src": "/opt/sandbox-test/tmp", "dst": "/tmp", "limit": 0},
    ],
    "executable": "/usr/bin/python",
    "parameters": ["/usr/bin/python", "test.py"],
    "environments": [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ],
    "time": 1000,
    "mountProc": True,
    "redirectBeforeChroot": True,
    "memory": 104857600,
    "process": 10,
    "user": "nobody",
    "workingDirectory": "/sandbox/working",
}


async def read(f):
    while True:
        data_len_buffer = await f.read(4096)
        if not data_len_buffer:  # EOF
            break
        print(data_len_buffer)


async def main():
    await sandbox.connect()

    sandboxInstance = await sandbox.startSandbox(args)

    # sandboxInstance.uuid
    # sandboxInstance.stdinFIFO
    # sandboxInstance.stdoutFIFO
    # sandboxInstance.stderrFIFO

    result = await sandboxInstance.waitForStop()

    print(result)
    print(await sandboxInstance.getStdoutContent())


def async_run_and_await_all_tasks(main):
    def get_pending_tasks():
        tasks = asyncio.Task.all_tasks()
        pending = [task for task in tasks if task != run_main_task and not task.done()]
        return pending

    async def run_main():
        await main()

        while True:
            pending_tasks = get_pending_tasks()
            if len(pending_tasks) == 0:
                return
            await asyncio.gather(*pending_tasks)

    loop = asyncio.new_event_loop()

    # loop.add_signal_handler(signal.SIGINT, client.on_signal)
    # loop.add_signal_handler(signal.SIGTERM, client.on_signal)

    def exitProgram():
        utils.log("Receive exit signal")
        exit(0)

    loop.add_signal_handler(signal.SIGINT, exitProgram)
    loop.add_signal_handler(signal.SIGTERM, exitProgram)

    run_main_coro = run_main()
    run_main_task = loop.create_task(run_main_coro)
    loop.run_until_complete(run_main_task)


# async_run_and_await_all_tasks(main)
asyncio.run(main())
