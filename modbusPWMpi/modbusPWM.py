from pymodbus.server.async import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer
from twisted.internet.task import LoopingCall
from threading import Thread
import pid
import threading
from time import sleep
import RPi.GPIO as GPIO
import os
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
#set up Raspberry GPIO 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(25,GPIO.OUT)
pwm = GPIO.PWM(25,60)
pwmDutyCycle=100
pwm.start(pwmDutyCycle)
temperaturePoll = None

class Temp(Thread):
    """
     A class for getting the current temp of a DS18B20
    """
    def __init__(self, fileName=''):
        Thread.__init__(self)
        super(Temp, self).__init__()
        self._stop = threading.Event()
        self.tempDir = '/sys/bus/w1/devices/'
        list = os.listdir(self.tempDir)
        if(list[0][:2]=="28"):
         fileName=list[0]
        self.fileName = fileName
        self.currentTemp = -999
        self.correctionFactor = 1;
        self.enabled = True
        self.Run=True
    def run(self):
        while self.isEnabled():
			try:
				f = open(self.tempDir + self.fileName + "/w1_slave", 'r')
			except IOError as e:
				print "Error: File " + self.tempDir + self.fileName + "/w1_slave" + " does not exits"
				return;
			lines=f.readlines()
			crcLine=lines[0]
			tempLine=lines[1]
			result_list = tempLine.split("=")
			temp = float(result_list[-1])/1000 # temp in Celcius
			temp = temp + self.correctionFactor # correction factor
			#if you want to convert to Celcius, comment this line
			temp = (9.0/5.0)*temp + 32
			if crcLine.find("NO") > -1:
				temp = -999
			self.currentTemp = temp
			#print "Current: " + str(self.currentTemp) + " " + str(self.fileName)
			sleep(.5)
    #returns the current temp for the probe
    def getCurrentTemp(self):
        return self.currentTemp
    #setter to enable this probe
    def setEnabled(self, enabled):
        self.enabled = enabled
    #getter
    def isEnabled(self):
        return self.enabled
	

def updating_writer(a):
	context  = a[0]
	register = 3
	slave_id = 0x00
	address  = 0x00
	global pwmDutyCycle,temp
	#uncomment to debug temperature
	print temp.getCurrentTemp()
	values = [int(pwmDutyCycle),temp.getCurrentTemp()*100]
	context[slave_id].setValues(register,address,values)
def read_context(a):
	context  = a[0]
	register = 3
	slave_id = 0x00
	address  = 0x00
	value = context[slave_id].getValues(register,address)[0]
	global pwmDutyCycle
	if(value!=pwmDutyCycle):
		print value
		pwmDutyCycle=value
		pwm.ChangeDutyCycle(pwmDutyCycle)
def main():
	
	store = ModbusSlaveContext(
		di = ModbusSequentialDataBlock(0, [0]*100),
		co = ModbusSequentialDataBlock(0, [0]*100),
		hr = ModbusSequentialDataBlock(0, [0]*100),
		ir = ModbusSequentialDataBlock(0, [0]*100))
	context = ModbusServerContext(slaves=store, single=True)
	identity = ModbusDeviceIdentification()
	identity.VendorName  = 'pymodbus'
	identity.ProductCode = 'PM'
	identity.VendorUrl   = 'http://github.com/simplyautomationized'
	identity.ProductName = 'pymodbus Server'
	identity.ModelName   = 'pymodbus Server'
	identity.MajorMinorRevision = '1.0'
	time = 5 # 5 seconds delaytime = 5 # 5 seconds delay
	writer = LoopingCall(read_context,a=(context,))
	loop = LoopingCall(updating_writer, a=(context,))
	loop.start(.5) # initially delay by time
	writer.start(.1)
	StartTcpServer(context, identity=identity)#, address=("localhost", 502))
	#cleanup async tasks
	temp.setEnabled(False)
	loop.stop()
	writer.stop()
	GPIO.cleanup()
if __name__ == "__main__":
	temp = Temp()
	temp.start()
	main()
