from judger.judger import Judger
import asyncio
import sys

logicArgs = {
    "hostname": "qwq",
    "chroot": "/opt/sandbox/rootfs",
    "mounts": [
        {
            "src": "/opt/sandbox-test/working",
            "dst": "/sandbox/working",
            "limit": 1,
        }
    ],
    "executable": "/usr/bin/python3",
    "parameters": ["/usr/bin/python3", "logic_python.py"],
    "environments": [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ],
    "time": 20*1000,
    "mountProc": True,
    "redirectBeforeChroot": True,
    "memory": 104857600,
    "process": 10,
    "user": "nobody",
    "workingDirectory": "/sandbox/working",
}

aiArgs = {
    "hostname": "qwq",
    "chroot": "/opt/sandbox/rootfs",
    "mounts": [
        {
            "src": "/opt/sandbox-test/working",
            "dst": "/sandbox/working",
            "limit": 0,
        }
    ],
    "executable": "/usr/bin/python3",
    "parameters": ["/usr/bin/python3", "ai_1.py"],
    "environments": [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ],
    "time": 20*1000,
    "mountProc": True,
    "redirectBeforeChroot": True,
    "memory": 104857600,
    "process": 10,
    "user": "nobody",
    "workingDirectory": "/sandbox/working",
}

async def main():
    judger = Judger()
    judger.addLocalPlayer(0, aiArgs)
    judger.addLocalPlayer(1, aiArgs)
    returnCode = await judger.startJudge(logicArgs, "", 'replay', (int)(sys.argv[1]))
    print(returnCode)
if __name__ == '__main__':
    asyncio.run(main(), debug=True)