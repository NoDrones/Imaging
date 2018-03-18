import sensor, image, time, utime, pyb, ustruct

#################
# This send function takes packed data, calculates the size, sends that first, then sends the data
# This means the receiver is always looking for a format "<i" before next_msg_format

def send_packed_msg(packed_msg, packed_msg_size, max_attempts = 5):

    # alternative for size calcs incase this doesnt work `PyBytes_Size(packed_msg)`
    packed_next_msg_size = ustruct.pack("<i", packed_msg_size)
    msg_list = [packed_next_msg_size, packed_msg]

    for msg in msg_list:
        attempts = 0
        success = False
        while success == False and attempts < max_attempts:
            print("Sending message. Attempt # %i" % attempts)
            # Attempt to send packed data with 5 second timeout
            attempts = attempts + 1
            try:
                i2c_obj.send(msg, addr=0x12, timeout=5000)
                print("Message sent...")
                success = True
            except OSError as err:
                print("Error: " + str(err))
                utime.sleep_ms(100)
                # I have been getting I/O errors, if we see one try resetting i2c
                if (err == EIO):
                    i2c_obj = pyb.I2C(2, pyb.I2C.MASTER)
                    i2c_obj.deinit() # Fully reset I2C device...
                    i2c_obj = pyb.I2C(2, pyb.I2C.MASTER)
                pass # Don't care about errors - so pass.
                # Note that there are 3 possible errors. A timeout error, a general purpose error, or
                # a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".

        if success == False:
            return -1
    return 1

#################
# Default next_msg_format_str is the one used to unpack this message
# Default next_msg_type_str is the one that matches this message

def send_next_msg_format(next_msg_type_str = "format", next_msg_format_str = "<50s"):

    next_msg_type_bytes = next_msg_type_str.encode('ascii')
    next_msg_format_bytes = next_msg_format_str.encode('ascii')

    # Both receiver and sender should always append an additional string and integer to the format
    # This will always be the expected format str and byte size for the next message
    format_str = "<50s50s"
    packed_next_msg_format = ustruct.pack(format_str, next_msg_type_bytes, next_msg_format_bytes)


    return send_packed_msg(packed_msg = packed_next_msg_format, packed_msg_size = ustruct.calcsize(format_str))

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call
# send_next_msg_format() at the begining of each communication it is unneccesary. Only specify this
# variable if you plan on sending a custom message without calling send_next_msg_format() first.

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0, warning_str = "none"):

    format_str = "<6i50s"
    success = send_next_msg_format(next_msg_type_str = "data", next_msg_format_str = format_str)
    if success == False:
        return -1

    warning_bytes = warning_str.encode('ascii')

    packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir, warning_bytes)

    return send_packed_msg(packed_msg = packed_data, packed_msg_size = ustruct.calcsize(format_str))

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call send_msg_format()
# at the begining of each communication it is unneccesary. Only specify this variable if you plan on
# sending a custom message after without calling send_msg_format() first.

def send_calibration(overall_gain = 0, rgb_gain = (0, 0, 0), exposure = 0, warning_str = "none"):

    format_str = "<5i50s"
    success = send_next_msg_format(next_msg_type_str = "calibration", next_msg_format_str = format_str)
    if success == False:
        return -1

    warning_bytes = warning_str.encode('ascii')
    packed_calibration = ustruct.pack(format_str + "s", overall_gain, rgb_gain[0], rgb_gain[1], rgb_gain[2], exposure, warning_bytes)

    return send_packed_msg(packed_msg = packed_calibration, packed_msg_size = ustruct.calcsize(format_str))

#################
# I might want to end up just using a ISR on a GPIO pin for this... but interrupts in uPython feels
# like using a fireplace to reflow a PCB, sure it might be possible, but there will be a lot of
# smoke and we probably shouldn't trust whatever comes out

def send_trigger():
    # Don't need to specify a next_msg_format_str because this message is treated differently
    success = send_next_msg_format(next_msg_type_str = "trigger")
    if success == False:
        return -1

    #### TRIGGER LIGHT SOURCE ####
    print("Light source triggered")
    #### TRIGGER LIGHTSOURCE ####

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

def listen_for_msg(format_str = "<50s50s", msg_size_bytes = 4, msg_stage = 1, wait_time = 30000):

    i2c_data = bytearray(msg_size_bytes)
    success = False
    t_start = time.ticks()
    elapsed_time = 0

    # Wait_time is divided by two here because this function calls itself, so the overall timeout
    # when list_for_msg() is called will be wait_time. This isn't very good naming but I can't be
    # bothered to deal with it.
    while elapsed_time < (wait_time / 2) and success == False:
        try:
            i2c_obj.recv(i2c_data, addr = 0x12, timeout = 5000)
            print("Received data")
            success = True
        except OSError as err:
            print("Error: " + str(err))
        elapsed_time = time.ticks() - t_start

    if success == False:
        print("Listening failed")
        return -1

    if msg_stage == 1:
        next_msg_size_bytes = ustruct.unpack("<i", i2c_data)[0]
        print("Message received (stage 1): ")
        print(next_msg_size_bytes)
        print("Type: ", type(next_msg_size_bytes))
        packed_msg = listen_for_msg(msg_size_bytes = int(next_msg_size_bytes), msg_stage = 2)
        # If an error occured in stage 2, exit stage 1
        if packed_msg == -1:
            return -1
        return ustruct.unpack(format_str, packed_msg)

    if msg_stage == 2:
        return i2c_data

#################
# This function is responsible for receiving messages and carrying out commands

def receive_msg():
    # Before you know what you're receiving call this function, expecting the first communication
    # to contain details about the 2nd communication. The assumption is this first communication is
    # formatted as '<ss'. If you want to try for longer, specify a longer wait_time.
    print("Listening...")

    received_tuple = listen_for_msg()
    if received_tuple == -1:
        return -1
    next_msg_type_bytes = received_tuple[0]
    next_msg_format_bytes =  received_tuple[1]

    next_msg_type_str = next_msg_type_bytes.decode("ascii")
    next_msg_format_str = next_msg_format_bytes.decode("ascii")

    if next_msg_type_str == "calibration":
        print("Calibration message incoming...")
        # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure,
        # warning_bytes
        calibration_tuple = listen_for_msg(format_str = next_msg_format_str)
        #### CALL CALIBRATION FUNCTION ####
        print("Calibration tuple: ", calibration_tuple)
        #### CALL CALIBRATION FUNCTION ####
        # Check for warnings
        if calibration_tuple[6] != "none":
            print("Calibration Warning: " + calibration_tuple[6])
        return (next_msg_type_str)

    elif next_msg_type_str == "data":
        print("Data message incoming...")
        # data tuple structure: leaf_count_h, leaf_count_u, leaf_health_h, leaf_health_u,
        # plant_ndvi, plant_ir, warning_bytes
        data_tuple = listen_for_msg(format_str = next_msg_format_str)
        #### CALL DATA LOGGING FUNCTION ####
        print("Data tuple: ", data_tuple)
        #### CALL DATA LOGGING FUNCTION ####
        # Check for warnings
        if data_tuple[7] != "none":
            print("Data Warning: " + data_tuple[7])
        # return the next_msg_format_str
        # should evaluate this, and if it's not "<s" you better be ready to send something else
        return (next_msg_type_str)

    elif next_msg_type_str == "trigger":
        #### CALL TRIGGER FUNCTION ####
        return (next_msg_type_str)

    # If we don't recognize the next_msg_type_str, print it and return it so the main can handle it
    else:
        print("Unrecognized message type: " + next_msg_type_str)
        print("Received tuple: ", listen_for_msg(format_str = next_msg_format_str))
        return (next_msg_type_str)

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

    i2c_obj = pyb.I2C(2, pyb.I2C.MASTER)
    i2c_obj.deinit() # Fully reset I2C device...
    i2c_obj = pyb.I2C(2, pyb.I2C.MASTER)

    success = send_calibration()
    print("Success??? = %d" % success)

    msg_type = receive_msg()
    if msg_type != "trigger":
        print("Unexpected msg_type: " + str(msg_type))
    print(msg_type)

    print("Triggering photo regardless...")
    # Wait 42ms and snap photo
    utime.sleep_ms(42)
    img = sensor.snapshot()         # Take a picture and return the image.

    img_hist = img.get_histogram()
    img_stats = img_hist.get_statistics()
    #print(img.compressed_for_ide(quality = 25))

    leaf_thresholds = [(0, 100, -127, img_stats.a_mode() - 2, img_stats.b_mode() + 2, 60)]
    bad_thresholds = [(0, 50, 0, 127, -127, 127)]
    # green is -a, yellow is +b, blue is -b, red is +a

    leaves_mean_a_sum = 0
    a_mean = 0
    blob_found = False

    for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
        blob_found = True
        print("leaf blob found: ")
        print(leaf_blob.rect())
        img.draw_rectangle(leaf_blob.rect(), color = (0, 0, 100))
        leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
        # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
        leaf_rect_pix_a_sum = leaf_rect_stats.a_mean() * leaf_blob[2] * leaf_blob[3]
        leaf_area = leaf_blob[2] * leaf_blob[3]
        for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
            print("bad blob found: ")
            print(bad_blob.rect())
            img.draw_rectangle(bad_blob.rect(), color = (100, 0, 0))
            bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
            # more undoing of mean function
            bad_rect_pix_a_sum = bad_rect_stats.a_mean() * bad_blob[2] * bad_blob[3]
            # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
            leaf_rect_pix_a_sum = leaf_rect_pix_a_sum - bad_rect_pix_a_sum
            # tracking the remaining area of the leaf as the bad_rects are removed
            leaf_area = leaf_area - (bad_blob[2] * bad_blob[3])

        leaf_rect_a_mean = leaf_rect_stats.a_mean()
        leaf_a_mean = leaf_rect_pix_a_sum / leaf_area
        print("leaf a mean = %i [outer a mean = %i]" % (leaf_a_mean, leaf_rect_a_mean))
        # the below function does not take into account the size of a leaf... each leaf is weighted equally
        leaves_mean_a_sum = leaves_mean_a_sum + leaf_a_mean

    # calculates the average value for the healthy leaves regardless of leaf size
    if (blob_found):
        a_mean = leaves_mean_a_sum / (leaf_blob_index + 1)

    sensor.flush()
    utime.sleep_ms(3000)
