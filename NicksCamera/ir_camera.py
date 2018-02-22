import sensor, image, time

def set_custom_exposure(high_mean_thresh = 100, low_mean_thresh = 90):
    try:
        print("Starting Exposure Adjustment...")
        b_gain = sensor.__read_reg(0x01)
        r_gain = sensor.__read_reg(0x02)
        g_gain = sensor.__read_reg(0x03)
        r_gain = round(r_gain/3)
        g_gain = round(g_gain/3)
        b_gain = round(b_gain/3)
        sensor.__write_reg(0x01, b_gain)
        sensor.__write_reg(0x02, r_gain)
        sensor.__write_reg(0x03, g_gain)

        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        mean = img_stats.mean()
        count = 0
        cur_gain = sensor.__read_reg(0x00)

        while(((mean > high_mean_thresh) | (mean < low_mean_thresh))) & (count < 1000):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            mean = img_stats.mean()

            print("current gain: " + str(cur_gain))
            print("mean: " + str(mean))

            if mean > high_mean_thresh:
                new_gain = cur_gain - 1
            elif mean < low_mean_thresh:
                new_gain = cur_gain + 1
            else:
                break #we're in the range now!

            sensor.__write_reg(0x00, new_gain)
            cur_gain = new_gain
            count += 1

        if count < 1000:
            print("Exposure Adjustment Complete.")
            return mean
        else:
            print("Exposure Adjustment Incomplete.")
            return -1

    except:
        print("Error occured!")
        return -2

if __name__ == "__main__":

    ########### SETUP STUFF

    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time = 2000)
    clock = time.clock()

    sensor.set_auto_gain(False, gain_db = 7) # must be turned off for color tracking
    sensor.set_auto_whitebal(False, rgb_gain_db = (4,4,4)) # must be turned off for color tracking
    sensor.set_auto_exposure(False, exposure_us = 4200)

    #set_mean = set_custom_exposure() #default thresholds

    #sensor.reset()
    #sensor.set_pixformat(sensor.GRAYSCALE)
    #sensor.set_framesize(sensor.QVGA)
    #sensor.skip_frames(time = 2000)
    #sensor.set_auto_gain(False, gain_db = 18) # must be turned off for color tracking
    #sensor.set_auto_whitebal(False) # must be turned off for color tracking
    #sensor.set_auto_exposure(False, exposure_us = 420)
    #clock = time.clock()


    #l_red = pyb.LED(1)
    #l_green = pyb.LED(2)
    #l_blue = pyb.LED(3)
    #l_IR = pyb.LED(4)

    #l_red.on() #red heartbeat
    #time.sleep(200)
    #l_red.off() #red heartbeat

    #l_green.on() #green heartbeat
    #time.sleep(200)
    #l_green.off() #green heartbeat

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

    healthy_leaf_thresholds = [(170, 255)]
    unhealthy_leaf_thresholds = [(80, 120)]
    bad_thresholds = [( 0, 50)]

    healthy_leaves_mean_sum = 0
    unhealthy_leaves_mean_sum = 0

    healthy_mean = 0
    unhealthy_mean = 0

    blob_found = False

    for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(healthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
        blob_found = True
        print("leaf blob found: ")
        print(leaf_blob.rect())
        img.draw_rectangle(leaf_blob.rect(), color = 255)
        leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
        # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
        leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3]
        leaf_area = leaf_blob[2] * leaf_blob[3]

        for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=50, area_threshold=50, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
            print("bad blob found: ")
            print(bad_blob.rect())
            img.draw_rectangle(bad_blob.rect(), color = 127)
            bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
            # more undoing of mean function
            bad_rect_pix_sum = bad_rect_stats.mean() * bad_blob[2] * bad_blob[3]
            # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
            leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum
            # tracking the remaining area of the leaf as the bad_rects are removed
            leaf_area = leaf_area - (bad_blob[2] * bad_blob[3])

        leaf_rect_mean = leaf_rect_stats.mean()
        leaf_mean = leaf_rect_pix_sum / leaf_area
        print("healthy leaf mean = %i [outer mean = %i]" % (leaf_mean, leaf_rect_mean))
        # the below function does not take into account the size of a leaf... each leaf is weighted equally
        healthy_leaves_mean_sum = healthy_leaves_mean_sum + leaf_mean

    # calculates the average value for the healthy leaves regardless of leaf size
    if (blob_found == True):
        healthy_mean = healthy_leaves_mean_sum / (leaf_blob_index + 1)

    blob_found = False

    for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(unhealthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
        blob_found = True
        print("leaf blob found: ")
        print(leaf_blob.rect())
        img.draw_rectangle(leaf_blob.rect(), color = 255)
        leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
        # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
        leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3]
        leaf_area = leaf_blob[2] * leaf_blob[3]
        for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
            print("bad blob found: ")
            print(bad_blob.rect())
            img.draw_rectangle(bad_blob.rect(), color = 127)
            bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
            # more undoing of mean function
            bad_rect_pix_sum = bad_rect_stats.mean()*bad_blob[2]*bad_blob[3]
            # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
            leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum
            # tracking the remaining area of the leaf as the bad_rects are removed
            leaf_area = leaf_area - (bad_blob[2] * bad_blob[3])

        leaf_rect_mean = leaf_rect_stats.mean()
        leaf_mean = leaf_rect_pix_sum / leaf_area
        print("unhealthy leaf mean = %i [outer mean = %i]" % (leaf_mean, leaf_rect_mean))
        # the below function does not take into account the size of a leaf... each leaf is weighted equally
        unhealthy_leaves_mean_sum = unhealthy_leaves_mean_sum + leaf_mean

    # calculates the average value for the healthy leaves regardless of leaf size
    if (blob_found == True):
        unhealthy_mean = unhealthy_leaves_mean_sum / (leaf_blob_index + 1)

    print("healthy mean = %i; unhealthy mean = %i" % (healthy_mean, unhealthy_mean))
    if (unhealthy_mean < 135):
        print("You got some seriously unhealthy leafage there, figure it out")
    elif (unhealthy_mean < 145):
        print("Some leaves are unhappy, although they're soldiering on")
    else:
        print("Even your unhealthy leaves are healthy!")


    print(img.compressed_for_ide(quality = 25))

    sensor.flush()
    time.sleep(3000)
