import smbus,time,threading
pi = smbus.SMBus(1)

address = 0x4e
def temp():
  return pi.read_byte_data(address,0x42)*1.8+32

def humidity():
  return pi.read_byte_data(address,0x42)

class pwm(threading.Thread):

  def __init__(self, frequency, gpioPin):
     """ 
     Init the PiZyPwm instance. Expected parameters are :
     - frequency : the frequency in Hz for the PWM pattern. A correct value may be 100.
     - gpioPin : the pin number which will act as PWM ouput
     - gpioScheme : the GPIO naming scheme (see RPi.GPIO documentation)
     """
     self.baseTime = 1.0 / frequency
     self.maxCycle = 100.0
     self.sliceTime = self.baseTime / self.maxCycle
     self.gpioPin = gpioPin
     self.terminated = False
     self.toTerminate = False
     #GPIO.setmode(gpioScheme)


  def start(self, dutyCycle):
    """
    Start PWM output. Expected parameter is :
    - dutyCycle : percentage of a single pattern to set HIGH output on the GPIO pin
    
    Example : with a frequency of 1 Hz, and a duty cycle set to 25, GPIO pin will 
    stay HIGH for 1*(25/100) seconds on HIGH output, and 1*(75/100) seconds on LOW output.
    """
    self.dutyCycle = dutyCycle
    #GPIO.setup(self.gpioPin, GPIO.OUT)
    self.thread = threading.Thread(None, self.run, None, (), {})
    self.thread.start()


  def run(self):
    """
    Run the PWM pattern into a background thread. This function should not be called outside of this class.
    """
    while self.toTerminate == False:
      if self.dutyCycle > 0:
        #GPIO.output(self.gpioPin, GPIO.HIGH)
        pi.write_byte_data(address,0x25,self.gpioPin)
	time.sleep(self.dutyCycle * self.sliceTime)
      
      if self.dutyCycle < self.maxCycle:
        #GPIO.output(self.gpioPin, GPIO.LOW)
	pi.write_byte_data(address,0x26,self.gpioPin)
        time.sleep((self.maxCycle - self.dutyCycle) * self.sliceTime)

    self.terminated = True


  def changeDutyCycle(self, dutyCycle):
    """
    Change the duration of HIGH output of the pattern. Expected parameter is :
    - dutyCycle : percentage of a single pattern to set HIGH output on the GPIO pin
    
    Example : with a frequency of 1 Hz, and a duty cycle set to 25, GPIO pin will 
    stay HIGH for 1*(25/100) seconds on HIGH output, and 1*(75/100) seconds on LOW output.
    """
    self.dutyCycle = dutyCycle


  def changeFrequency(self, frequency):
    """
    Change the frequency of the PWM pattern. Expected parameter is :
    - frequency : the frequency in Hz for the PWM pattern. A correct value may be 100.
    
    Example : with a frequency of 1 Hz, and a duty cycle set to 25, GPIO pin will 
    stay HIGH for 1*(25/100) seconds on HIGH output, and 1*(75/100) seconds on LOW output.
    """
    self.baseTime = 1.0 / frequency
    self.sliceTime = self.baseTime / self.maxCycle


  def stop(self):
    """
    Stops PWM output.
    """
    self.toTerminate = True
    while self.terminated == False:
      # Just wait
      time.sleep(0.01)
    pi.write_byte_data(address,0x26,self.gpioPin)
    #GPIO.output(self.gpioPin, GPIO.LOW)
    #GPIO.setup(self.gpioPin, GPIO.IN)

#motor = pwm(100,4)
#motor.start(100)

