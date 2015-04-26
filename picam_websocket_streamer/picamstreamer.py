import sys,json
from time import sleep
import picamera,threading
from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from fractions import Fraction
from twisted.web.static import File
from autobahn.twisted.websocket import WebSocketServerFactory, \
                                       WebSocketServerProtocol, \
                                       listenWS
camwrite = None
cam = None
clients=[]
class MyOutput(object):
	def __init__(self):
		self.size = 0
	def write(self, s):
		self.size += len(s)
		camwrite(s)
	def flush(self):
		print('%d bytes would have been written' % self.size)
class BroadcastServerProtocol(WebSocketServerProtocol):

   def onOpen(self):
      self.factory.register(self)

   def onMessage(self, payload, isBinary):
	global cam
	if not isBinary:
	 msg = "{} from {}".format(payload.decode('utf8'), self.peer)
	 #self.factory.broadcast(msg)
	 cmd = json.loads(payload)
	 if(cmd.has_key("cmd")):
		if(cmd["cmd"]=="showpreview"):
			cam.start_preview()
		if(cmd["cmd"]=="hidepreview"):
			cam.stop_preview()
	 if(cmd.has_key("framerate")):
		cam.stop_recording()
		cam.framerate=int(cmd["framerate"])
		cam.start_recording(MyOutput(), format='mjpeg',bitrate=0,quality=40)
   def connectionLost(self, reason):
      WebSocketServerProtocol.connectionLost(self, reason)
      self.factory.unregister(self)

class BroadcastServerFactory(WebSocketServerFactory):
   def __init__(self, url, debug = False, debugCodePaths = False):
		WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debugCodePaths)
		global clients
		self.clients = clients
		self.tickcount = 0
		global cam,camwrite
		camwrite=self.broadcast
		cam = picamera.PiCamera()
		cam.framerate = 2
		cam.exposure_mode = 'night'
		
   def register(self, client):
      if (len(self.clients)==0):
		 cam.start_recording(MyOutput(), format='mjpeg',bitrate=0,quality=40)
      if not client in self.clients:
         print("registered client {}".format(client.peer))
         self.clients.append(client)
   def unregister(self, client):
      if client in self.clients:
         print("unregistered client {}".format(client.peer))
         self.clients.remove(client)
      if(len(self.clients)<=0):
		 cam.stop_recording()
		 
   def broadcast(self, msg):
      #print("broadcasting message '{}' ..".format(msg))
      for c in self.clients:
         c.sendMessage(msg.encode('base64'))
         print("message sent to {}".format(c.peer))

if __name__ == '__main__':
	
   if len(sys.argv) > 1 and sys.argv[1] == 'debug':
      log.startLogging(sys.stdout)
      debug = True
   else:
      debug = False
   global cam
   ServerFactory = BroadcastServerFactory
   #ServerFactory = BroadcastPreparedServerFactory

   factory = ServerFactory("ws://localhost:9000",
                           debug = debug,
                           debugCodePaths = debug)

   factory.protocol = BroadcastServerProtocol
   factory.setProtocolOptions(allowHixie76 = True)
   listenWS(factory)

   webdir = File("/usr/local/www")
   web = Site(webdir)
   reactor.listenTCP(80, web)
   
   reactor.run()
   cam.stop_recording()
   cam.close()
