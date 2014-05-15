import pid as pid,pwm_weather as pwm
from time import sleep
import os
fan = pwm.pwm(60,2)
p = pid.PID(1,1,0.02, Integrator_max=100, Integrator_min=0)
p.setPoint(74.0)
#start fan @ 0 
fan.start(0)
cycle=0

try:
 while True:
  sleep(.5)
  os.system('clear')
  #get temperature from my pwm class and pass it into the pid loop update
  x = (p.update(pwm.temp()))*-1
  print x
  cycle = 100 + int(x)
  if (cycle<0):
   cycle=0
  if (cycle>100):
   cycle=100
  print 'Setpoint: 74.0 \nTemp: '+str(pwm.temp())+' \nFan Speed: ',str(cycle)+'%'
  fan.changeDutyCycle(cycle)
except KeyboardInterrupt:
  fan.stop()
  pass
 
