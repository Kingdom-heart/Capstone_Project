from naoqi import *
import time
import reach as tracker

'''
-----------------GLOBALS--------------------------------------------------------------------
'''
stateDict = {
	"listening":1,
	"selling":2,
	"tracking":3,
	"grabbing":4
}

ROBOT_IP = '127.0.0.1'
global broker; broker = ALBroker("pythonBroker","0.0.0.0", 0, ROBOT_IP, 9559)
global pythonSpeechModule;
currentState = stateDict['listening']

'''
-----------SPEECH RECO--------------------------------------------------------------------	
	This is a module that initiates the speech recognition sequence and callbacks
-------------------------------------------------------------------------------------------------
'''
class SpeechRecoModule(ALModule):
	""" A module to use speech recognition """
	def __init__(self, name):
		ALModule.__init__(self, name)
		try:
			self.asr = ALProxy("ALSpeechRecognition")
			self.moving = ALProxy("ALAutonomousMoves")
			self.moving.setExpressiveListeningEnabled(False)
		except Exception as e:
			self.asr = None
		self.memory = ALProxy("ALMemory")

	def onLoad(self):
		from threading import Lock
		self.bIsRunning = False
		self.mutex = Lock()
		self.hasPushed = False
		self.hasSubscribed = False
		self.BIND_PYTHON(self.getName(), "onWordRecognized")

	def onUnload(self):
		from threading import Lock
		self.mutex.acquire()
		try:
			if (self.bIsRunning):
				if (self.hasSubscribed):
					self.memory.unsubscribeToEvent("WordRecognized", self.getName())
				if (self.hasPushed and self.asr):
					self.asr.popContexts()
		except RuntimeError, e:
			self.mutex.release()
			raise e
		self.bIsRunning = False;
		self.mutex.release()

	def onInput_onStart(self):
		from threading import Lock
		self.mutex.acquire()
		if(self.bIsRunning):
			self.mutex.release()
			return
		self.bIsRunning = True
		try:
			if self.asr:
				self.asr.setVisualExpression(True)
				self.asr.pushContexts()
			self.hasPushed = True
			if self.asr:
				self.asr.setVocabulary( ['banana','yes'], True )
			self.memory.subscribeToEvent("WordRecognized", self.getName(), "onWordRecognized")
			self.hasSubscribed = True
		except RuntimeError, e:
			self.mutex.release()
			self.onUnload()
			raise e
		self.mutex.release()

	def onWordRecognized(self, key, value, message):
		global currentState
		if(len(value) > 1 and value[1] >= 0.5):
			print 'recognized the word :', value[0]
			if value[0] == "<...> banana <...>" :
				tts = ALProxy("ALTextToSpeech", "127.0.0.1", 9559)
				tts.say("Do you want to buy a banana?")
				currentState = stateDict['selling']
			if value[0] == "<...> yes <...>" and currentState == stateDict['selling']:
				tts = ALProxy("ALTextToSpeech", "127.0.0.1", 9559)
				tts.say("okay let me look for that banana")
				currentState = stateDict['tracking']
				return
		else:
			print 'unsifficient threshold'

'''
----------------METHODS------------------------------------------------------------
'''
#---------------Function to lock/unlock motors for motion 
def StiffnessOn(proxy):
  #We use the "Body" name to signify the collection of all joints
  pNames = "Body"
  pStiffnessLists = 1.0
  pTimeLists = 1.0
  proxy.stiffnessInterpolation(pNames, pStiffnessLists, pTimeLists)

def lookAtInventory(motionProxy):
	headYaw = "HeadYaw"
	headPitch = "HeadPitch"
	x_turn = .8
	y_turn= .2  

	#position the head to look towards Caitlyn's inventory
	motion.angleInterpolation( [headYaw],[0,x_turn],[1,2],False )

	motion.angleInterpolation([headPitch],[0,y_turn],[1,2], False)
	time.sleep(1.0)
	motion.setStiffnesses("Head",0.0)

def moveArmToBanana(motionProxy):
	#position the arm so that the hands will be able to grab the banana
	names = ["LShoulderRoll","LElbowRoll","LElbowYaw","LWristYaw","LShoulderPitch"]

	timeLists = [[2.0],[2.0],[2.0],[2.0],[2.0]]
	isAbsolute = True
	angleLists = [[.15],[-1.09],[-.94],[-.605],[.5]]
	motionProxy.angleInterpolation(names, angleLists, timeLists, isAbsolute)
	time.sleep(0.5)

	names = ["LShoulderRoll","LElbowRoll","LElbowYaw","LWristYaw","LShoulderPitch"]

	timeLists = [[2.0],[2.0],[2.0],[2.0],[2.0]]
	isAbsolute = True
	angleLists = [[1.3],[-1.12],[.368],[-.352],[.6]]
	motionProxy.angleInterpolation(names, angleLists, timeLists, isAbsolute)
	time.sleep(0.5)

def lowerArm(motionProxy):

	names = ["LShoulderRoll","LElbowRoll","LElbowYaw","LWristYaw","LShoulderPitch"]

	timeLists = [[2.0],[2.0],[2.0],[2.0],[2.0]]
	isAbsolute = True
	angleLists = [[1.3],[-1.12],[.368],[-.352],[.80]]
	motionProxy.angleInterpolation(names, angleLists, timeLists, isAbsolute)
	time.sleep(0.5)

def openClose(motionProxy):
	#-----open and close the hand to grab the banana
	hands = []
	hands.append( "LHand" )
	ids = []
	for hand in hands:
		ids.append( motion.post.openHand(hand) )
	for id in ids:
		motion.wait( id, 0 )
	ids = []
	for hand in hands:
		ids.append( motion.post.closeHand(hand) )
	for id in ids:
		motion.wait( id, 0 )

'''
--------------------OFFER BANANA--------------------
	This function will bring the banana to the buyer
'''
def offerBanana(motionProxy):

	names = ["LShoulderRoll","LElbowRoll","LElbowYaw","LWristYaw","LShoulderPitch"]

	timeLists = [[2.0],[2.0],[2.0],[2.0],[2.0]]
	isAbsolute = True
	angleLists = [[.9],[-1.101],[-.947],[-.602],[.20]]
	motion.angleInterpolation(names, angleLists, timeLists, isAbsolute)
	time.sleep(0.5)
'''
--------------------CHECK HANDS----------------------------------------------------------
	This function will compare the initial angles given and the current angles of 
	each hand to determine whether there is a banana in Caitlyn's hand or not
	Returns: False for no banana/ True for banana
'''
def checkHands(motionProxy):
	names = ["RHand", "LHand"]
	commandAngles = motionProxy.getAngles(names,False)
	print "Command Angles:"
	print str(commandAngles)
	print ""
	sensorAngles = motionProxy.getAngles(names,True)
	print "Sensor Angles:"
	print str(sensorAngles)
	print ""

	if sensorAngles[1]  < 0.2:
		print "Caitlyn closed her hand fully and is not holding a banana."
		return False
	else:
		print "Caitlyn is still holding a banana"
		return True
'''
-------------------------END METHODS-----------------------------------------------------
'''


#------Start listening for commands to start sale sequence
pythonSpeechModule = SpeechRecoModule('pythonSpeechModule')
pythonSpeechModule.onLoad()
pythonSpeechModule.onInput_onStart()
time.sleep(15)
pythonSpeechModule.onUnload()

#--------Start stage 2
if(currentState == stateDict['tracking']): 

	#------initialize proxies for motion at ROBOT_IP and port number
	motion = ALProxy("ALMotion",ROBOT_IP,9559)
	posture = ALProxy("ALRobotPosture",ROBOT_IP,9559)
	tts = ALProxy("ALTextToSpeech","127.0.0.1",9559)#, "<IP of your robot>", 9559)

	#unlock the motors to ready caitlyn for movement
	StiffnessOn(motion)

	#reset hand angles
	hands = ["RHand","LHand"]
	closeAngles = [0,0]
	openAngles = [1,1]
	motion.setAngles(hands,closeAngles,1)

	#position the head of Caitlyn to look at the banana -> Classifier is not being used as of yet
	lookAtInventory(motion)

	#open the hands of Caitlyn
	motion.setAngles(hands,openAngles,.4)

	#position the arm so that Caitlyn can grab the banana in its inventory -> Classifier not in use yet
	moveArmToBanana(motion)

	#grab the banana
	lowerArm(motion)
	motion.setAngles(hands,closeAngles,.6)

	# move Caitlyn's head to look at her hand while banana is being offered
	x_turn = -.8
	y_turn= -.16
	headYaw = "HeadYaw"
	headPitch = "HeadPitch"
	motion.angleInterpolation([headYaw],[0,x_turn],[1,2],False )
	motion.angleInterpolation([headPitch],[0,y_turn],[1,2], False)
	time.sleep(1.0)
	motion.setStiffnesses("Head",0.0)

	#offer the banana to the buyer
	offerBanana(motion)

	tts.post.say("Here's your banana sir or madame!")
	#give buyer time to acquire banana
	time.sleep(10)

	#check if banana was removed  (testing sending the commands to the robot)
	isHolding = checkHands(motion)
	#reset posture for tracking
	posture.goToPosture("Sit",1.0)
	motion.setAngles(hands,closeAngles,1)
	time.sleep(3.0)
	if isHolding == False:
		got_banana = False
		nao = tracker.Banana_detective()
		while(True):
			nao.takePicture()
			coords=nao.detect_banana()
			nao.look(coords)
			time.sleep(2)
			got_banana = checkHands(motion)
			if got_banana == True:
				#do something here
				posture.goToPosture("Sit",1)
				tts.say('This was my last one sorry! Come back tomorrow.')
				break
			else:
				posture.goToPosture("Sit",1)
				motion.setAngles(hands,closeAngles,1)
				tts.say("I don't have anything to sell because of you.")
	else:
		tts.say("I can make some money off this thing!")
else:
	tts = ALProxy("ALTextToSpeech","127.0.0.1",9559)#, "<IP of your robot>", 9559)
	tts.post.say("Hello World!")

  

