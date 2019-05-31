
 ##################################################
# RaceEssentials by Filip Topuzovic (Topuz)
#
# Version - v1.4.8
#
# Credits:
# Erwin Schmidt - Accurate delta calculation
# Jorge Alves - Inspiration and some app logic
# Rombik - Shared memory Sim Info code
# Minolin, Neys - Thanks for your contributions and inspiration to always do
# more and better
# Yachanay - TC/ABS/DRS performance optimization
#
# None of the code below is to be redistributed
# or reused without the permission of the
# author(s).
##################################################

##################################################
# Wally Masterson's changes
#
# Version 1.4.8
# - Show time left in a timed race.
#
# Version 1.4.7
# - Updated compounds.ini for Dallara F312 mod car.
#
# Version 1.4.6
# - Updated compounds.ini for AC 1.12.
#
# Version 1.4.5
# - added evil_overlord's use of compounds.ini from Topuz's Sidekick app.
#
# Version 1.4.4
# - fixed the Porsche 919 RPM bar not working
#
##################################################
import ac
import acsys
import sys
import os.path
import platform
import datetime
import pickle
import bisect
import configparser
import threading
import raceessentials_lib.win32con
import codecs
import json
import re
# 1.4.7
import traceback

if platform.architecture()[0] == "64bit":
	sysdir = os.path.dirname(__file__) + '/stdlib64'
else:
	sysdir = os.path.dirname(__file__) + '/stdlib'

sys.path.insert(0, sysdir)
os.environ['PATH'] = os.environ['PATH'] + ";."

import ctypes
from ctypes import wintypes

from raceessentials_lib.sim_info import info

updateConfig = False
#Test
configPath = "apps/python/RacingDash/config.ini"

config = configparser.ConfigParser()
config.read(configPath)

if config.has_section("RacingDash") != True:
	config.add_section("RacingDash")
	updateConfig = True
	
def getOrSetDefaultBoolean(config, key, default):
	global updateConfig
	try:
		return config.getboolean("RacingDash", key)
	except:
		config.set("RacingDash", key, str(default))
		updateConfig = True
		return default

def getOrSetDefaultFloat(config, key, default):
	global updateConfig
	try:
		return config.getfloat("RacingDash", key)
	except:
		config.set("RacingDash", key, str(default))
		updateConfig = True
		return default
	
scale = getOrSetDefaultFloat(config, "scale", 1)
speedInKPH = getOrSetDefaultBoolean(config, "speedInKPH", True)
backgroundOpacity = getOrSetDefaultFloat(config, "backgroundOpacity", 0.5)
showTyreWear = getOrSetDefaultBoolean(config, "showTyreWear", True)
tyreWearScale = getOrSetDefaultFloat(config, "tyreWearScale", 16.66)
deltaResolution = getOrSetDefaultFloat(config, "deltaResolution", 0.05)
updateDelta = getOrSetDefaultFloat(config, "updateDelta", 0.05)
centralGear = getOrSetDefaultBoolean(config, "centralGear", False)
startClearsValidity = getOrSetDefaultBoolean(config, "startClearsValidity", True)
orangeLimitEnabled = getOrSetDefaultBoolean(config, "orangeLimitEnabled", True)
orangeLimitPercentage = getOrSetDefaultFloat(config, "orangeLimitPercentage", 0.9)
redLimitEnabled = getOrSetDefaultBoolean(config, "redLimitEnabled", True)
redLimitPercentage = getOrSetDefaultFloat(config, "redLimitPercentage", 0.94)
maxPowerRpmLights = getOrSetDefaultBoolean(config, "maxPowerRpmLights", True)
orangeLimitPowerPercentage = getOrSetDefaultFloat(config, "orangeLimitPowerPercentage", 0.94)
redLimitPowerPercentage = getOrSetDefaultFloat(config, "redLimitPowerPercentage", 1)

if updateConfig:
	with open(configPath, 'w') as fileConfig:
		config.write(fileConfig)

centralOffset = 0
if centralGear:
	centralOffset = 312
		

###START GLOBAL VARIABLES

#Status helpers
oldStatusValue = 0
appActiveValue = 0

#Reset trigger
resetTrigger = 1

#Outlap helper
outLap = 0

#Pit check helper
carWasInPit = 0

#Timers
timerData = 1
timerDisplay = 0
timerDelay = 0

#Previous lap counter
previousLapValue = 0

#Fuel needed switcher
switcher = 0

#Needed because of references before assignments
rpmMaxValue = 0
trackGripValue = 0
tyreTemperatureValue = 0
tyrePressureValue = 0
tyreWearValue = 0
tyreCompoundValue = 0
tyreCompoundShort = 0
tyreCompoundCleaned = ""
previousTyreCompoundValue = 0
positionBoardValue = 0
positionValue = 0
totalCarsValue = 0
occupiedSlotsValue = 0
totalLapsValue = 0
sessionTimeValue = 0
sessionTypeValue = 0
systemClockValue = 0
fuelAmountValue = 0
airTemperatureValue = 0
roadTemperatureValue = 0
carInPitValue = 0
serverIPValue = 0
hasERS = 0
hasKERS = 0
turboPercentageValue = 0

personalBestLapValue = 0

compoundButtonValue = 0
pedalButtonValue = 0
flagValue = 0

rpmPercentageValue = 0
turboMaxValue = 0
lapValidityValue = 0
lastLapValue = 0
previousBestLapValue = 0
bestLapValue = 0
previousPersonalBestLapValue = 0
previousLastLapValue = 0
fuelStartValue = 0
fuelEndValue = 0
relevantLapsNumber = 0
fuelSpentValue = 0
fuelPerLapValue = 0

idealPressureFront = 0
idealPressureRear = 0
minimumOptimalTemperature = 0
maximumOptimalTemperature = 0

#Delta related
deltaTimer = 0
timer = 0
previousLapProgressValue = 0
posList = []
timeList = []
lastPosList = []
lastTimeList = []
bestPosList = []
bestTimeList = []
personalBestPosList = []
personalBestTimeList = []
deltaButtonValue = 0
prevt = 0
prevt2 = 0
ttb = 0
ttb_old = 0
ttpb = 0
ttpb_old = 0

#Max power rpm
maxPowerRpm = 0
maxPower = 0
maxPowerRpmPercentageValue = 0

#Cache variables
absOldValue = -1
tcOldValue = -1

#Listen key loop helper
listenKeyActive = True

###END GLOBAL VARIABLES

#Set file and folder locations
personalBestDir = "apps/python/RacingDash/personal_best/"
compoundsPath = "apps/python/RacingDash/compounds/"
configDir = "apps/python/RacingDash/config/"

template = "apps/python/RacingDash/images/template.png"
abson = "apps/python/RacingDash/images/abs.png"	
absoff = "apps/python/RacingDash/images/absoff.png"
tcon = "apps/python/RacingDash/images/tc.png"
tcoff = "apps/python/RacingDash/images/tcoff.png"
drs_available = "apps/python/RacingDash/images/drs_available.png"
drs_enabled = "apps/python/RacingDash/images/drs_enabled.png"
drs_off = "apps/python/RacingDash/images/drs_off.png"

def acMain(ac_version):
	global maxPowerRpmLights, maxPowerRpm, maxPower
	global appWindow, PossibleNewLaptimLable, gearLabel, speedLabel, TestLable, rpmLabel, turboLabel, kersChargeLabel, absLabel, tcLabel, drsLabel, currentLapLabel, trackGripLabel, lastLapLabel, bestLapLabel, personalBestLapLabel, tyreLabelWearFL, tyreLabelWearFR, tyreLabelWearRL, tyreLabelWearRR, tyreLabelTempFL, tyreLabelTempFR, tyreLabelTempRL, tyreLabelTempRR, tyreLabelPresFL, tyreLabelPresFR, tyreLabelPresRL, tyreLabelPresRR, tyreCompoundLabel, deltaLabel, positionLabel, lapLabel, sessionTimeLabel, systemClockLabel, fuelAmountLabel, fuelPerLapLabel, fuelForLapsLabel, fuelNeededLabel, temperatureLabel
	global carValue
	global filePersonalBest, personalBestLapValue
	global filePersonalBestPosList, filePersonalBestTimeList, personalBestPosList, personalBestTimeList
	global fileCompoundButton, compoundButtonValue
	global filePedalButton, pedalButtonValue
	global flagValue
	global fileDeltaButton, deltaButtonValue, deltaButton
	global fileAppActive, appActiveValue
	global compounds, modCompound
	global trackConfigValue
	
	#Create file names
	carValue = ac.getCarName(0)
	trackValue = ac.getTrackName(0)
	trackConfigValue = ac.getTrackConfiguration(0)

	filePersonalBest = personalBestDir + carValue + "_" + trackValue + trackConfigValue + "_pb.ini"
	filePersonalBestPosList = personalBestDir + carValue + "_" + trackValue + trackConfigValue + "_pbposlist.ini"
	filePersonalBestTimeList = personalBestDir + carValue + "_" + trackValue + trackConfigValue + "_pbtimelist.ini"
	fileCompoundButton = configDir + "compoundButton.ini"
	filePedalButton = configDir + "pedalButton.ini"
	fileDeltaButton = configDir + "deltaButton.ini"
	fileAppActive = configDir + "appActive.ini"

	#Load data from files
	personalBestLapValue = loadFile(filePersonalBest, personalBestLapValue)
	personalBestPosList = loadFile(filePersonalBestPosList, personalBestPosList)
	personalBestTimeList = loadFile(filePersonalBestTimeList, personalBestTimeList)
	compoundButtonValue = loadFile(fileCompoundButton, compoundButtonValue)
	pedalButtonValue = loadFile(filePedalButton, pedalButtonValue)
	deltaButtonValue = loadFile(fileDeltaButton, deltaButtonValue)
	appActiveValue = loadFile(fileAppActive, appActiveValue)
	
	#Figure out what is the max power rpm
	if maxPowerRpmLights:
		try:
			with codecs.open("content/cars/" + carValue + "/ui/ui_car.json", "r", "utf-8-sig") as uiFile:
				uiDataString = uiFile.read().replace('\r', '').replace('\n', '').replace('\t', '')
			uiDataJson = json.loads(uiDataString)
			for step in uiDataJson["powerCurve"]:
				if int(step[1]) >= maxPower:
					maxPower = int(step[1])
					maxPowerRpm = int(step[0])
		except:
			ac.console("RacingDash: UTF ui_car.json failed to load")
			try:
				with codecs.open("content/cars/" + carValue + "/ui/ui_car.json", "r", "latin-1") as uiFile:
					uiDataString = uiFile.read().replace('\r', '').replace('\n', '').replace('\t', '')
				uiDataJson = json.loads(uiDataString)
				for step in uiDataJson["powerCurve"]:
					if int(step[1]) >= maxPower:
						maxPower = int(step[1])
						maxPowerRpm = int(step[0])
			except:
				ac.console("RacingDash: ANSI ui_car.json failed to load")
				maxPowerRpmLights = False

	#Initialize font
	ac.initFont(0, "Consolas", 1, 1)
	
	#Initialize configparsers
	compounds = configparser.ConfigParser()
	compounds.read(compoundsPath + "compounds.ini")
	modCompound = configparser.ConfigParser()
	modCompound.read(compoundsPath + carValue + ".ini")
	
	#App window
	appWindow = ac.newApp("RacingDash")
	ac.setTitle(appWindow, "")
	ac.drawBorder(appWindow, 0)
	ac.setIconPosition(appWindow, 0, -10000)
	ac.setSize(appWindow, 704 * scale, 128 * scale)
	ac.setVisible(appWindow, appActiveValue)
	#ac.setBackgroundTexture(appWindow, template)

	###START CREATING LABELS
	
	#TestLable
	TestLable = ac.addLabel(appWindow, "Test")
	ac.setPosition(TestLable, 0 * scale, -20 * scale)
	ac.setFontSize(TestLable, 13 * scale)
	ac.setCustomFont(TestLable, "Consolas", 0, 1)

	#Gear
	gearLabel = ac.addLabel(appWindow, "-")
	ac.setPosition(gearLabel, (7 + centralOffset) * scale, -9 * scale)
	ac.setFontSize(gearLabel, 96 * scale)
	ac.setCustomFont(gearLabel, "Consolas", 0, 1)
	 
	#Speed
	speedLabel = ac.addLabel(appWindow, "---")
	ac.setPosition(speedLabel, (65 + centralOffset) * scale, 8 * scale)
	ac.setFontSize(speedLabel, 36 * scale)
	ac.setCustomFont(speedLabel, "Consolas", 0, 1)
	ac.setFontAlignment(speedLabel, "left")
	
	#RPM
	rpmLabel = ac.addLabel(appWindow, "---- rpm")
	ac.setPosition(rpmLabel, 140 * scale, 15 * scale)
	ac.setFontSize(rpmLabel, 13 * scale)
	ac.setCustomFont(rpmLabel, "Consolas", 0, 1)
	
	#Current lap
	currentLapLabel = ac.addLabel(appWindow, "-:--.---")
	ac.setPosition(currentLapLabel, 217 * scale, 6 * scale)
	ac.setFontSize(currentLapLabel, 24 * scale)
	ac.setCustomFont(currentLapLabel, "Consolas", 0, 1)
	
	#Last lap
	lastLapLabel = ac.addLabel(appWindow, "L: -:--.---")
	ac.setPosition(lastLapLabel, 217 * scale, 35 * scale)
	ac.setFontSize(lastLapLabel, 18 * scale)
	ac.setCustomFont(lastLapLabel, "Consolas", 0, 1)

	#Best lap
	bestLapLabel = ac.addLabel(appWindow, "B: -:--.---")
	ac.setPosition(bestLapLabel, 217 * scale, 55 * scale)
	ac.setFontSize(bestLapLabel, 18 * scale)
	ac.setCustomFont(bestLapLabel, "Consolas", 0, 1)  

	#Personal best lap
	personalBestLapLabel = ac.addLabel(appWindow, "P: -:--.---")
	ac.setPosition(personalBestLapLabel, 217 * scale, 75 * scale)
	ac.setFontSize(personalBestLapLabel, 18 * scale)
	ac.setCustomFont(personalBestLapLabel, "Consolas", 0, 1)
	
	#Tyre FL wear
	tyreLabelWearFL = ac.addLabel(appWindow, "")
	ac.setPosition(tyreLabelWearFL, (649 - centralOffset) * scale, 96 * scale)
	ac.setFontSize(tyreLabelWearFL, 15 * scale)
	ac.setCustomFont(tyreLabelWearFL, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelWearFL, "right")
	
	#Tyre FR wear
	tyreLabelWearFR = ac.addLabel(appWindow, "")
	ac.setPosition(tyreLabelWearFR, (679 - centralOffset) * scale, 96 * scale)
	ac.setFontSize(tyreLabelWearFR, 15 * scale)
	ac.setCustomFont(tyreLabelWearFR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelWearFR, "right")
	
	#Tyre RL wear
	tyreLabelWearRL = ac.addLabel(appWindow, "")
	ac.setPosition(tyreLabelWearRL, (649 - centralOffset) * scale, 111 * scale) 
	ac.setFontSize(tyreLabelWearRL, 15 * scale)
	ac.setCustomFont(tyreLabelWearRL, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelWearRL, "right")
	
	#Tyre RR wear
	tyreLabelWearRR = ac.addLabel(appWindow, "")
	ac.setPosition(tyreLabelWearRR, (679 - centralOffset) * scale, 111 * scale)
	ac.setFontSize(tyreLabelWearRR, 15 * scale)
	ac.setCustomFont(tyreLabelWearRR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelWearRR, "right")
	
	#Tyre FL temperature
	tyreLabelTempFL = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelTempFL, (649 - centralOffset) * scale, 10 * scale)
	ac.setFontSize(tyreLabelTempFL, 15 * scale)
	ac.setCustomFont(tyreLabelTempFL, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelTempFL, "right")
	
	#Tyre FR temperature
	tyreLabelTempFR = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelTempFR, (679 - centralOffset) * scale, 10 * scale)
	ac.setFontSize(tyreLabelTempFR, 15 * scale)
	ac.setCustomFont(tyreLabelTempFR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelTempFR, "right")
	
	#Tyre RL temperature
	tyreLabelTempRL = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelTempRL, (649 - centralOffset) * scale, 25 * scale)
	ac.setFontSize(tyreLabelTempRL, 15 * scale)
	ac.setCustomFont(tyreLabelTempRL, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelTempRL, "right")
	
	#Tyre RR temperature
	tyreLabelTempRR = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelTempRR, (679 - centralOffset) * scale, 25 * scale)
	ac.setFontSize(tyreLabelTempRR, 15 * scale)
	ac.setCustomFont(tyreLabelTempRR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelTempRR, "right")
	
	#Tyre FL pressure
	tyreLabelPresFL = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelPresFL, (649 - centralOffset) * scale, 53 * scale)
	ac.setFontSize(tyreLabelPresFL, 15 * scale)
	ac.setCustomFont(tyreLabelPresFL, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelPresFL, "right")
	
	#Tyre FR pressure
	tyreLabelPresFR = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelPresFR, (679 - centralOffset) * scale, 53 * scale)
	ac.setFontSize(tyreLabelPresFR, 15 * scale)
	ac.setCustomFont(tyreLabelPresFR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelPresFR, "right")
	
	#Tyre RL pressure
	tyreLabelPresRL = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelPresRL, (649 - centralOffset) * scale, 68 * scale)
	ac.setFontSize(tyreLabelPresRL, 15 * scale)
	ac.setCustomFont(tyreLabelPresRL, "Consolas", 0, 1) 
	ac.setFontAlignment(tyreLabelPresRL, "right")
	
	#Tyre RR pressure
	tyreLabelPresRR = ac.addLabel(appWindow, "--")
	ac.setPosition(tyreLabelPresRR, (679 - centralOffset) * scale, 68 * scale)
	ac.setFontSize(tyreLabelPresRR, 15 * scale)
	ac.setCustomFont(tyreLabelPresRR, "Consolas", 0, 1)
	ac.setFontAlignment(tyreLabelPresRR, "right")
	
    #DeltaButton
	deltaButton = ac.addButton(appWindow, "")
	ac.setPosition(deltaButton, 355 * scale, 39 * scale)
	ac.setSize(deltaButton, 93 * scale, 52 * scale)
	ac.setFontSize(deltaButton, 13 * scale)
	ac.setCustomFont(deltaButton, "Consolas", 0, 1)   
	ac.drawBorder(deltaButton, 0)
	ac.setBackgroundOpacity(deltaButton, 0)
	ac.addOnClickedListener(deltaButton, deltaButtonClicked)

	#Delta
	deltaLabel = ac.addLabel(appWindow, "--.--")
	ac.setPosition(deltaLabel, 399 * scale, 53 * scale)
	ac.setFontSize(deltaLabel, 24 * scale)
	ac.setCustomFont(deltaLabel, "Consolas", 0, 1)
	ac.setFontAlignment(deltaLabel, "center")
	
	#Position
	positionLabel = ac.addLabel(appWindow, "Pos: -/-")
	ac.setPosition(positionLabel, 11 * scale, 89 * scale)
	ac.setFontSize(positionLabel, 18 * scale)
	ac.setCustomFont(positionLabel, "Consolas", 0, 1)
	
	#Lap
	lapLabel = ac.addLabel(appWindow, "Lap: -/-")
	ac.setPosition(lapLabel, 11 * scale, 107 * scale)
	ac.setFontSize(lapLabel, 18 * scale)
	ac.setCustomFont(lapLabel, "Consolas", 0, 1)
	
    #System clock
	systemClockLabel = ac.addLabel(appWindow, "Time: --:--")
	ac.setPosition(systemClockLabel, 496 * scale, 6 * scale)
	ac.setFontSize(systemClockLabel, 13 * scale) 
	ac.setCustomFont(systemClockLabel, "Consolas", 0, 1)

	#Session time
	sessionTimeLabel = ac.addLabel(appWindow, "Rem: --:--")
	ac.setPosition(sessionTimeLabel, 503 * scale, 21 * scale)
	ac.setFontSize(sessionTimeLabel, 13 * scale)
	ac.setCustomFont(sessionTimeLabel, "Consolas", 0, 1)
	
	#Fuel amount
	fuelAmountLabel = ac.addLabel(appWindow, "--.- L")
	ac.setPosition(fuelAmountLabel, 517 * scale, 66 * scale)
	ac.setFontSize(fuelAmountLabel, 13 * scale)
	ac.setCustomFont(fuelAmountLabel, "Consolas", 0, 1)
	
	#Fuel per lap
	fuelPerLapLabel = ac.addLabel(appWindow, "Usage: --.-")
	ac.setPosition(fuelPerLapLabel, 494 * scale, 81 * scale)
	ac.setFontSize(fuelPerLapLabel, 13 * scale)
	ac.setCustomFont(fuelPerLapLabel, "Consolas", 0, 1)
	
	#Fuel for laps
	fuelForLapsLabel = ac.addLabel(appWindow, "Laps Left: --.-")
	ac.setPosition(fuelForLapsLabel, 467 * scale, 95 * scale)
	ac.setFontSize(fuelForLapsLabel, 13 * scale)
	ac.setCustomFont(fuelForLapsLabel, "Consolas", 0, 1)
	
	#Fuel needed
	fuelNeededLabel = ac.addLabel(appWindow, "Required: --.-")
	ac.setPosition(fuelNeededLabel, 473 * scale, 111 * scale)
	ac.setFontSize(fuelNeededLabel, 13 * scale)
	ac.setCustomFont(fuelNeededLabel, "Consolas", 0, 1)
	
	#Ambient temperature
	temperatureLabel = ac.addLabel(appWindow, "Tmp: --C/--C")
	ac.setPosition(temperatureLabel, 140 * scale, 97 * scale) 
	ac.setFontSize(temperatureLabel, 13 * scale)
	ac.setCustomFont(temperatureLabel, "Consolas", 0, 1)

	#Track grip
	trackGripLabel = ac.addLabel(appWindow, "Track: --%")
	ac.setPosition(trackGripLabel, 125 * scale, 111 * scale)
	ac.setFontSize(trackGripLabel, 13 * scale)
	ac.setCustomFont(trackGripLabel, "Consolas", 0, 1)

	#Tyre compound
	#tyreCompoundLabel = ac.addLabel(appWindow, "--")                 
	#ac.setPosition(tyreCompoundLabel, 105 * scale, 111 * scale)
	#ac.setFontSize(tyreCompoundLabel, 13 * scale)
	#ac.setCustomFont(tyreCompoundLabel, "Consolas", 0, 1)

    #Possible New Laptime
	PossibleNewLaptimLable = ac.addLabel(appWindow, "-:--.---")
	ac.setPosition(PossibleNewLaptimLable, 369 * scale, 93 * scale)
	ac.setFontSize(PossibleNewLaptimLable, 13 * scale)
	ac.setCustomFont(PossibleNewLaptimLable, "Consolas", 0, 1)

	#Compound-Button
	#compoundButton = ac.addButton(appWindow, "")
	#ac.setPosition(compoundButton, 583 * scale, 100 * scale)
	#ac.setSize(compoundButton, 120 * scale, 27 * scale)
	#ac.drawBorder(compoundButton, 0)
	#ac.setBackgroundOpacity(compoundButton, 0)
	#ac.addOnClickedListener(compoundButton, compoundButtonClicked)

    #PedalButton
	pedalButton = ac.addButton(appWindow, "")
	ac.setPosition(pedalButton, 142 * scale, 33 * scale)
	ac.setSize(pedalButton, 50 * scale, 40 * scale)
	ac.drawBorder(pedalButton, 0)
	ac.setBackgroundOpacity(pedalButton, 0)
	ac.addOnClickedListener(pedalButton, pedalButtonClicked)
    ###END CREATING LABELS
	
	###START CREATING BUTTONS
	
	
	###END CREATING BUTTONS
	
	#App visibility listeners
	ac.addOnAppActivatedListener(appWindow, appActivated)
	ac.addOnAppDismissedListener(appWindow, appDismissed)
	
	###START UPDATE LABELS WITH LOADED DATA
	
	#Personal best lap
	if personalBestLapValue > 0:
		personalBestLapValueSeconds = (personalBestLapValue / 1000) % 60
		personalBestLapValueMinutes = (personalBestLapValue // 1000) // 60
		ac.setText(personalBestLapLabel, "P: {:.0f}:{:06.3f}".format(personalBestLapValueMinutes, personalBestLapValueSeconds))
	
	#Delta
	if deltaButtonValue == 0:
		ac.setText(deltaButton, "Delta B:")
	elif deltaButtonValue == 1:
		ac.setText(deltaButton, "Delta P:")
	
	###END UPDATE LABELS WITH LOADED DATA
	
	#Render callback for drawing bars
	ac.addRenderCallback(appWindow, onFormRender)
	
	return "RacingDash"

def acUpdate(deltaT):
	global appWindow,PossibleNewLaptimLable,  gearLabel, speedLabel, rpmLabel, turboLabel, kersChargeLabel, absLabel, tcLabel, drsLabel, currentLapLabel, trackGripLabel, lastLapLabel, bestLapLabel, personalBestLapLabel, tyreLabelWearFL, tyreLabelWearFR, tyreLabelWearRL, tyreLabelWearRR, tyreLabelTempFL, tyreLabelTempFR, tyreLabelTempRL, tyreLabelTempRR, tyreLabelPresFL, tyreLabelPresFR, tyreLabelPresRL, tyreLabelPresRR, tyreCompoundLabel, deltaLabel, positionLabel, lapLabel, sessionTimeLabel, systemClockLabel, fuelAmountLabel, fuelPerLapLabel, fuelForLapsLabel, fuelNeededLabel, temperatureLabel
	global carValue
	global personalBestLapValue
	global personalBestPosList, personalBestTimeList
	global compoundButtonValue, pedalButtonValue
	global flagValue
	global trackConfigValue
	
	global oldStatusValue, resetTrigger, outLap, carWasInPit, timerData, timerDisplay, timerDelay, previousLapValue, switcher
	global deltaResolution, updateDelta, deltaTimer, timer, previousLapProgressValue, posList, timeList,lastPosList,lastTimeList, bestPosList, bestTimeList, prevt, prevt2, ttb, ttb_old, ttpb, ttpb_old
	global turboMaxValue, lapValidityValue, lastLapValue, previousBestLapValue, previousLastLapValue, bestLapValue, previousPersonalBestLapValue,previousLastLapValue,  fuelStartValue, fueEndValue, relevantLapsNumber, fuelSpentValue, fuelPerLapValue
	global compounds, modCompound, idealPressureFront, idealPressureRear, minimumOptimalTemperature, maximumOptimalTemperature

	global speedValueKPH, rpmPercentageValue, maxPowerRpmPercentageValue, turboPercentageValue, kersChargeValue, kersInputValue, tyreWearValue, slipRatioValue, ttpb, clutchValue, brakeValue, throttleValue, ffbValue, ersCurrentKJValue, ersMaxJValue
	global rpmMaxValue, trackGripValue, tyreTemperatureValue, tyrePressureValue, tyreWearValue, tyreCompoundValue, tyreCompoundShort, tyreCompoundCleaned, previousTyreCompoundValue, positionBoardValue, positionValue, totalCarsValue, occupiedSlotsValue, totalLapsValue, sessionTimeValue, sessionTypeValue, systemClockValue, fuelAmountValue, airTemperatureValue, roadTemperatureValue, carInPitValue, serverIPValue, hasERS, hasKERS
	
	global maxPowerRpmLights, maxPowerRpm
	global absOldValue, tcOldValue
	###START RUN THIS INDENTATION WITH EACH FRAME
	
	try:
		ac.setBackgroundOpacity(appWindow, backgroundOpacity)
		
		#Check if the game is replay mode
		statusValue = info.graphics.status
		
		if statusValue == 1:
			oldStatusValue = 1
			ac.setVisible(appWindow, 0)
		if statusValue != 1 and oldStatusValue and appActiveValue:
			oldStatusValue = 0
			ac.setVisible(appWindow, 1)
			
		if statusValue != 1:
			
			#Fetch data once per frame
			gearValue = ac.getCarState(0, acsys.CS.Gear)
			speedValueKPH = ac.getCarState(0, acsys.CS.SpeedKMH)
			speedValueMPH = ac.getCarState(0, acsys.CS.SpeedMPH)
			rpmValue = ac.getCarState(0, acsys.CS.RPM)
			turboValue = ac.getCarState(0, acsys.CS.TurboBoost)
			kersChargeValue = ac.getCarState(0, acsys.CS.KersCharge)
			kersInputValue = ac.getCarState(0, acsys.CS.KersInput)
			absValue = info.physics.abs
			tcValue = info.physics.tc
			drsAvailableValue = ac.getCarState(0, acsys.CS.DrsAvailable)
			drsEnabledValue = ac.getCarState(0, acsys.CS.DrsEnabled)
			currentLapValue = info.graphics.iCurrentTime
			tiresOutValue = info.physics.numberOfTyresOut
			slipRatioValue = ac.getCarState(0, acsys.CS.SlipRatio)
			lapValue = ac.getCarState(0, acsys.CS.LapCount)
			if trackConfigValue == "touristenfahrten":	#A dirty hack for Nordschleife Tourist
				lapProgressValue = (ac.getCarState(0, acsys.CS.NormalizedSplinePosition) + 0.0480) % 1
			else:
				lapProgressValue = ac.getCarState(0, acsys.CS.NormalizedSplinePosition)
			clutchValue = ac.getCarState(0, acsys.CS.Clutch)
			brakeValue = ac.getCarState(0, acsys.CS.Brake)
			throttleValue = ac.getCarState(0, acsys.CS.Gas)
			ffbValue = ac.getCarState(0, acsys.CS.LastFF)
			if hasERS or hasKERS:
				ersCurrentKJValue = ac.getCarState(0, acsys.CS.ERSCurrentKJ)
				ersMaxJValue = ac.getCarState(0, acsys.CS.ERSMaxJ)
				if carValue == "ks_ferrari_sf15t":
					ersMaxJValue = 4000000

			#Fetch data once per second
			timerData += deltaT
			
			if timerData > 1:
				timerData = 0
				
				if info.static.maxRpm:
					rpmMaxValue = info.static.maxRpm
				if info.static.maxTurboBoost > turboMaxValue:
					turboMaxValue = info.static.maxTurboBoost
				trackGripValue = info.graphics.surfaceGrip
				tyreTemperatureValue = ac.getCarState(0, acsys.CS.CurrentTyresCoreTemp)
				tyrePressureValue = ac.getCarState(0, acsys.CS.DynamicPressure)
				tyreWearValue = info.physics.tyreWear
				tyreCompoundValue = info.graphics.tyreCompound
				flagValue = info.graphics.flag
				tyreCompoundShort = tyreCompoundValue[tyreCompoundValue.find("(") + 1:tyreCompoundValue.find(")")]
				tyreCompoundCleaned = re.sub('\_+$', '', re.sub(r'[^\w]+', '_', tyreCompoundValue)).lower()
				positionBoardValue = ac.getCarLeaderboardPosition(0)
				positionValue = ac.getCarRealTimeLeaderboardPosition(0)
				totalCarsValue = ac.getCarsCount()
				occupiedSlotsValue = ac.getServerSlotsCount()
				totalLapsValue = info.graphics.numberOfLaps
				sessionTimeValue = info.graphics.sessionTimeLeft
				sessionTypeValue = info.graphics.session
				systemClockValue = datetime.datetime.now()
				fuelAmountValue = info.physics.fuel
				airTemperatureValue = info.physics.airTemp
				roadTemperatureValue = info.physics.roadTemp
				carInPitValue = ac.isCarInPitline(0)
				serverIPValue = ac.getServerIP()
				hasERS = info.static.hasERS
				hasKERS = info.static.hasKERS
				
			#Reset session check
			if resetTrigger == 1 and currentLapValue < 500 and lapValue == 0 and speedValueKPH < 1:
				resetTrigger = 0
				outLap = 1
				previousLapValue = 0
				lapValidityValue = 0
				ac.setFontColor(lastLapLabel, 1, 1, 1, 1)
				lastLapValue = 0
				previousLastLapValue = 0
				ac.setText(lastLapLabel, "L: -:--.---")
				previousBestLapValue = 0
				bestLapValue = 0
				ac.setText(bestLapLabel, "B: -:--.---")
				previousPersonalBestLapValue = 0
				relevantLapsNumber = 0
				fuelSpentValue = 0
				fuelPerLapValue = 0
				ac.setText(fuelPerLapLabel, "Usage: --.-")
				ac.setFontColor(deltaLabel, 1, 1, 1, 1)
				prevt = 0
				prevt2 = 0
				ac.setText(deltaLabel, "--.--")
				lastPosList = []
				lastTimeList = []
				bestPosList = []
				bestTimeList = []
			elif resetTrigger == 0 and currentLapValue > 500:
				resetTrigger = 1
			if (currentLapValue < 1000 and lapValue == 0 and (speedValueKPH > 10 or speedValueMPH > 10)) or sessionTypeValue == 2:
				outLap = 0
			
		
			###START DATA DISPLAY

			#Gear
			if gearValue == 0: 
				ac.setText(gearLabel, "R")
			elif gearValue == 1: 
				ac.setText(gearLabel, "N")
			else: 
				ac.setText(gearLabel, "{}".format(gearValue - 1))
			
			if rpmValue > rpmMaxValue:
				rpmMaxValue = rpmValue
			if rpmMaxValue:
				rpmPercentageValue = rpmValue / rpmMaxValue
			if rpmMaxValue and (not maxPowerRpmLights or maxPowerRpm >= rpmMaxValue):
				if orangeLimitEnabled and rpmPercentageValue > orangeLimitPercentage and rpmPercentageValue < redLimitPercentage:
					ac.setFontColor(gearLabel, 1, 0.46, 0.18, 1)
				elif redLimitEnabled and rpmPercentageValue >= redLimitPercentage:
					ac.setFontColor(gearLabel, 1, 0.18, 0.18, 1)
				else:
					ac.setFontColor(gearLabel, 1, 1, 1, 1)
			elif maxPowerRpm and maxPowerRpm < rpmMaxValue and maxPowerRpmLights:
				maxPowerRpmPercentageValue = rpmValue / maxPowerRpm
				if orangeLimitEnabled and maxPowerRpmPercentageValue > orangeLimitPowerPercentage and maxPowerRpmPercentageValue < redLimitPowerPercentage:
					ac.setFontColor(gearLabel, 1, 0.46, 0.18, 1)
				elif redLimitEnabled and maxPowerRpmPercentageValue >= redLimitPowerPercentage:
					ac.setFontColor(gearLabel, 1, 0.18, 0.18, 1)
				else:
					ac.setFontColor(gearLabel, 1, 1, 1, 1)
				
			#Speed
			if speedInKPH:
				ac.setText(speedLabel, "{:.0f}".format(speedValueKPH))
			else:
				ac.setText(speedLabel, "{:.0f}".format(speedValueMPH))
				
			#RPM
			ac.setText(rpmLabel, "RPM: {:.0f}".format(rpmValue))
		
			#Current lap
			currentLapValueSeconds = (currentLapValue / 1000) % 60
			currentLapValueMinutes = (currentLapValue // 1000) // 60
			ac.setText(currentLapLabel, "{:.0f}:{:06.3f}".format(currentLapValueMinutes, currentLapValueSeconds))
			
			#Lap validity
			if tiresOutValue > 2 or carWasInPit:
				lapValidityValue = 1
			if lapValidityValue:
				ac.setFontColor(currentLapLabel, 1, 0.18, 0.18, 1)
			else:
				ac.setFontColor(currentLapLabel, 1, 1, 1, 1)
				
			#Tyre compound
			#if compoundButtonValue:
			#	ac.setText(tyreCompoundLabel, "{}: {}C-{}C".format(tyreCompoundShort, minimumOptimalTemperature, maximumOptimalTemperature))
			#else:
			#	ac.setText(tyreCompoundLabel, "{}: {}psi/{}psi".format(tyreCompoundShort, idealPressureFront, idealPressureRear))
			
			#Delta
			deltaTimer += deltaT
			timer += deltaT
			
			if deltaTimer > deltaResolution:
				deltaTimer = 0
				if lapProgressValue > previousLapProgressValue and lapProgressValue < 1:
					timeList.append(currentLapValue)
					posList.append(lapProgressValue)
				previousLapProgressValue = lapProgressValue
			
			if timer > updateDelta and currentLapValue > 4000 and lapProgressValue > 0.005 and lapProgressValue < 0.995 and carWasInPit == 0:
				timer = 0
				if bestLapValue and deltaButtonValue == 0:
					i = bisect.bisect_right(bestPosList, lapProgressValue) - 1
					c = (bestTimeList[i + 1] - bestTimeList[i]) / (bestPosList[i + 1] - bestPosList[i])
					interpolatedLapValue = bestTimeList[i] + c * (lapProgressValue - bestPosList[i])
					t = (currentLapValue - interpolatedLapValue) / 1000
			
					if t == 0:
						ac.setText(deltaLabel, "--.--")
						ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					elif t > 0:
						ac.setText(deltaLabel, "{:+.2f}".format(t))
						ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setText(deltaLabel, "{:+.2f}".format(t))
						ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)
						
					if prevt2:
						ttb_old = ttb
						ttb = 2 * t - prevt - prevt2
					
					prevt2 = float(prevt)
					prevt = float(t)
				
				elif bestLapValue == 0 and deltaButtonValue == 0:
					ac.setText(deltaLabel, "--.--")
					ac.setFontColor(deltaLabel, 1, 1, 1, 1)
				
				if personalBestLapValue and deltaButtonValue == 1 and outLap != 1:
					i = bisect.bisect_right(personalBestPosList, lapProgressValue) - 1
					c = (personalBestTimeList[i + 1] - personalBestTimeList[i]) / (personalBestPosList[i + 1] - personalBestPosList[i])
					interpolatedLapValue = personalBestTimeList[i] + c * (lapProgressValue - personalBestPosList[i])
					t = (currentLapValue - interpolatedLapValue) / 1000
			
					if t == 0:
						ac.setText(deltaLabel, "--.--")
						ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					elif t > 0:
						ac.setText(deltaLabel, "{:+.2f}".format(t))
						ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setText(deltaLabel, "{:+.2f}".format(t))
						ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)
						
					if prevt2:
						ttpb_old = ttpb
						ttpb = 2 * t - prevt - prevt2
					
					prevt2 = float(prevt)
					prevt = float(t)
						
				elif personalBestLapValue == 0 and deltaButtonValue == 1:
					ac.setText(deltaLabel, "--.--")
					ac.setFontColor(deltaLabel, 1, 1, 1, 1)
				
				if lastLapValue and deltaButtonValue == 2:
				    i = bisect.bisect_right(lastPosList, lapProgressValue) - 1
				    c = (lastTimeList[i + 1] - lastTimeList[i]) / (lastPosList[i + 1] - lastPosList[i])
				    interpolatedLapValue = lastTimeList[i] + c * (lapProgressValue - lastPosList[i])
				    t = (currentLapValue - interpolatedLapValue) / 1000
			
				    #if t == 0:
						#ac.setText(deltaLabel, "--.--")
						#ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					#elif t > 0:
						#ac.setText(deltaLabel, "{:+.2f}".format(t))
						#ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
				    #else:
						#ac.setText(deltaLabel, "{:+.2f}".format(t))
						#ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)

				    #if prevt2:
					    #ttb_old = ttb
					    #ttb = 2 * t - prevt - prevt2

				    #prevt2 = float(prevt)
				    #prevt = float(t)

				elif lastLapValue == 0 and deltaButtonValue == 2:
				    ac.setText(deltaLabel, "--.--")
				    ac.setFontColor(deltaLabel, 1, 1, 1, 1)
			
			elif timer > updateDelta and currentLapValue > 4000 and carWasInPit:
				timer = 0
				ac.setText(deltaLabel, "--.--")
				ac.setFontColor(deltaLabel, 1, 1, 1, 1)
				
			elif timer > updateDelta and currentLapValue > 1000 and currentLapValue < 4000 and timerDelay == 0:
				timer = 0
				
				if bestLapValue and deltaButtonValue == 0 and lapValue > 1:
					if previousBestLapValue and previousBestLapValue > bestLapValue:
						t = (lastLapValue - previousBestLapValue) / 1000
					else:
						t = (lastLapValue - bestLapValue) / 1000
					if t == 0:
						ac.setText(deltaLabel, "--.--")
						ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					elif t > 0:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)
					
				if personalBestLapValue and deltaButtonValue == 1 and lapValue > 0:
					if previousPersonalBestLapValue and previousPersonalBestLapValue > personalBestLapValue:
						t = (lastLapValue - previousPersonalBestLapValue) / 1000
					else:
						t = (lastLapValue - personalBestLapValue) / 1000
					if t == 0:
						ac.setText(deltaLabel, "--.--")
						ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					elif t > 0:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)

				if lastBestLapValue and deltaButtonValue == 2 and lapValue > 0:
					if previousLastLapValue and previousLastLapValue > lastBestLapValue:
						t = (lastLapValue - previousLastLapValue) / 1000
					else:
						t = (lastLapValue - lastLapValue) / 1000
					if t == 0:
						ac.setText(deltaLabel, "--.--")
						ac.setFontColor(deltaLabel, 1, 1, 1, 1)
					elif t > 0:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setText(deltaLabel, "{:+.3f}".format(t))
						ac.setFontColor(deltaLabel, 0.18, 1, 0.18, 1)
			
		
			

			#Possible New Laptime
			if bestLapValue and deltaButtonValue == 0 and lapValue > 0:
				PossibleNewPersonalBestLap = bestLapValue + (prevt * 1000)
				PossibleNewLaptimSeconds = ((PossibleNewPersonalBestLap / 1000) % 60) 
				PossibleNewLaptimMinutes = ((PossibleNewPersonalBestLap // 1000) // 60)
				ac.setText(PossibleNewLaptimLable, "{:.0f}:{:06.3f}".format(PossibleNewLaptimMinutes, PossibleNewLaptimSeconds))

			if personalBestLapValue and deltaButtonValue == 1 and lapValue > 0:
				PossibleNewPersonalBestLap = personalBestLapValue + (prevt * 1000)
				PossibleNewLaptimSeconds = ((PossibleNewPersonalBestLap / 1000) % 60) 
				PossibleNewLaptimMinutes = ((PossibleNewPersonalBestLap // 1000) // 60)
				ac.setText(PossibleNewLaptimLable, "{:.0f}:{:06.3f}".format(PossibleNewLaptimMinutes, PossibleNewLaptimSeconds))


			#Display data once per second
			timerDisplay += deltaT
			
			if timerDisplay > 1:
				timerDisplay = 0

				#Reset previous laps helper
				if currentLapValue > 4000 and (previousBestLapValue > 0 or previousPersonalBestLapValue > 0 or previousLastLapValue > 0):
					previousBestLapValue = 0
					previousPersonalBestLapValue = 0
					previousLastLapValue = 0
					
				#Car in pit check
				if carInPitValue:
					carWasInPit = 1
				
				#Set ideal tyre temperatures and pressures
				if previousTyreCompoundValue != tyreCompoundValue:
					previousTyreCompoundValue = tyreCompoundValue
					compounds.read(compoundsPath)
					
					
					if compounds.has_section(carValue + "_" + tyreCompoundShort.lower()):
						idealPressureFront = int(compounds.get(carValue + "_" + tyreCompoundCleaned, "IDEAL_PRESSURE_F"))
						idealPressureRear = int(compounds.get(carValue + "_" + tyreCompoundCleaned, "IDEAL_PRESSURE_R"))
						minimumOptimalTemperature = int(compounds.get(carValue + "_" + tyreCompoundCleaned, "MIN_OPTIMAL_TEMP"))
						maximumOptimalTemperature = int(compounds.get(carValue + "_" + tyreCompoundCleaned, "MAX_OPTIMAL_TEMP"))
						
					elif modCompound.has_section(carValue + "_" + tyreCompoundShort.lower()):
						idealPressureFront = int(modCompound.get(carValue + "_" + tyreCompoundCleaned, "IDEAL_PRESSURE_F"))
						idealPressureRear = int(modCompound.get(carValue + "_" + tyreCompoundCleaned, "IDEAL_PRESSURE_R"))
						minimumOptimalTemperature = int(modCompound.get(carValue + "_" + tyreCompoundCleaned, "MIN_OPTIMAL_TEMP"))
						maximumOptimalTemperature = int(modCompound.get(carValue + "_" + tyreCompoundCleaned, "MAX_OPTIMAL_TEMP"))
				
				

				#Track grip
				ac.setText(trackGripLabel, "Track: {:.1f}%".format(trackGripValue * 100))
				
				#Tyre wear
				if showTyreWear:
					ac.setText(tyreLabelWearFL, "Wear:{:.0f}".format(max(100 - (100 - tyreWearValue[0]) * tyreWearScale, 0)))
					ac.setText(tyreLabelWearFR, "{:.0f}".format(max(100 - (100 - tyreWearValue[1]) * tyreWearScale, 0)))
					ac.setText(tyreLabelWearRL, "{:.0f}".format(max(100 - (100 - tyreWearValue[2]) * tyreWearScale, 0)))
					ac.setText(tyreLabelWearRR, "{:.0f}".format(max(100 - (100 - tyreWearValue[3]) * tyreWearScale, 0)))
					
				#Tyre temperatures
				ac.setText(tyreLabelTempFL, "Temp:{:.0f}".format(tyreTemperatureValue[0]))
				if minimumOptimalTemperature and maximumOptimalTemperature:
					if int(round(tyreTemperatureValue[0])) >= minimumOptimalTemperature and int(round(tyreTemperatureValue[0])) <= maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFL, 0.18, 1, 0.18, 1)
					elif int(round(tyreTemperatureValue[0])) < minimumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFL, 0.18, 0.92, 1, 1)
					elif int(round(tyreTemperatureValue[0])) > maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFL, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelTempFR, "{:.0f}".format(tyreTemperatureValue[1]))
				if minimumOptimalTemperature and maximumOptimalTemperature:
					if int(round(tyreTemperatureValue[1])) >= minimumOptimalTemperature and int(round(tyreTemperatureValue[1])) <= maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFR, 0.18, 1, 0.18, 1)
					elif int(round(tyreTemperatureValue[1])) < minimumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFR, 0.18, 0.92, 1, 1)
					elif int(round(tyreTemperatureValue[1])) > maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempFR, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelTempRL, "{:.0f}".format(tyreTemperatureValue[2]))
				if minimumOptimalTemperature and maximumOptimalTemperature:
					if int(round(tyreTemperatureValue[2])) >= minimumOptimalTemperature and int(round(tyreTemperatureValue[2])) <= maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRL, 0.18, 1, 0.18, 1)
					elif int(round(tyreTemperatureValue[2])) < minimumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRL, 0.18, 0.92, 1, 1)
					elif int(round(tyreTemperatureValue[2])) > maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRL, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelTempRR, "{:.0f}".format(tyreTemperatureValue[3]))
				if minimumOptimalTemperature and maximumOptimalTemperature:
					if int(round(tyreTemperatureValue[3])) >= minimumOptimalTemperature and int(round(tyreTemperatureValue[3])) <= maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRR, 0.18, 1, 0.18, 1)
					elif int(round(tyreTemperatureValue[3])) < minimumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRR, 0.18, 0.92, 1, 1)
					elif int(round(tyreTemperatureValue[3])) > maximumOptimalTemperature:
						ac.setFontColor(tyreLabelTempRR, 1, 0.18, 0.18, 1)
				
				#Tyre pressures
				ac.setText(tyreLabelPresFL, "Press:{:.0f}".format(tyrePressureValue[0]))
				if idealPressureFront and idealPressureRear:
					if idealPressureFront == int(round(tyrePressureValue[0])):
						ac.setFontColor(tyreLabelPresFL, 0.18, 1, 0.18, 1)
					elif int(round(tyrePressureValue[0])) < idealPressureFront:
						ac.setFontColor(tyreLabelPresFL, 0.18, 0.92, 1, 1)
					elif int(round(tyrePressureValue[0])) > idealPressureFront:
						ac.setFontColor(tyreLabelPresFL, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelPresFR, "{:.0f}".format(tyrePressureValue[1]))
				if idealPressureFront and idealPressureRear:
					if idealPressureFront == int(round(tyrePressureValue[1])):
						ac.setFontColor(tyreLabelPresFR, 0.18, 1, 0.18, 1)
					elif int(round(tyrePressureValue[1])) < idealPressureFront:
						ac.setFontColor(tyreLabelPresFR, 0.18, 0.92, 1, 1)
					elif int(round(tyrePressureValue[1])) > idealPressureFront:
						ac.setFontColor(tyreLabelPresFR, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelPresRL, "{:.0f}".format(tyrePressureValue[2]))
				if idealPressureFront and idealPressureRear:
					if idealPressureRear == int(round(tyrePressureValue[2])):
						ac.setFontColor(tyreLabelPresRL, 0.18, 1, 0.18, 1)
					elif int(round(tyrePressureValue[2])) < idealPressureRear:
						ac.setFontColor(tyreLabelPresRL, 0.18, 0.92, 1, 1)
					elif int(round(tyrePressureValue[2])) > idealPressureRear:
						ac.setFontColor(tyreLabelPresRL, 1, 0.18, 0.18, 1)
				
				ac.setText(tyreLabelPresRR, "{:.0f}".format(tyrePressureValue[3]))
				if idealPressureFront and idealPressureRear:
					if idealPressureRear == int(round(tyrePressureValue[3])):
						ac.setFontColor(tyreLabelPresRR, 0.18, 1, 0.18, 1)
					elif int(round(tyrePressureValue[3])) < idealPressureRear:
						ac.setFontColor(tyreLabelPresRR, 0.18, 0.92, 1, 1)
					elif int(round(tyrePressureValue[3])) > idealPressureRear:
						ac.setFontColor(tyreLabelPresRR, 1, 0.18, 0.18, 1)
				
				#Lap
				if totalLapsValue:
					if lapValue == totalLapsValue:
						ac.setText(lapLabel, "Lap: {}/{}".format(totalLapsValue, totalLapsValue))
					elif lapValue < totalLapsValue:
						ac.setText(lapLabel, "Lap: {}/{}".format(lapValue + 1, totalLapsValue))
				else:
					ac.setText(lapLabel, "Lap: {}/-".format(lapValue + 1))
				
				#Position
				if sessionTypeValue == 3:
					ac.setText(positionLabel, "Pos: -/-")
				elif sessionTypeValue == 2:
					if serverIPValue:
						ac.setText(positionLabel, "Pos: {}/{}".format(positionValue + 1, occupiedSlotsValue))
					else:
						ac.setText(positionLabel, "Pos: {}/{}".format(positionValue + 1, totalCarsValue))
				else:
					if serverIPValue:
						ac.setText(positionLabel, "Pos: {}/{}".format(positionBoardValue, occupiedSlotsValue))
					else:
						ac.setText(positionLabel, "Pos: {}/{}".format(positionBoardValue, totalCarsValue))
					
				#Session time
				sessionTimeValueSeconds = (sessionTimeValue / 1000) % 60
				sessionTimeValueMinutes = (sessionTimeValue // 1000) // 60
				if (sessionTypeValue == 2 and info.static.isTimedRace == 0) or sessionTypeValue > 2 or sessionTimeValue < 0:
					ac.setFontColor(sessionTimeLabel, 1, 1, 1, 1)
					ac.setText(sessionTimeLabel, "Rem: --:--")
				else:
					if sessionTimeValueMinutes < 5:
						ac.setFontColor(sessionTimeLabel, 1, 0.18, 0.18, 1)
						ac.setText(sessionTimeLabel, "Rem: {:02.0f}:{:02.0f}".format(sessionTimeValueMinutes, sessionTimeValueSeconds))
					elif sessionTimeValueMinutes >= 60:
						ac.setFontColor(sessionTimeLabel, 1, 1, 1, 1)
						ac.setText(sessionTimeLabel, "Rem: >1h")
					else:
						ac.setFontColor(sessionTimeLabel, 1, 1, 1, 1)
						ac.setText(sessionTimeLabel, "Rem: {:02.0f}:{:02.0f}".format(sessionTimeValueMinutes, sessionTimeValueSeconds))
					
				#System clock
				ac.setText(systemClockLabel, "Time: {:02.0f}:{:02.0f}".format(systemClockValue.hour, systemClockValue.minute))
				
				#Fuel amount
				ac.setText(fuelAmountLabel, "{:.1f} L".format(fuelAmountValue))
				
				#Fuel for laps
				if fuelPerLapValue:
					LapsLeft = fuelAmountValue / fuelPerLapValue
					if LapsLeft < 2:
						ac.setFontColor(fuelForLapsLabel, 1, 0.18, 0.18, 1)
						ac.setText(fuelForLapsLabel, "Laps Left: {:.1f}".format(LapsLeft))
					else:
						ac.setFontColor(fuelForLapsLabel, 1, 1, 1, 1)
						ac.setText(fuelForLapsLabel, "Laps Left: {:.1f}".format(LapsLeft))
				else:
					ac.setText(fuelForLapsLabel, "Laps Left: --.-")
					
				#Fuel needed
				if lapValue > 0 and sessionTypeValue == 2:
					fuelNeededValue = (totalLapsValue - lapValue - lapProgressValue) * fuelPerLapValue
					if fuelAmountValue < fuelNeededValue and switcher:
						ac.setFontColor(fuelNeededLabel, 1, 0.18, 0.18, 1)
						ac.setText(fuelNeededLabel, "Required: {:.1f}".format(fuelNeededValue))
						switcher = 0
					elif fuelAmountValue < fuelNeededValue and not switcher:
						ac.setFontColor(fuelNeededLabel, 1, 0.18, 0.18, 1)
						ac.setText(fuelNeededLabel, "Required: {:.1f}".format(fuelNeededValue - fuelAmountValue))
						switcher = 1
					else:
						ac.setFontColor(fuelNeededLabel, 1, 1, 1, 1)
						ac.setText(fuelNeededLabel, "Required: {:.1f}".format(fuelNeededValue))
				else:
					ac.setFontColor(fuelNeededLabel, 1, 1, 1, 1)
					ac.setText(fuelNeededLabel, "Required: --.-")
					
				#Ambient temperature
				ac.setText(temperatureLabel, "Tmp: {:.0f}C/{:.0f}C".format(airTemperatureValue, roadTemperatureValue))

			#Display data once per lap
			
			#Run on lap start
			if currentLapValue > 500 and currentLapValue < 1000:
				carWasInPit = 0
				fuelStartValue = fuelAmountValue
				timeList = []
				posList = []
				prevt = 0
				prevt2 = 0
				ttb = 0
				ttpb = 0
				if startClearsValidity:
					lapValidityValue = 0

			#Run on lap finish
			if previousLapValue < lapValue:
				timerDelay += deltaT
				
				#Reset helpers
				outLap = 0	#Just in case the first condition misfired
						
				if timerDelay > 0.46:
					timerDelay = 0
					previousLapValue = lapValue

					#Last lap
					lastLapValue = info.graphics.iLastTime
					previousLastLapValue = lastLapValue
					lastLapValueSeconds = (lastLapValue / 1000) % 60
					lastLapValueMinutes = (lastLapValue // 1000) // 60
					if lapValidityValue:
						ac.setFontColor(lastLapLabel, 1, 0.18, 0.18, 1)
					else:
						ac.setFontColor(lastLapLabel, 1, 1, 1, 1)
						ac.setText(lastLapLabel, "L: {:.0f}:{:06.3f}".format(lastLapValueMinutes, lastLapValueSeconds))
						lastPosList = list(posList)#LastLapChange
						lastTimeList = list(timeList)#LastLapChange

					#Best lap
					if lapValidityValue != 1:
						previousBestLapValue = bestLapValue
						if not bestLapValue:
							bestLapValue = lastLapValue
						if lastLapValue < bestLapValue:
							bestLapValue = lastLapValue
						bestLapValueSeconds = (bestLapValue / 1000) % 60
						bestLapValueMinutes = (bestLapValue // 1000) // 60
						ac.setText(bestLapLabel, "B: {:.0f}:{:06.3f}".format(bestLapValueMinutes, bestLapValueSeconds))
						if bestLapValue < previousBestLapValue or previousBestLapValue == 0:
							bestPosList = list(posList)
							bestTimeList = list(timeList)

					#Personal best lap
					if (bestLapValue < personalBestLapValue or personalBestLapValue == 0) and bestLapValue:
						previousPersonalBestLapValue = personalBestLapValue
						personalBestLapValue = bestLapValue
						personalBestLapValueSeconds = (personalBestLapValue / 1000) % 60
						personalBestLapValueMinutes = (personalBestLapValue // 1000) // 60
						ac.setText(personalBestLapLabel, "P: {:.0f}:{:06.3f}".format(personalBestLapValueMinutes, personalBestLapValueSeconds))
						personalBestPosList = list(posList)
						personalBestTimeList = list(timeList)
						


					#Fuel per lap
					if fuelAmountValue < fuelStartValue and not carWasInPit:
						fuelEndValue = fuelAmountValue
						relevantLapsNumber += 1
						fuelSpentValue += (fuelStartValue - fuelEndValue) + (fuelStartValue - fuelEndValue) * (540 / lastLapValue)
						fuelPerLapValue = fuelSpentValue / relevantLapsNumber
						ac.setText(fuelPerLapLabel, "Usage: {:.1f}".format(fuelPerLapValue))
						
					#Reset helper
					lapValidityValue = 0
			
			###END DATA DISPLAY
			
			###END RUN THIS INDENTATION WITH EVERY FRAME
	except:
		ac.log(traceback.format_exc())
	
#Draw bars
def onFormRender(deltaT):
	global ffbValue
	
	#RPM
	ac.glColor4f(1, 1, 1, 0.3)
	ac.glQuad(10 * scale, 7 * scale, 196 * scale, 6 * scale)
	if not maxPowerRpmLights or maxPowerRpm >= rpmMaxValue:
		if orangeLimitEnabled and rpmPercentageValue > orangeLimitPercentage and rpmPercentageValue < redLimitPercentage:
			ac.glColor4f(1, 0.46, 0.18, 1)
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)
		elif redLimitEnabled and rpmPercentageValue >= redLimitPercentage:
			ac.glColor4f(1, 0.18, 0.18, 1)
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)
		else:
			ac.glColor4f(1, 1, 1, 1)
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)
	elif maxPowerRpmLights and maxPowerRpm < rpmMaxValue:
		if orangeLimitEnabled and maxPowerRpmPercentageValue > orangeLimitPowerPercentage and maxPowerRpmPercentageValue < redLimitPowerPercentage:
			ac.glColor4f(1, 0.46, 0.18, 1)
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)
		elif redLimitEnabled and maxPowerRpmPercentageValue >= redLimitPowerPercentage:
			ac.glColor4f(1, 0.18, 0.18, 1)
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)
		else:
			ac.glColor4f(1, 1, 1, 1) 
			ac.glQuad(10 * scale, 7 * scale, (rpmPercentageValue * 196) * scale, 6 * scale)

	
	#Delta gain bar
	ac.glColor4f(1, 1, 1, 0.3)
	ac.glQuad(352 * scale, 83 * scale, 100 * scale, 6 * scale)
	if deltaButtonValue:
		if ttpb > 0:
			ac.glColor4f(1, 0.18, 0.18, 1)
			deltaOffset = min(ttpb * 1000, 50)
			ac.glQuad((402 - deltaOffset) * scale, 83 * scale, deltaOffset * scale, 6 * scale)
		if ttpb < 0:
			ac.glColor4f(0.18, 1, 0.18, 1)
			deltaOffset = min(abs(ttpb * 1000), 50)
			ac.glQuad(402 * scale, 83 * scale, deltaOffset * scale, 6 * scale)
	else:
		if ttb > 0:
			ac.glColor4f(1, 0.18, 0.18, 1)
			deltaOffset = min(ttb * 1000, 50)
			ac.glQuad((402 - deltaOffset) * scale, 83 * scale, deltaOffset * scale, 6 * scale)
		if ttb < 0:
			ac.glColor4f(0.18, 1, 0.18, 1)
			deltaOffset = min(abs(ttb * 1000), 50)
			ac.glQuad(402 * scale, 83 * scale, deltaOffset * scale, 6 * scale)

    #Clutch
	if pedalButtonValue == 1:
		ac.glColor4f(1, 1, 1, 0.3)
		ac.glQuad(142 * scale, 33 * scale, 14 * scale, 14 * scale)
		if clutchValue < 1:
			ac.glColor4f(0.18, 0.46, 1, 1)
			ac.glQuad(142 * scale, 33 * scale, 14 * scale, 14 * scale)
	elif pedalButtonValue == 2:
			ac.glColor4f(1, 1, 1, 0.3)
			ac.glQuad(142 * scale, 33 * scale, 14 * scale, 40 * scale)
			ac.glColor4f(0.18, 0.46, 1, 1)
			ac.glQuad(142 * scale, ((1 - (1 - clutchValue)) * 40 + 33) * scale, 14 * scale, ((1 - clutchValue) * 40) * scale)
	
	#Brake
	if pedalButtonValue == 1:
		ac.glColor4f(1, 1, 1, 0.3)
		ac.glQuad(160 * scale, 33 * scale, 14 * scale, 14 * scale)
		if brakeValue >= 0.01:
			ac.glColor4f(1, 0.18, 0.18, 1)
			ac.glQuad(160 * scale, 33 * scale, 14 * scale, 14 * scale)
	elif pedalButtonValue == 2:
		ac.glColor4f(1, 1, 1, 0.3)
		ac.glQuad(160 * scale, 33 * scale, 14 * scale, 40 * scale)
		ac.glColor4f(1, 0.18, 0.18, 1)
		ac.glQuad(160 * scale, ((1 - brakeValue) * 40 + 33) * scale, 14 * scale, (brakeValue * 40) * scale)

	#Throttle
	if pedalButtonValue == 1:
		ac.glColor4f(1, 1, 1, 0.3)
		ac.glQuad(178 * scale, 33 * scale, 14 * scale, 14 * scale)
		if throttleValue >= 0.01:
			ac.glColor4f(0.18, 1, 0.18, 1)
			ac.glQuad(178 * scale, 33 * scale, 14 * scale, 14 * scale)
	elif pedalButtonValue == 2:
		ac.glColor4f(1, 1, 1, 0.3)
		ac.glQuad(178 * scale, 33 * scale, 14 * scale, 40 * scale)
		ac.glColor4f(0.18, 1, 0.18, 1)
		ac.glQuad(178 * scale, ((1 - throttleValue) * 40 + 33) * scale, 14 * scale, (throttleValue * 40) * scale)

    #Flags
	ac.glColor4f(1, 1, 1, 0.3)
	ac.glQuad(360 * scale, 3 * scale, 77 * scale, 14 * scale)
	ac.glColor4f(1, 1, 1, 0.3)
	ac.glQuad(360 * scale, 20 * scale, 77 * scale, 14 * scale)
	
	#Yellow
	if flagValue == 2:
		ac.glColor4f(1, 1, 0, 1)
		ac.glQuad(360 * scale, 3 * scale, 77 * scale, 14 * scale)
	
	#Blue
	if flagValue == 1:
		ac.glColor4f(0.18, 0.46, 1, 1)
		ac.glQuad(360 * scale, 20 * scale, 77 * scale, 14 * scale)

	
#Do on AC shutdown
def acShutdown():
	global personalBestDir, configDir
	global filePersonalBest, personalBestLapValue
	global filePersonalBestPosList, personalBestPosList
	global filePersonalBestTimeList, personalBestTimeList
	global fileCompoundButton, compoundButtonValue
	global filePedalButton, pedalButtonValue
	global fileDeltaButton, deltaButtonValue
	global fileAppActive, appActiveValue
	
	writeFile(filePersonalBest, personalBestLapValue, personalBestDir)
	writeFile(filePersonalBestPosList, personalBestPosList, personalBestDir)
	writeFile(filePersonalBestTimeList, personalBestTimeList, personalBestDir)
	writeFile(fileCompoundButton, compoundButtonValue, configDir)
	writeFile(filePedalButton, pedalButtonValue, configDir)
	writeFile(fileDeltaButton, deltaButtonValue, configDir)
	writeFile(fileAppActive, appActiveValue, configDir)
	
#Button actions
def deltaButtonClicked(*args):
	global deltaButtonValue, deltaButton
	global ttb, ttpb
	
	if deltaButtonValue == 1:
		deltaButtonValue = 0
		ac.setText(deltaButton, "Delta B:")
		ttb = 0
	
	elif deltaButtonValue == 0:
		deltaButtonValue = 1
		ac.setText(deltaButton, "Delta P:")
		ttpb = 0


#def compoundButtonClicked(*args):
#	global compoundButtonValue
	
#	if compoundButtonValue == 1:
#		compoundButtonValue = 0
		
#	elif compoundButtonValue == 0:
#		compoundButtonValue = 1

def pedalButtonClicked(*args):
	global pedalButtonValue
	
	if pedalButtonValue == 0:
		pedalButtonValue = 1
		
	elif pedalButtonValue == 1:
		pedalButtonValue = 2
	
	elif pedalButtonValue == 2:
		pedalButtonValue = 0

#Activity listeners
def appActivated(*args):
	global appActiveValue
	
	appActiveValue = 1

def appDismissed(*args):
	global appActiveValue
	
	appActiveValue = 0
	
#Helper functions
def writeFile(file, list, dir):

	if not os.path.exists(dir):
		os.makedirs(dir)

	f = open(file, "wb")
	pickle.dump(list, f)
	f.close()

def loadFile(file, var):

	if os.path.exists(file):
		f = open(file, "rb")
		var = pickle.load(f)
		f.close()

	return var
	
def listenKey1():
	try:
		ctypes.windll.user32.RegisterHotKey(None, 1, raceessentials_lib.win32con.MOD_ALT, 0x44)
		msg = ctypes.wintypes.MSG()
		while listenKeyActive:
			if ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
				if msg.message == raceessentials_lib.win32con.WM_HOTKEY:
					deltaButtonClicked()

				ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
				ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))
	finally:
		ctypes.windll.user32.UnregisterHotKey(None, 1)
		
def listenKey2():
	try:
		ctypes.windll.user32.RegisterHotKey(None, 1, raceessentials_lib.win32con.MOD_ALT, 0x43)
		msg = ctypes.wintypes.MSG()
		while listenKeyActive:
			if ctypes.windll.user32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
				#if msg.message == raceessentials_lib.win32con.WM_HOTKEY:
					#compoundButtonClicked()
				ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
				ctypes.windll.user32.DispatchMessageA(ctypes.byref(msg))
	finally:
		ctypes.windll.user32.UnregisterHotKey(None, 1)

keyListener1 = threading.Thread(target = listenKey1)
keyListener1.daemon = True
keyListener1.start()

keyListener2 = threading.Thread(target = listenKey2)
keyListener2.daemon = True
keyListener2.start()