import sensor, image, time, pyb, ustruct

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False, value = 128) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
sensor.set_auto_exposure(False, value = 64)
clock = time.clock()


l_red = pyb.LED(1)
l_green = pyb.LED(2)
l_blue = pyb.LED(3)
l_IR = pyb.LED(4)

l_red.on() #red heartbeat
time.sleep(200)
l_red.off() #red heartbeat

l_green.on() #green heartbeat
time.sleep(200)
l_green.off() #green heartbeat

img = sensor.snapshot()

i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
i2c_obj.deinit() # Fully reset I2C device...
i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

print(i2c_obj)
print("Beginning...")
thing_to_send = 69
packed_data = ustruct.pack("<i", thing_to_send)

while(True):
    try:
        i2c_obj.send(packed_data,timeout=10000)

    except OSError as err:
        print(err)
        pass # Don't care about errors - so pass.
        # Note that there are 3 possible errors. A timeout error, a general purpose error, or
        # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".
