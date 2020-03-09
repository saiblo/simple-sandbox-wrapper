import asyncio
import json
import functools
from simple_sandbox_wrapper import sandbox
from uuid import uuid1
from judger.processManager import processManager

class gameLogic(processManager):
    def __init__(self, startArgs):
        processManager.__init__(self, startArgs)
        self.playerDict = {}
        self.taskDict = {}
        self.taskListenList = []
        self.state = 0

    async def startGame(self, playerDict, config, replay):
        self.playerDict = playerDict
        startList = []
        for player_ in self.playerDict.values():
            startList.append(self.taskAdd(player_.start(player_.endCallback)))
        startList.append(self.taskAdd(self.start(self.endCallback)))
        await asyncio.gather(*startList)
        await self.sendInitInfo(playerDict, config, replay)
        return await self.listen()

    async def sendInitInfo(self, playerDict, config, replay):
        playerList = [player_.askInitState() for player_ in playerDict.values()]
        playerLen = len(playerList)
        infoDict = {'player_list': playerList,
                    'player_len': playerLen,
                    'config': config,
                    'replay': replay}
        info = self.convertByte(json.dumps(infoDict))
        await self.putMessage(info)

    def checkGoal(self, goal):
        try:
            assert(goal >= -1 and goal < len(self.playerDict))
        except:
            errorDict = {'error': 'logicGoalError'}
            return json.dumps(errorDict)
        else:
            return None

    def checkData(self, data):
        try:
            dataDict = json.loads(data)
            assert('state' in dataDict)
            assert(isinstance(dataDict['state'], int))
            if dataDict['state'] > 0:
                assert('listen' in dataDict)
                assert('player' in dataDict)
                assert('content' in dataDict)
                assert(isinstance(dataDict['listen'], list))
                assert(isinstance(dataDict['player'], list))
                assert(isinstance(dataDict['content'], list))
                for listen_ in dataDict['listen']:
                    assert(isinstance(listen_, int))
                    assert(listen_ >= 0 and listen_ < len(self.playerDict))
                assert(len(dataDict['player']) == len(dataDict['content']))
                for player_ in dataDict['player']:
                    assert(isinstance(player_, int))
                    assert(player_ >= 0 and player_ < len(self.playerDict))
                for content_ in dataDict['content']:
                    assert(isinstance(content_, str))
            elif dataDict['state'] < 0:
                assert('end_info' in dataDict)
                assert(isinstance(dataDict['end_info'], str))
                endDict = json.loads(dataDict['end_info'])
                for key_ in self.playerDict.keys():
                    assert(str(key_) in endDict)
                    assert(isinstance(endDict[str(key_)], int))
        except:
            errorDict = {'error': 'logicProtocolFormatError'}
            return None, json.dumps(errorDict)
        else:
            return dataDict, None

    def taskCallback(self, id, future):
        if id in self.taskDict:
            print(f"Del task {id}")
            del self.taskDict[id]

    def taskAdd(self, coro):
        id = str(uuid1())
        print(f"Add task {id}")
        self.taskDict[id] = asyncio.create_task(coro)
        self.taskDict[id].add_done_callback(functools.partial(self.taskCallback, id))
        return self.taskDict[id]

    async def updateState(self, msgDict):
        self.state = msgDict['state']
        print(f'state = {self.state}')
        for task_ in self.taskListenList:
            task_.cancel()
        for key_ in self.playerDict.keys():
            if key_ in msgDict['listen']:
                await self.playerDict[key_].thaw()
            else:
                await self.playerDict[key_].freeze()
        sendList = []
        for index_, content_ in enumerate(msgDict['content']):
            sendList.append((msgDict['player'][index_], 
                            bytes(content_, encoding='utf8')))
        for send_ in sendList:
            self.taskAdd(self.playerDict[send_[0]].putMessage(send_[1]))
        print('send Done!')
        self.taskListenList = []
        for index_ in msgDict['listen']:
            self.taskListenList.append(self.taskAdd(self.playerDict[index_].roundStart(self.state, self.putMessage)))

    async def listen(self):
        self.taskAdd(self.getMessage())
        for player_ in self.playerDict.values():
            self.taskAdd(player_.getMessage())
        for player_ in self.playerDict.values():
            self.taskAdd(player_.listen(self.putMessage))
        while True:
            byteLen = await self.readMessage(4)
            if not byteLen:
                return json.dumps({'error': 'logicRunError'})
            intLen = int.from_bytes(byteLen, byteorder='big', signed=True)
            byteGoal = await self.readMessage(4)
            if not byteGoal:
                return json.dumps({'error': 'logicRunError'})
            intGoal = int.from_bytes(byteGoal, byteorder='big', signed=True)
            data = await self.readMessage(intLen)
            if not data:
                return json.dumps({'error': 'logicRunError'})
            print(data)
            goalFlag = self.checkGoal(intGoal)
            if goalFlag is not None:
                return goalFlag
            if intGoal == -1:
                dataDict, dataFlag = self.checkData(data)
                if dataFlag is not None:
                    return dataFlag
                if dataDict['state'] > 0:
                    await self.updateState(dataDict)
                elif dataDict['state'] < 0:
                    return dataDict['end_info']
                # TODO: state = 0 
            else:
                self.taskAdd(self.playerDict[intGoal].putMessage(data))
    async def clear(self):
        for task_ in self.taskDict.values():
            task_.cancel()
        endTask = []
        for player_ in self.playerDict.values():
            endTask.append(self.taskAdd(player_.end()))
        endTask.append(self.taskAdd(self.end()))
        await asyncio.gather(*endTask)
        for player_ in self.playerDict.values():
            del player_.sandboxInstance
            #await player_.sandboxInstance.cleanUp()
        del self.sandboxInstance
        #await self.sandboxInstance.cleanUp()

