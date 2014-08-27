from parse_rest.connection import register
from parse_rest.datatypes import Object
from threading import Thread
from time import sleep
import os
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
class Temperature(Object):
	pass


class TempLogger(Thread):
	"""
	A class for getting the current temp of a DS18B20
	"""
	def __init__(self, fileName='',debug=False,appkey='',apikey=''):
		Thread.__init__(self)
		register(appkey,apikey)
		self.debug = debug
		self.probes = {}
		self.tempDir = '/sys/bus/w1/devices/'
		self.currentTemp = -999
		self.correctionFactor = 1;
		self.enabled = True
		self.repopulateprobes()
	def repopulateprobes(self):
		list = os.listdir(self.tempDir)
		for item in list:
		 if(item[:2]=="28"):
			if(self.debug):
				print item
			if(self.probes.has_key(item)==False):
				self.probes[item]=0

	def getTempForFile(self,file):
		try:
			f = open(self.tempDir + file + "/w1_slave", 'r')
		except IOError as e:
			print "Error: File " + self.tempDir + file + "/w1_slave" + " doesn't exist"
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
		if(self.debug):
			print "Current: " + str(temp) + " " + str(file)
		return float(int(temp*100))/100	   
	def run(self):
		while self.enabled:
			for item in self.probes.items():
				temp = self.getTempForFile(item[0])
				if(item[1]!=temp):
					parseDBObject=Temperature()
					parseDBObject.Probe=item[0]
					parseDBObject.Temperature=temp
					try:
						parseDBObject.save()
					except:
						pass
					self.probes[item[0]]=temp
	def stop(self):
		self.enabled=False
    #returns the current temp for the probe
	def getCurrentTemp(self,file):
		return self.probes[file]