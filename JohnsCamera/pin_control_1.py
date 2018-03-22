# Pin Control Example
#
# This example shows how to use the I/O pins in GPIO mode on your OpenMV Cam.

import pyb


# Connect a switch to pin 0 that will pull it low when the switch is closed.
# Pin 1 will then light up.
pin0 = Pin('P0', Pin.IN, Pin.PULL_UP)
pin1 = Pin('P1', Pin.OUT_PP, Pin.PULL_NONE)


# \/ This is the code to define a Pin, make it an output and set it high/low \/
p = pyb.Pin("P2", pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
pin0.low()         #p.high() or p.value(1) to make the pin high (3.3V)
p.low()            # or p.value(0) to make the pin low (0V)
print ("Pin value = ",p.value())

while(True):
    pin1.value(not pin0.value())
