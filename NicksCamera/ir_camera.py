import sensor, image, time, pyb, ustruct

# leafcount = (healthy, unhealthy): average of color and IR leaf count, possibly just IR
def send_msg_type(send_type_str = "none"):
    send_type_bytes = send_type_str.encode('ascii')
    success = False
    packed_data = ustruct.pack("<s", send_type_bytes)

    # Send message type over i2c with 5 attempts, each attempt having it's own timeout
    while success == False and attempts < 5:
        print("Sending message type. attempt # " + i)
        # Attempt to send packed data with 5 second timeout
        try:
            attempts = attempts + 1
            i2c_obj.send(packed_data,timeout=5000)
            print("Data sent...")
            success = True
        except OSError as err:
            print("Error: " + str(err))
            pass # Don't care about errors - so pass.
            # Note that there are 3 possible errors. A timeout error, a general purpose error, or
            # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".
    if success == False:
        return -1
    return 1

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0, warning_string = "none"):

    success = send_msg_type(send_type_str = "data")
    if success == False:
        return -1

    attempts = 0
    success = False
    warning_bytes = warning_string.encode('ascii')
    packed_data = ustruct.pack("<6is", leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir, warning_bytes)

    # Send data over i2c with 5 attempts, each attempt having it's own timeout
    while success == False and attempts < 5:
        print("Sending data. attempt # " + i)
        # Attempt to send packed data with 5 second timeout
        try:
            attempts = attempts + 1
            i2c_obj.send(packed_data,timeout=5000)
            print("Data sent...")
            success = True
        except OSError as err:
            print("Error: " + str(err))
            pass # Don't care about errors - so pass.
            # Note that there are 3 possible errors. A timeout error, a general purpose error, or
            # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".
    if success == False:
        return -1

    return 1

def send_calibration(overall_gain = 0, rgb_gain = (0, 0, 0), exposure = 0, warning_string = "none"):

    success = send_msg_type(send_type_str = "calibration")
    if success == False:
        return -1

    attempts = 0
    success = False
    warning_bytes = warning_string.encode('ascii')
    packed_data = ustruct.pack("<5is", overall_gain, rgb_gain[0], rgb_gain[1], rgb_gain[2], exposure, warning_bytes)

    # Send data over i2c with 5 attempts, each attempt having it's own timeout
    while success == False and attempts < 5:
        print("Sending calibration. attempt # " + i)
        # Attempt to send packed data with 5 second timeout
        try:
            attempts = attempts + 1
            i2c_obj.send(packed_data,timeout=5000)
            print("Data sent...")
            success = True
        except OSError as err:
            print("Error: " + str(err))
            pass # Don't care about errors - so pass.
            # Note that there are 3 possible errors. A timeout error, a general purpose error, or
            # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".
    if success == False:
        return -1

    return 1

def send_trigger():
    success = send_msg_type(send_type_str = "trigger")
    if success == False:
        return -1

    return 1

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

    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
    i2c_obj.deinit() # Fully reset I2C device...
    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

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
