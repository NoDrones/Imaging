import sensor, image, time, pyb, ustruct

#################
# This send function takes packed data, calculates the size, sends that first, then sends the data
# This means the receiver is always looking for a format "<i" before next_msg_format

def send_packed_msg(packed_msg, max_attempts = 5):

    # alternative for size calcs incase this doesnt work `PyBytes_Size(packed_msg)`
    packed_next_msg_size = ustruct.pack("<i", packed_msg.size())
    msg_list = [packed_next_msg_size, packed_msg]

    for msg in msg_list
        attempts = 0
        while success == False and attempts < max_attempts:
            print("Sending message. Attempt # %i" % attempt)
            # Attempt to send packed data with 5 second timeout
            attempts = attempts + 1
            try:
                i2c_obj.send(msg,timeout=5000)
                print("Message sent...")
                success = True
            except OSError as err:
                print("Error: " + str(err))
                pass # Don't care about errors - so pass.
                # Note that there are 3 possible errors. A timeout error, a general purpose error, or
                # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".

        if success == False:
            return -1
    return 1

#################
# Default next_msg_format_str is the one used to unpack this message
# Default next_msg_type_str is the one that matches this message

def send_next_msg_format(next_msg_type_str = "format", next_msg_format_str = "<s"):

    next_msg_type_bytes = next_msg_type_str.encode('ascii')
    next_msg_format_bytes = next_msg_format_str.encode('ascii')

    # Both receiver and sender should always append an additional string and integer to the format
    # This will always be the expected format str and byte size for the next message
    packed_next_msg_format = ustruct.pack("<ssi", next_msg_type_bytes, next_msg_format_bytes)

    return send_packed_msg(packed_msg = packed_next_msg_format)

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call send_msg_format()
# at the begining of each communication it is unneccesary. Only specify this variable if you plan on
# sending a custom message without calling send_msg_format() first.

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0,
                warning_str = "none", next_msg_format_str = "<ss":

    format_str = "<6is"
    success = send_msg_format(next_msg_type_str = "data", next_msg_format_str = format_str)
    if success == False:
        return -1

    warning_bytes = warning_str.encode('ascii')

    if !next_msg_format_str.endswith("s"):
        print("Warning: next_msg_format_str doesn't end with an s, receiver will default to <s")
    packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1],
                                leaf_health[0], leaf_health[1], plant_ndvi, plant_ir,
                                warning_bytes, next_msg_format_str)

    return send_packed_msg(packed_msg = packed_data)

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call send_msg_format()
# at the begining of each communication it is unneccesary. Only specify this variable if you plan on
# sending a custom message after without calling send_msg_format() first.

def send_calibration(overall_gain = 0, rgb_gain = (0, 0, 0), exposure = 0, warning_str = "none"
                        next_msg_format_str = "<s"):

    format_str = "<5is"
    success = send_msg_format(next_msg_type_str = "calibration", next_msg_format_str = format_str)
    if success == False:
        return -1

    warning_bytes = warning_str.encode('ascii')
    packed_calibration = ustruct.pack(format_str + "s", overall_gain, rgb_gain[0],
                                rgb_gain[1], rgb_gain[2], exposure, warning_bytes,
                                next_msg_format_str)

    return send_packed_msg(packed_msg = packed_calibration)

#################
# I might want to end up just using a ISR on a GPIO pin for this... but interrupts in uPython feels
# like using a fireplace to reflow a PCB, sure it might be possible, but there will be a lot of
# smoke and we probably shouldn't trust whatever comes out

def send_trigger():
    # Don't need to specify a next_msg_format_str because this message is treated differently
    success = send_msg_format(next_msg_type_str = "trigger")
    if success == False:
        return -1

    return 1

#################
# This function was designed to receive a format string and return the unpacked tuple.
# To listen and wait for direction from the sender simply call listen_for_msg and specify a
# long wait_time, without a format_str argument you should expect to receive back a two string
# tuple, with the first string specifying a type or delivering a message, and the second string
# specifying the next_msg_format_str that should be used upon calling listen_for_msg() again.
#
# 1st msg_stage receives a 4 byte integer specifying the next message size
# 2nd msg_stage recursively returns the next packed_data, which the 1st msg_stage unpacks
# based on the format_str specifier it was given, and returns the tuple

def listen_for_msg(format_str = "<ss", msg_size_bytes = 4, msg_stage = 1, wait_time = 30000):

    i2c_data = bytearray(msg_size_bytes)
    success = False
    t_start = time.ticks()

    while elapsed_time < (wait_time / 2) and success == False:
        try:
            i2c_obj.recv(i2c_data, timeout = 5000)
            print("Received data")
            success = True
        except OSError as err:
            print("Error: " + str(err))
        elapsed_time = time.ticks() - t_start

    if success == False:
        return -1

    if msg_stage = 1:
        next_msg_size_bytes = int(ustruct.unpack("<i", i2c_data))
        packed_msg = listen_for_msg(msg_size_bytes = next_msg_size_bytes, msg_stage = 2)
        # If an error occured in stage 2, exit stage 1
        if packed_msg == -1:
            return -1
        return ustruct.unpack(format_str, packed_msg)

    if msg_stage = 2:
        return i2c_data

#################
# This function is responsible for receiving messages and carrying out commands

def receive_msg()
    # Before you know what you're receiving call this function, expecting the first communication
    # to contain details about the 2nd communication
    next_msg_type_bytes, next_msg_format_bytes = listen_for_msg()
    next_msg_type_str = next_msg_type_bytes.decode("ascii")
    next_msg_format_str = next_msg_format_bytes.decode("ascii")

    if next_msg_type_str == "calibration":
        # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure,
        # warning_bytes, next_msg_format_str
        calibration_tuple = listen_for_msg(format_str = next_msg_format_str)
        #### CALL CALIBRATION FUNCTION ####
        # Check for warnings
        if calibration_tuple[6] != "none"
            print("Calibration Warning: " + calibration_tuple[6])
        # return the next_msg_format_str
        # should evaluate this, and if it's not "<s" you better be ready to send something else
        next_msg_format = calibration_tuple[7]
        if !next_msg_format.endswith("s"):
            print("Warning: the next ")
        return calibration_tuple[7]

    elif next_msg_type_str == "data":
        # data tuple structure: leaf_count_h, leaf_count_u, leaf_health_h, leaf_health_u,
        # plant_ndvi, plant_ir, warning_bytes, next_msg_format_str
        data_tuple = listen_for_msg(format_str = next_msg_format_str)
        #### CALL DATA LOGGING FUNCTION ####
        # Check for warnings
        if data_tuple[7] != "none"
            print("Data Warning: " + data_tuple[6])
        # return the next_msg_format_str
        # should evaluate this, and if it's not "<s" you better be ready to send something else
        return data_tuple[8]

    elif next_msg_type_str == "trigger":
        #### CALL TRIGGER FUNCTION ####
        return 1

    # If we don't recognize the next_msg_type_str, print it and return the tuple
    else:
        print("Unrecognized message type: " + next_msg_type_str)
        return (next_msg_type_str, listen_for_msg(format_str = next_msg_format_str))

#################

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
