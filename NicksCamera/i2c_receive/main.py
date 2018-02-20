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

t_start = time.ticks()
t_elapsed = 0

img = sensor.snapshot()

bus = pyb.I2C(2, pyb.I2C.MASTER)
bus.deinit() # Fully reset I2C device...
bus = pyb.I2C(2, pyb.I2C.MASTER)

print(bus)
print("Beginning...")
data = bytearray(16)

while(True):
    try:
        bus.recv(data, 0x12,timeout=10000)
        print(data)
        print(ustruct.unpack("<ds", data))
        try:
            bus.recv(data, 0x12,timeout=10000)
            print(data)
            print(ustruct.unpack("<ds", data))
        except OSError as err:
            print(err)
            pass # Don't care about errors - so pass.
            # Note that there are 3 possible errors. A timeout error, a general purpose error, or
            # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".
    except OSError as err:
        print(err)
        pass # Don't care about errors - so pass.
        # Note that there are 3 possible errors. A timeout error, a general purpose error, or
        # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".


'''
L = Lightness where 0 is black and 100 is white
A = -127 is green and 128 is red
B = -127 is blue and 128 is yellow.
'''

#Discriminate against median to determine lighting conditions
#3 bins:
#median < 20 = dimly lit (18 maybe?)
#20 =< median =< 40 = well lit
#median > 40 = over lit

#thresholds LAB -> [Llo, Lhi, Alo, Ahi, Blo, Bhi]
#stage_one_thresholds = [(0, 100, -127, -10, 0, 60)]

#Goal is to make sure we're evaluating the right areas in a photo for NDVI change.
#If we found the edges of a leaf, that feels the most powerful...

#Either way, we need to make sure we're looking only at leaf, and not other semi-reflective objects.
#Similarly we want to ensure that if the leaf has parts that are dying, we don't remove those. It
#feels like once we have identified a leaf, we move into the center and then create a reliable area
#to perform operations on.

#One way to do this is use the blob function to get a centroid - centroids seem to be pretty
#reliable. We then create an area around the centroid to perform NDVI on, the larger the area the
#less likely noise and anomolies hurt us, the smaller the area the safer we are from including
#pixels off the leaf.

#We can use the blobs rect specs and density to calculate the size of the area. Something like
#ndvi_area = rect_area*density ... if ndvi_area > area_min, ndvi_area = 0 to ensure if a bad
#blob is found or the leaf is too small we don't bother with it.

#img.find_edges(image.EDGE_SIMPLE, (80, 120))
