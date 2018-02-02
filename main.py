import sensor, image, time, pyb

sensor.reset()                      # Reset and initialize the sensor.
print("just reset")
sensor.set_gainceiling(16)
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
                                    # Can't do operations on RGB565 @ VGA resolution because not enough RAM. Image is automatically and forcibly compressed to JPEG.

sensor.set_auto_whitebal(False)

print("just disabled exp and white")
sensor.skip_frames(n = 60)          # Wait for settings take effect.
print("just skipped frames")

'''
#get white balance. You have two seconds.
t_start = time.ticks()
t_elapsed = 0
'''

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

for i in range(1000):
    img = sensor.snapshot()         # Take a picture and return the image.

    #img.histeq()

    '''
    L = Lightness where 0 is black and 100 is white
    A = position between red and green where -127 is green and 128 is red
    B = position between yellow and blue where -127 is blue and 128 is yellow.
    '''

    stage_one_thresholds = [(0, 100, -127, 0, 0, 60)] #LAB -> [Llo, Lhi, Alo, Ahi, Blo, Bhi]
    stage_two_thresholds = [(10, 50, -10, 40, -30, 30)]


    for blob_index, stage_one_blob in enumerate(img.find_blobs(stage_one_thresholds, pixels_threshold=50, area_threshold=50, merge = False)):

        cur_hist = img.get_histogram(roi = (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3]))
        cur_stats = cur_hist.get_statistics()

        #Use threshold_cb for this functionality!!!
        if abs(cur_stats.a_mean() - cur_stats.b_mean()) > 20: #if the a and b histograms are close together it means the color is probably white and should be discarded
            img.draw_rectangle(stage_one_blob.rect(), color = 120)

            l_blue.on()
            time.sleep(50)
            l_blue.off()
            img.save("/stg_one_blob_" + str(blob_index), 100, (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3]))


            for stage_two_blob in img.find_blobs(stage_two_thresholds, merge = False, roi = (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3])):
                img.draw_rectangle(stage_two_blob.rect(), color = 0)

                #img.save("/blob" + str(blob_index), 100, roi = (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3]))



#need these to flush the current image (if only taking a single image) in the frame buffer to the IDE and then give time for the blob containers to appear
sensor.flush()
time.sleep(1000)


