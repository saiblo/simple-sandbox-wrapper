import asyncio
import json
from judger.processManager import processManager

class localPlayer(processManager):
	def __init__(self, startArgs, index):
		processManager.__init__(self, startArgs)
		self.index = index
		self.state = 0
		self.time = 5

	def askInitState(self):
		return (0 if self.endTag else 1)

	def runError(self, state):
		errorDict = {'player': self.index,
					 'state': self.state,
					 'error': 0,
					 'error_log': 'runError'}
		sendDict = {'player': -1, 'content': json.dumps(errorDict)}
		return self.convertByte(json.dumps(sendDict))

	def timeOutError(self, state):
		errorDict = {'player': self.index, 
					 'state': state,
					 'error': 1, 
					 'error_log': 'timeOutError'}
		sendDict = {'player': -1, 'content': json.dumps(errorDict)}
		return self.convertByte(json.dumps(sendDict))

	def addDataHead(self, data):
		sendDict = {"player": self.index, "content": data.decode()}
		return self.convertByte(json.dumps(sendDict))

	async def listen(self, sendToLogic):
		while True:
			byteLen = await self.readMessage(4)
			if not byteLen:
				await sendToLogic(self.runError(self.state))
				return
			intLen = int.from_bytes(byteLen, byteorder='big', signed=True)
			data = await self.readMessage(intLen)
			if not data:
				await sendToLogic(self.runError(self.state))
				return
			await sendToLogic(self.addDataHead(data))

	async def roundStart(self, state, sendToLogic):
		self.state = state
		await asyncio.sleep(self.time)
		await sendToLogic(self.timeOutError(state))

		