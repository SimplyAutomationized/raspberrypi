###############################################################################
##
##  Copyright (C) 2011-2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################
import sqlite3 as lite
import sys,json,time
from time import sleep
import Koyo
from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File
from OpenSSL import SSL
from twisted.internet import reactor,ssl,protocol
from twisted.web.resource import Resource
from twisted.web.wsgi import WSGIResource
from autobahn.twisted.resource import WebSocketResource, HTTPChannelHixie76Aware
from autobahn.twisted.websocket import WebSocketServerFactory, \
                                       WebSocketServerProtocol, \
                                       listenWS
mysprinkler=None
status=None

class BroadcastServerProtocol(WebSocketServerProtocol):

   def onOpen(self):
      print self.peer
      self.factory.register(self)

   def onMessage(self, payload, isBinary):
      if not isBinary:
         msg = "{} from {}".format(payload.decode('utf8'), self.peer)
         #self.factory.broadcast(msg)

   def connectionLost(self, reason):
      WebSocketServerProtocol.connectionLost(self, reason)
      self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):
   """
   Simple broadcast server broadcasting any message it receives to all
   currently connected clients.
   """

   def __init__(self, url, debug = False, debugCodePaths = False):
	WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debugCodePaths)
	self.clients = []
	self.tickcount = 0
	self.tempstatus=None
	self.sprinkler_status=spinklercontrol()
	self.tick()


   def tick(self):
	self.tickcount += 1
	try:
		self.sprinkler_status=spinklercontrol()
		if(self.tempstatus!=self.sprinkler_status):#send sprinkler status on status change
			self.broadcast(json.dumps({"status":self.sprinkler_status}))
			self.tempstatus=self.sprinkler_status
		if(self.tickcount>=100):#send status every 10 seconds
			self.broadcast(json.dumps({"status":self.sprinkler_status}))
			self.tempstatus=self.sprinkler_status
			self.tickcount=0
			print 'tick',time.time()
	except Exception:
		sleep(1)
		print time.asctime()
		pass
	reactor.callLater(.1, self.tick)

   def register(self, client):
	if not client in self.clients:
		rint("registered client {}".format(client.peer))
		self.clients.append(client)
		self.sprinkler_status=status
		self.broadcast(json.dumps({"status":self.sprinkler_status}))
   def unregister(self, client):
      if client in self.clients:
         print("unregistered client {}".format(client.peer))
         self.clients.remove(client)
   def broadcast(self, msg):
      for c in self.clients:
         c.sendMessage(msg.encode('utf8'))
         

class BroadcastPreparedServerFactory(BroadcastServerFactory):
   """
   Functionally same as above, but optimized broadcast using
   prepareMessage and sendPreparedMessage.
   """

   def broadcast(self, msg):
      print("broadcasting prepared message '{}' ..".format(msg))
      preparedMsg = self.prepareMessage(msg)
      for c in self.clients:
         c.sendPreparedMessage(preparedMsg)
         print("prepared message sent to {}".format(c.peer))

class MyProcessProtocol(protocol.ProcessProtocol):
	def __init__(self):
		global result
	def outReceived(self, data):
		global result
		result=data
	def outConnectionLost(self):
		result='done!'
class schedule(Resource):
	def render_GET(self,request):
		#print request.args
		if(request.args['cmd'][0]=='get'):
			station_id=request.args['uid'][0]
			request.setHeader("content-type", "application/json")
			con = lite.connect('sprinklers.db')
			con.row_factory=lite.Row
			cur=con.cursor()
			rows=cur.execute('select * from schedule left join stations on schedule.station_uid=stations.uid where station_uid=? order by day_of_week,time_of_day asc',(station_id,)).fetchall()
			con.commit()
			con.close()
			return json.dumps( [dict(ix) for ix in rows] )
		else:
			return ''
	def render_POST(self,request):
		#print request.args
		if(request.args['cmd'][0]=='add'):
			station_id=request.args['uid'][0]
			day=request.args['day'][0]
			startTime=request.args['startTime'][0]
			runTime=request.args['runTime'][0]
			request.setHeader('content-type','application/json')
			con = lite.connect('sprinklers.db')
			con.row_factory=lite.Row
			cur=con.cursor()
			cur.execute("Insert into schedule (station_uid,day_of_week,time_of_day,run_time) Values(?,?,?,?)",(station_id,day,startTime,runTime.zfill(2),))
			id=cur.execute('select uid from schedule order by uid desc limit 1').fetchall()
			con.commit()
			con.close()
			return json.dumps({'newuid':int(id[0][0])})
		if(request.args['cmd'][0]=='remove'):
			uid=request.args['uid'][0]
			con = lite.connect('sprinklers.db')
			con.row_factory=lite.Row
			cur=con.cursor()
			cur.execute("Delete from schedule where uid='{0}'".format(uid))
			con.commit()
			con.close()
			return json.dumps({'response':True,'uid':uid})
		return ''
class sChange(Resource):
	def render_GET(self,request):
		request.setHeader("content-type", "application/json")
		con = lite.connect('sprinklers.db')
		con.row_factory=lite.Row
		cur=con.cursor()
		rows=cur.execute('select * from stations').fetchall()
		con.commit()
		con.close()
		return json.dumps( [dict(ix) for ix in rows] )
	def render_POST(self,request):
		request.setHeader("content-type", "application/json")
		#json_request = json.loads(request.args)
		#print json_request['cmd']
		if(request.args['cmd'][0]=='edit'):
			station = request.args["station"][0]
			port= request.args["port"][0]
			uid=request.args["uid"][0]
			con = lite.connect('/home/pi/cron/sprinklers.db')
			con.row_factory=lite.Row
			cur = con.cursor()
			cur.execute("Update stations set station=?,koyo_output=? where uid=?",(station,port,uid,))
			con.commit()
			con.close()
			request.setHeader("content-type", "text/html")
			return '<html><head><script>window.location="sprinklers.html"</script></head></html>'
		if(request.args['cmd'][0]=='add'):
			station = request.args["station"][0]
			port = request.args["koyo_output"][0]
			con = lite.connect('/home/pi/cron/sprinklers.db')
			con.row_factory=lite.Row
			cur = con.cursor()
			cur.execute("Insert into stations (station,koyo_output) values(?,?)",(station,port,))
			id=cur.execute("select uid from stations order by uid desc limit 1").fetchall()
			#print id[0][0]
			con.commit()
			con.close()
			return json.dumps({'newuid':int(id[0][0])})
		if(request.args['cmd'][0]=='remove'):
			uid=request.args['uid'][0]
			con = lite.connect('/home/pi/cron/sprinklers.db')
			cur = con.cursor()
			cur.execute("Delete from stations where uid=?",(uid,))
			con.commit()
			con.close()
			return json.dumps({'removed':uid})
def loadStationInfo():
    con = lite.connect('sprinklers.db')
    con.row_factory=dict_factory
    cur=con.cursor()
    items=cur.execute('select * from stations').fetchall()
    con.commit()
    con.close()
    return items
def checkManualTable():
    con = lite.connect('sprinklers.db')
    con.row_factory=dict_factory
    cur=con.cursor()
    items=cur.execute('select * from getmanuals').fetchall()
    con.commit()
    con.close()
    return items
def loadScheduled():
    con = lite.connect('sprinklers.db')
    con.row_factory=dict_factory
    cur=con.cursor()
    items = cur.execute('select * from getcurrent').fetchall()
    con.commit()
    con.close()
    return items
def spinklercontrol():
    global status
    stations=loadStationInfo()
    scheduled = loadScheduled()
    new_list=[]
    controller=Koyo.Koyo('0.0.0.0')
    status=controller.ReadC_All()
# go through the result if any and turn on the sprinkler if it isn't on already
    for item in scheduled:
        koyo_port=item['koyo_output']
        if(not controller.ReadC(koyo_port)):
            controller.WriteC(koyo_port, 1)
        new_list.append(koyo_port)
        #print new_list
        #print item['station']
#go through the manual table to see whether to turn on or off stations
    manuals = checkManualTable()
    for manual in manuals:
        koyo_port=manual['koyo_output']
        if(manuals['state']):
            controller.WriteC(koyo_port,1)
            if(not new_list.count(koyo_port)):
                new_list.append(koyo_port)
        else:
            controller.WriteC(koyo_port,0)
            new_list.remove(koyo_port)
# go through the stations and turn off the ones that aren't returned in the both queries
    for station in stations:
        #print station
        koyo_port=station['koyo_output']
        if(new_list.count(koyo_port) == 0  and controller.ReadC(koyo_port)):
            controller.WriteC(koyo_port,0)
    status=controller.ReadC_All()
    return status
def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
if __name__ == '__main__':
   if len(sys.argv) > 1 and sys.argv[1] == 'debug':
      log.startLogging(sys.stdout)
      debug = True
   else:
      debug = False
   contextFactory = ssl.DefaultOpenSSLContextFactory('/home/pi/cron/keys/server.key',
			'/home/pi/cron/keys/server.crt')
   ServerFactory = BroadcastServerFactory
   factory = ServerFactory("wss://localhost:5000",
                           debug = debug,
                           debugCodePaths = debug)
   factory2 = ServerFactory("ws://localhost:5001",
                           debug = debug,
                           debugCodePaths = debug)
   factory.protocol = BroadcastServerProtocol
   factory.setProtocolOptions(allowHixie76 = True)
   factory2.protocol = BroadcastServerProtocol
   factory2.setProtocolOptions(allowHixie76 = True)
   listenWS(factory2)
   listenWS(factory,contextFactory)
   webdir = File("sprinklerwww/")
   web = Site(webdir)
   web.protocol = HTTPChannelHixie76Aware
   webdir.contentTypes['.crt'] = 'application/x-x509-ca-cert'
   webdir.putChild("sChange",sChange())
   webdir.putChild("schedule",schedule())
   reactor.listenTCP(80, web)
   reactor.listenSSL(443,web,contextFactory)
   reactor.run()
