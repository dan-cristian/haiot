# author Ingmar Stapel
# version 0.1 BETA
# date 20140810 04:36 AM

import webiopi
from time import sleep
from time import time
import os

# Enable debug output
# webiopi.setDebug()
GPIO = webiopi.GPIO

# initiales setzen der Beschleunigung
acceleration = 0
turnacceleration = 0
# auf der Stelle drehen = false
spotturn = "false"
	
# Here we configure the PWM settings for
# the two DC motors. It defines the two GPIO
# pins used for the input on the L298 H-Bridge,
# starts the PWM and sets the
# motors' speed initial to 0
MAXSPEED = 100
MAXSTEERSPEED = 50
#BCM PINS
motorDriveForwardPin = 17 
motorDriveReversePin = 4 
motorSteerLeftPin = 6
motorSteerRightPin = 5 
#ledLeftPin = 23 #16
#ledRightPin = 24 #18
motorDrivePWM = 27 #29
motorSteerPWM = 22 #31

#ultrasonic sensor
#set GPIO Pins
GPIO_TRIGGER = 18
GPIO_ECHO = 23
SAFE_DISTANCE = 20 #cm

# IR line sensor
irLPin = 24
irCPin = 25
irRPin = 12

# alarm
alarmPin = 26

# power pin
powerPin = 13


#setup function is called automatically at WebIoPi startup
def setup():
	#GPIO.setmode(GPIO.BCM)
	GPIO.setFunction(motorDriveForwardPin, GPIO.OUT)
	GPIO.setFunction(motorDriveReversePin, GPIO.OUT)
	GPIO.setFunction(motorSteerLeftPin, GPIO.OUT)
	GPIO.setFunction(motorSteerRightPin, GPIO.OUT)
	#GPIO.setFunction(ledLeftPin, GPIO.OUT)
	#GPIO.setFunction(ledRightPin, GPIO.OUT)
	GPIO.setFunction(motorDrivePWM, GPIO.PWM)
	GPIO.setFunction(motorSteerPWM, GPIO.PWM)

	#set GPIO sound sensor direction (IN / OUT)
	GPIO.setFunction(GPIO_TRIGGER, GPIO.OUT)
	GPIO.setFunction(GPIO_ECHO, GPIO.IN)
	#set ir input
	GPIO.setFunction(irLPin, GPIO.IN)
	GPIO.setFunction(irCPin, GPIO.IN)
	GPIO.setFunction(irRPin, GPIO.IN)
	
	GPIO.setFunction(alarmPin, GPIO.IN, GPIO.PUD_UP)

	GPIO.setFunction(powerPin, GPIO.IN)
	
def initiate():
	global acceleration
	global turnacceleration
	global motorDriveSpeed
	global motorSteerSpeed
	global speedstep
	global maxspeed
	global maxsteerspeed	
	global minspeed
	
	spotturn = "false"
	acceleration = 0
	turnacceleration = 0
	motorDriveSpeed = 0
	motorSteerSpeed = 0
	speedstep = 10
	maxspeed = 100
	maxsteerspeed = 50
	minspeed = 0
	
	webiopi.utils.thread.runLoop(func=loopThread, async=True)


def loopThread():
	power = GPIO.input(powerPin)
	alarm = GPIO.input(alarmPin)
	print 'power=', power, ' alarm=', alarm, ' distance=', distance()
	sleep(1)


def reverse():
    GPIO.digitalWrite(motorDriveForwardPin, GPIO.LOW)
    GPIO.digitalWrite(motorDriveReversePin, GPIO.HIGH)

def forward():
    GPIO.digitalWrite(motorDriveForwardPin, GPIO.HIGH)
    GPIO.digitalWrite(motorDriveReversePin, GPIO.LOW)

def left():
    GPIO.digitalWrite(motorSteerLeftPin, GPIO.HIGH)
    GPIO.digitalWrite(motorSteerRightPin, GPIO.LOW)
    #GPIO.digitalWrite(ledLeftPin, GPIO.HIGH)
    #GPIO.digitalWrite(ledRightPin, GPIO.LOW)    

def right():
    GPIO.digitalWrite(motorSteerLeftPin, GPIO.LOW)
    GPIO.digitalWrite(motorSteerRightPin, GPIO.HIGH)
    #GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
    #GPIO.digitalWrite(ledRightPin, GPIO.HIGH)

def resetSteer():
	GPIO.digitalWrite(motorSteerLeftPin, GPIO.LOW)
	GPIO.digitalWrite(motorSteerRightPin, GPIO.LOW)
	#GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
	#GPIO.digitalWrite(ledRightPin, GPIO.LOW)

def flashAll():	
	#GPIO.digitalWrite(ledLeftPin, GPIO.HIGH)
	#GPIO.digitalWrite(ledRightPin, GPIO.HIGH)
	sleep(0.5)
	#GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
	#GPIO.digitalWrite(ledRightPin, GPIO.LOW)
	sleep(0.5)
	#GPIO.digitalWrite(ledLeftPin, GPIO.HIGH)
	#GPIO.digitalWrite(ledRightPin, GPIO.HIGH)
	sleep(0.5)
	#GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
	#GPIO.digitalWrite(ledRightPin, GPIO.LOW)

# stop the motors
def stop():
	GPIO.digitalWrite(motorDriveForwardPin, GPIO.LOW)
	GPIO.digitalWrite(motorDriveReversePin, GPIO.LOW)
	GPIO.digitalWrite(motorSteerLeftPin, GPIO.LOW)
	GPIO.digitalWrite(motorSteerRightPin, GPIO.LOW)
	#GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
	#GPIO.digitalWrite(ledRightPin, GPIO.LOW)
	# motorLspeed, motorRspeed, acceleration
	initiate()
	return 0, 0, 0

# stop the motors
def stopSteer():
	GPIO.digitalWrite(motorSteerLeftPin, GPIO.LOW)
	GPIO.digitalWrite(motorSteerRightPin, GPIO.LOW)
	#GPIO.digitalWrite(ledLeftPin, GPIO.LOW)
	#GPIO.digitalWrite(ledRightPin, GPIO.LOW)

# stop the motors
def stopMotor():
        GPIO.digitalWrite(motorDriveForwardPin, GPIO.LOW)
        GPIO.digitalWrite(motorDriveReversePin, GPIO.LOW)


# This functions sets the motor speed.
def setacceleration(value):
	global motorDriveSpeed
	global motorSteerSpeed
	global acceleration
	global minspeed
	global maxspeed
	
	acceleration = acceleration + value
	
	minspeed, maxsteerspeed = getMinMaxSpeed()
	
	#Set Min and Max values for acceleration
	if(acceleration < -MAXSPEED):
		acceleration = -MAXSPEED
	
	if(acceleration > MAXSPEED):
		acceleration = MAXSPEED	
	
	if(acceleration > 0):
		# drive forward
		forward()
		motorDriveSpeed = acceleration
		#print("forward: ", motorLspeed, motorRspeed)
	elif(acceleration == 0):
		# stopp motors
		motorDriveSpeed = acceleration
		motorDriveSpeed, motorSteerSpeed, acceleration = stop()
		#print("stop: ", motorLspeed, motorRspeed)
	else:
		# drive backward
		reverse()
		motorDriveSpeed = (acceleration * -1)
		#print("backward: ", motorLspeed, motorRspeed)
	
	motorDriveSpeed, motorSteerSpeed = check_motorspeed(motorDriveSpeed, motorSteerSpeed)
	#print("check: ", motorLspeed, motorRspeed)

# This functions sets the motor speed.
def setturnacceleration(value):
	global motorDriveSpeed
	global motorSteerSpeed
	global turnacceleration
	global minspeed
	global maxsteerspeed
	
	turnacceleration = turnacceleration + value
	
	minspeed, maxsteerspeed = getMinMaxSteerSpeed()
	
	#Set Min and Max values for acceleration
	if(turnacceleration < -MAXSTEERSPEED):
		turnacceleration = -MAXSTEERSPEED
	
	if(turnacceleration > MAXSTEERSPEED):
		turnacceleration = MAXSTEERSPEED	
	
	if(turnacceleration > 0):
		# drive forward
		left()
		motorSteerSpeed = turnacceleration
		#print("forward: ", motorLspeed, motorRspeed)
	elif(turnacceleration == 0):
		# stopp motors
		motorSteerSpeed = turnacceleration
		motorSteerSpeed, turnacceleration = stopSteer()
		#print("stop: ", motorLspeed, motorRspeed)
	else:
		# drive backward
		right()
		motorSteerSpeed = (turnacceleration * -1)
		#print("backward: ", motorLspeed, motorRspeed)
	
	motorDriveSpeed, motorSteerSpeed = check_motorspeed(motorDriveSpeed, motorSteerSpeed)	

# check the motorspeed if it is correct and in max/min range
def check_motorspeed(motorDriveSpeed, motorSteerSpeed):
	if (motorDriveSpeed < minspeed):
		motorDriveSpeed = minspeed

	if (motorDriveSpeed > maxspeed):
		motorDriveSpeed = maxspeed
		
	if (motorSteerSpeed < minspeed):
		motorSteerSpeed = minspeed

	if (motorSteerSpeed > maxspeed):
		motorSteerSpeed = maxspeed	
		
	return motorDriveSpeed, motorSteerSpeed

# Set Min Max Speed
def getMinMaxSpeed():
	minspeed = 0
	maxspeed = 100
	return minspeed, maxspeed

# Set Min Max Speed
def getMinMaxSteerSpeed():
	minspeed = 0
	maxsteerspeed = 50
	return minspeed, maxsteerspeed
	
# Get the motor speed
def getMotorSpeed():
	global motorDriveSpeed
	global motorSteerSpeed
	
	return motorDriveSpeed, motorSteerSpeed

def getMotorSpeedStep():
	return 10	

def getSteerMotorSpeedStep():
	return 50		
	
@webiopi.macro
def ButtonForward():
	fowardAcc = 0
	fowardAcc = getMotorSpeedStep()

	setacceleration(fowardAcc)
	
	motorDriveSpeed, motorSteerSpeed = getMotorSpeed()
	
	# percent calculation	
	valueDrive =  float(motorDriveSpeed)/100
		
	GPIO.pulseRatio(motorDrivePWM, valueDrive)
	
@webiopi.macro
def ButtonReverse():
	backwardAcc = 0
	backwardAcc = getMotorSpeedStep()

	setacceleration((backwardAcc*-1))
	
	motorDriveSpeed, motorSteerSpeed = getMotorSpeed()
	
	# percent calculation
	valueDrive = float(motorDriveSpeed)/100
		
	GPIO.pulseRatio(motorDrivePWM, valueDrive)

@webiopi.macro
def ButtonStepForward():
	try:
        	dist = distance()
		print ("Distance = ", dist)	
		if dist > SAFE_DISTANCE:
			forward()
        		sleep(0.2)
        		stopMotor()
		irL, irC, irR = irstatus()
		print ("IR=", irL, irC, irR)
	except Exception, ex:
		print ("Exception ", ex)

@webiopi.macro
def ButtonStepBack():
        reverse()
        sleep(0.2)
        stopMotor()


@webiopi.macro
def ButtonTurnLeft():
	left()
	#GPIO.pulseRatio(motorSteerPWM, 0.7)	
	sleep(0.05)
	resetSteer()

@webiopi.macro
def ButtonTurnRight():
	print ("Turn right")
	right()
	print ("Pause")
	#GPIO.pulseRatio(motorSteerPWM, 0.7)
	sleep(0.05)	
	print ("Reset")
	resetSteer()

@webiopi.macro
def ButtonTurnLeftOld():
	global motorSteerSpeed
	global motorDriveSpeed
	global speedstep

	steerLeftAcc = 0
	steerLeftAcc = getSteerMotorSpeedStep()

	setturnacceleration((steerLeftAcc))
	
	motorDriveSpeed, motorSteerSpeed = getMotorSpeed()
	
	# percent calculation
	valueDrive = float(motorSteerSpeed)/100
		
	GPIO.pulseRatio(motorSteerPWM, valueDrive)
	
	#print("LEFT: ",valueL,valueR,spotturn)	
@webiopi.macro
def ButtonTurnRightOld():
	global motorSteerSpeed
	global motorDriveSpeed
	global speedstep

	steerRightAcc = 0
	steerRightAcc = getSteerMotorSpeedStep()

	setturnacceleration((steerRightAcc*-1))
	
	motorDriveSpeed, motorSteerSpeed = getMotorSpeed()
	
	# percent calculation
	valueDrive = float(motorSteerSpeed)/100
		
	GPIO.pulseRatio(motorSteerPWM, valueDrive)
	
	#print("RIGHT: ",valueL,valueR, spotturn)		

@webiopi.macro
def ButtonFlashAll():
	flashAll()

@webiopi.macro
def ButtonStop():	
	stop()
	flashAll()

def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)

    # set Trigger after 0.01ms to LOW
    sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    StartTime = time()
    StopTime = time()

    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time()

    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2

    return distance


def irstatus():
	irL = GPIO.input(irLPin)
	irC = GPIO.input(irCPin)
	irR = GPIO.input(irRPin)
	
	return irL, irC, irR

def shutdown():
	os.system('sudo halt')	


def detectMove():
	os.system('flite -voice awb -t "I see you"')
	
initiate()
