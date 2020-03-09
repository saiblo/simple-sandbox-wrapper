import asyncio
import json
import sys
import os
from judger.localPlayer import localPlayer
from judger.gameLogic import gameLogic
from uuid import uuid1

class Judger:
    def __init__(self):
        self.clear()

    def clear(self):
        self.playerDict = {}
        self.logic = None
        self.judgeResult = {}

    def addLocalPlayer(self, index, Args):
        self.playerDict[index] = localPlayer(Args, index)

    def delPlayer(self, index):
        if not self.playerDict.has_key(index):
            return
        del self.playerDict[index]

    def checkPlayerDict(self):
        keyList = list(self.playerDict.keys())
        keyList.sort()
        for index_, key_ in enumerate(keyList):
            if index_ != key_:
                return False
        return True

    def invalidStartError(self):
        errorDict = {'error': 'invalidStartError'}
        return json.dumps(errorDict)

    def timeOutError(self):
        errorDict = {'error': 'timeOutError'}
        return json.dumps(errorDict)

    def logicRunError(self):
        errorDict = {'error': 'logicRunError'}
        return json.dumps(errorDict)

    async def startJudge(self, args, config, replay, judgeMaxTime):
        if not self.checkPlayerDict():
            fut.set_result(self.invalidStartError())
            return
        self.logic = gameLogic(args)
        logicTask = asyncio.create_task(self.logic.startGame(self.playerDict, config, replay))
        try:
            self.judgeResult['end_info'] = await asyncio.wait_for(logicTask, timeout=judgeMaxTime)
        except asyncio.TimeoutError:
            self.judgeResult['end_info'] = self.timeOutError()
        except asyncio.CancelledError:
            self.judgeResult['end_info'] = self.logicRunError()
        finally:
            await self.logic.clear()
            await self.logic.endFuture
            for player_ in self.playerDict.values():
                await player_.endFuture
            self.judgeResult['logic_info'] = self.logic.endFuture.result()
            self.judgeResult['player_info'] = []
            for player_ in self.playerDict.values():
                self.judgeResult['player_info'].append(player_.endFuture.result())
            return self.judgeResult