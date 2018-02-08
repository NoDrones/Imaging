import sensor, image, time, pyb

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
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



#for i in range(1000):

#get white balance. You have two seconds.
t_start = time.ticks()
t_elapsed = 0
while(t_elapsed < 4000):
    img = sensor.snapshot()
    t_elapsed = time.ticks() - t_start
    print(img.compressed_for_ide(quality = 25))


img = sensor.snapshot()         # Take a picture and return the image.

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

img_hist = img.get_histogram()
img_stats = img_hist.get_statistics()

stage_one_thresholds = [(80, 100,-8, 8, -8, 8)]

for blob_index, stage_one_blob in enumerate(img.find_blobs(stage_one_thresholds, pixels_threshold=100, area_threshold=100, merge = True)):
    blob_hist = img.get_histogram(roi = (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3]))
    blob_stats = blob_hist.get_statistics()
    print("blob found: ")
    print(stage_one_blob.rect())
    img.draw_rectangle(stage_one_blob.rect(), color = 120)

    for x in range(stage_one_blob[2]):
        for y in range(stage_one_blob[3]):
            pix_location = [stage_one_blob[0] + x, stage_one_blob[1] + y]
            pix_vals = img.get_pixel(pix_location[0], pix_location[1])
            lab_pix_vals = image.rgb_to_lab(pix_vals)

            if (lab_pix_vals[0] > 50):
                pass
            else:
                img.set_pixel(pix_location[0], pix_location[1], (255, 70, 255))

'''
    if (abs(blob_stats.a_mean() - blob_stats.b_mean()) > 20) & (blob_stats.a_max() - blob_stats.a_min() > 20) & (blob_stats.b_max() - blob_stats.b_min() > 20): #if the a and b histograms are close together it means the color is probably white and should be discarded

        img.draw_rectangle(stage_one_blob.rect(), color = 120)

        l_blue.toggle()

        for x in range(stage_one_blob[2]):
            for y in range(stage_one_blob[3]):
                pix_location = [stage_one_blob[0] + x, stage_one_blob[1] + y]
                pix_vals = img.get_pixel(pix_location[0], pix_location[1])
                lab_pix_vals = image.rgb_to_lab(pix_vals)

                if (lab_pix_vals[1] < 0) & (abs(lab_pix_vals[2] - lab_pix_vals[1]) > 40):
                    pass
                else:
                    img.set_pixel(pix_location[0], pix_location[1], (255, 70, 255))

                if (pix_vals[0] <= 20) | (pix_vals[1] <= 20) | (pix_vals[2] <= 20):

                    img.set_pixel(pix_location[0], pix_location[1], (255, 70, 255))



        stage_two_thresholds = [(0, blob_stats.l_mode() + 5, blob_stats.a_mean(), 128, -127, blob_stats.b_mean())]



        for stage_two_blob in img.find_blobs(stage_two_thresholds, merge = False, roi = (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3])):
            img.draw_rectangle(stage_two_blob.rect(), color = 0)

    #img.save("/blob_" + str(blob_index), 100, (stage_one_blob[0], stage_one_blob[1], stage_one_blob[2], stage_one_blob[3]))
'''
print(img.compressed_for_ide(quality = 25))

sensor.flush()
time.sleep(3000)
