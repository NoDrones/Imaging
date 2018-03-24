import sensor, image, time, utime, pyb, ustruct, os

#################
# Returns Overall Gain in DB

def get_gain():
    gain_reg_val = sensor.__read_reg(0x00)
    #print("gain_reg_val: " + str(gain_reg_val))
    bitwise_gain_range = (gain_reg_val & 0b11110000) >> 4 #get the highest four bits which correspond to gain range. Depends on the bits set. Can be 0 > 4 for a total of 5 ranges.
    #print("bitwise_gain_range: " + str(bin(bitwise_gain_range)))
    gain_range = ((bitwise_gain_range & 0b1000) >> 3) + ((bitwise_gain_range & 0b0100) >> 2) + ((bitwise_gain_range & 0b0010) >> 1) + (bitwise_gain_range & 0b0001) #get an int for the number of bits set
    #print("read_gain_range: " + str(gain_range))
    gain_LSBs = gain_reg_val & 0b00001111 #The 4 lsbs represent the fine tuning gain control.
    #print("gain_LSBs: " + str(gain_LSBs))
    gain_curve_index = 16 * gain_range + gain_LSBs # this gives you an index from 0 > 79 which is the range of points you need to describe every possible gain setting along the new gain curve
    #print("gain_curve_index: " + str(gain_curve_index))
    gain = 10 ** (30 * gain_curve_index / 79 / 20) #10** = 10 ^, calculate the gain along the new exponential gain curve I defined earlier on
    #print("gain: " + str(gain))
    #g = sensor.__read_reg(0x01)
    #print(g)
    #utime.sleep_ms(1000)

    #t = 0b00000100 & g
    #print(t)
    #utime.sleep_ms(1000)

    if ((0b00000100 & sensor.__read_reg(0x5C)) == 0):
        b_gain = sensor.__read_reg(0x01) / 0x40
        r_gain = sensor.__read_reg(0x02) / 0x40
        g_gain = sensor.__read_reg(0x03) / 0x40
    else:
        b_gain = sensor.__read_reg(0x01) / 0x80
        r_gain = sensor.__read_reg(0x02) / 0x80
        g_gain = sensor.__read_reg(0x03) / 0x80

    return (gain, r_gain, g_gain, b_gain)

#################
#

def set_gain(gain_db):
    # gain_correlation_equation = 20*log(gain_db) = 30*(index)/79
    gain_curve_index = (79 * 20 * math.log(gain_db, 10)) / 30 #return an index from the new exponential gain curve...
    #... Can be 0 > 79 which is the # of points needed to describe every gain setting along the new curve
    #print("gain_curve_index: " + str(gain_curve_index))
    gain_range = int(gain_curve_index/16) #find a 0 > 4 value for the gain range. This range is defined by the 4 msbs. Thus we divide and round down by the LSB of the 4 MSBs (16)
    #print("gain_range: " + str(gain_range))
    gain_LSBs = int(gain_curve_index - 16 * gain_range) & 0b00001111 #Find how many LSBs above the gain range the index is. This is your fine tuning gain control
    #print("gain_LSBs: " + str(bin(gain_LSBs)))
    bitwise_gain_range = (0b1111 << gain_range) & 0b11110000 #make the gain range bitwise
    #print("bitwise_gain_range: " + str(bin(bitwise_gain_range)))
    gain_reg_val = bitwise_gain_range | gain_LSBs #OR
    #print("gain to set: " + str(bin(gain_reg_val)))
    sensor.__write_reg(0x00, gain_reg_val)
    return gain_reg_val

#################
#

def set_custom_exposure(high_mean_thresh = 65, low_mean_thresh = 55):
    try:
        print("Starting Exposure Adjustment...")
        cur_gain = get_gain()[0]
        #b_gain_raw = sensor.__read_reg(0x01)
        #r_gain_raw = sensor.__read_reg(0x02)
        #g_gain_raw = sensor.__read_reg(0x03)
        #r_gain_raw = round(r_gain/4)
        #g_gain_raw = round(g_gain/4)
        #b_gain_raw = round(b_gain/4)
        #sensor.__write_reg(0x01, b_gain_raw)
        #sensor.__write_reg(0x02, r_gain_raw)
        #sensor.__write_reg(0x03, g_gain_raw)

        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        mean = img_stats.mean()
        count = 0

        while(((mean > high_mean_thresh) | (mean < low_mean_thresh))) & (count < 256) & (cur_gain >= 0):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            mean = img_stats.mean()

            if ((cur_gain < 1) | (cur_gain > 32)):
                break

            if mean > high_mean_thresh:
                new_gain = cur_gain - .1
            elif mean < low_mean_thresh:
                new_gain = cur_gain + .1
            else:
                break #we're in the range now!

            set_gain(new_gain)
            cur_gain = new_gain
            count += 1

        if (count < 310) | (cur_gain == 0):
            print("Exposure Adjustment Complete.")
            return mean
        else:
            print("Exposure Adjustment Incomplete.")
            return -1

    except Exception as e:
        print(e)
        print("Error occured!")
        return -2

#################
# This send function takes packed data, calculates the size, sends that first, then sends the data
# This means the receiver is always looking for a format "<i" before next_msg_format

def send_packed_msg(packed_msg, max_attempts = 5):

    # alternative for size calcs incase this doesnt work `PyBytes_Size(packed_msg)`
    packed_next_msg_size = ustruct.pack("<i", len(packed_msg))
    msg_list = [packed_next_msg_size, packed_msg]

    for msg in msg_list:
        attempts = 0
        success = False
        while success == False and attempts < max_attempts:
            print("Sending message. Attempt # %i" % attempts)
            # Attempt to send packed data with 5 second timeout
            attempts = attempts + 1
            try:
                i2c_obj.send(msg, timeout=5000)
                print("Message sent...")
                success = True
            except OSError as err:
                print("Error: " + str(err))
                utime.sleep_ms(100)
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


    return send_packed_msg(packed_msg = packed_next_msg_format)

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call
# send_next_msg_format() at the begining of each communication it is unneccesary. Only specify this
# variable if you plan on sending a custom message without calling send_next_msg_format() first.

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0, warning_str = "none"):

    format_str = "<2i4f50s"
    success = send_next_msg_format(next_msg_type_str = "data")
    if success == False:
        return -1

    warning_bytes = warning_str.encode('ascii')
    print("leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir:")
    print(leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir)

    packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir, warning_bytes)

    return send_packed_msg(packed_msg = packed_data)

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

    return send_packed_msg(packed_msg = packed_calibration)

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
            i2c_obj.recv(i2c_data, timeout = 5000)
            print("Received data (stage %i)" % msg_stage)
            success = True
        except OSError as err:
            print("Error: " + str(err))
        elapsed_time = time.ticks() - t_start

    if success == False:
        print("Listening failed")
        return -1

    if msg_stage == 1:
        next_msg_size_bytes = ustruct.unpack("<i", i2c_data)[0]
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

    if "calibration" in next_msg_type_str:
        print("Calibration message incoming...")
        # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure,
        # warning_bytes
        calibration_tuple = listen_for_msg(format_str = next_msg_format_str)
        calibration_list = list(calibration_tuple)
        # strip extra bytes from end of warning string, which is the last value in the list
        calibration_list[-1] = calibration_list[-1].decode('ascii').rstrip('\x00')
        #### CALL CALIBRATION FUNCTION ####
        print("Calibration list: ", calibration_list)
        #### CALL CALIBRATION FUNCTION ####
        # Check for warnings
        if "none" not in calibration_list[-1]:
            print("Calibration Warning: " + calibration_list[-1].decode('ascii'))
        return (next_msg_type_str)

    elif "data" in next_msg_type_str:
        print("Data message incoming...")
        # data tuple structure: leaf_count_h, leaf_count_u, leaf_health_h, leaf_health_u,
        # plant_ndvi, plant_ir, warning_bytes
        data_tuple = listen_for_msg(format_str = next_msg_format_str)
        data_list = list(data_tuple)
        # strip extra bytes from end of warning string, which is the last value in the list
        data_list[-1] = data_list[-1].decode('ascii').rstrip('\x00')
        #### CALL DATA LOGGING FUNCTION ####
        print("Data list: ", data_list)
        #### CALL DATA LOGGING FUNCTION ####
        # Check for warnings
        if "none" not in data_list[-1]:
            print("Data Warning: " + data_list[-1].decode('ascii'))
        # return the next_msg_format_str
        # should evaluate this, and if it's not "<s" you better be ready to send something else
        return (next_msg_type_str)

    elif "trigger" in next_msg_type_str:
        #### CALL TRIGGER FUNCTION ####
        return (next_msg_type_str)

    # If we don't recognize the next_msg_type_str, print it and return it so the main can handle it
    else:
        print("Unrecognized message type: " + next_msg_type_str)
        print("Received tuple: ", listen_for_msg(format_str = next_msg_format_str))
        return (next_msg_type_str)

#################
# Call this function to toggle the flash state, it will return the new flash state
# The return value is the inverse of the pin value because of the inverting drive circuit

def toggle_flash():
    # \/ This is the code to define a Pin, make it an output and set it high/low \/
    ir_flash = pyb.Pin("P3", pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
    if ir_flash.value() == 1:
        ir_flash.low()            # or p.value(0) to make the pin low (0V)
        return 1
    elif ir_flash.value() == 0:
        ir_flash.high()           # or p.value(1) to make the pin high (3.3V)
        return 0
    else:
        print("I can't let you do that Dave")
    return -1

##################
#def exposure_time_us():
    #return global exposure_time_us
##################
#def r_gain():
    #return global r_gain
##################
#def g_gain():
    #return global g_gain
##################
#def b_gain():
    #return global b_gain
##################
#def overall_gain():
    #return global overall_gain
##################

if __name__ == "__main__":

    exposure_time_us = 4200
    r_gain = 4
    g_gain = 4
    b_gain = 4
    overall_gain = 7

    # \/ Setup Camera \/

    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time = 2000)
    clock = time.clock()

    # Analog gain introduces less noise than digital gain, we should use this before anything else
    #print("Initial analog gain register = " + bin(sensor.__read_reg(0x4D)))
    #print("Maxing out analog gain register and setting AWB/AGC...")
    ##sensor.__write_reg(0x4D, 0b11111111)
    #print("Analog gain register pre AWB/AGC setting = " + bin(sensor.__read_reg(0x4D)))

    sensor.set_auto_gain(False, gain_db = overall_gain) # must be turned off for color tracking
    sensor.set_auto_whitebal(False, rgb_gain_db = (r_gain, g_gain, b_gain)) # must be turned off for color tracking
    sensor.set_auto_exposure(False, exposure_us = exposure_time_us)

    # Analog gain introduces less noise than digital gain, we should use this before anything else
    print("Analog gain register post AWB/AGC setting = " + bin(sensor.__read_reg(0x4D)))
    # Now set the exposure
    set_custom_exposure()

    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
    i2c_obj.deinit() # Fully reset I2C device...
    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

    # ensure flash is off
    while toggle_flash() != 0:
        pass

    # \/ Receive Calibration \/

    # Calling receive_message will also trigger action if directed by sender, such as performing
    # calibration, or passing on/storing data, or taking a photo/flashing the light source
    # The returned msg_type can be used to verify the expected action took place if desired, and
    # react if necessary (such as repeat a process)

    # IR camera waits for calibration directions from the color camera
    msg_type = receive_msg()
    if msg_type == -1:
        print("Could not receive message.")
    elif "calibration" not in msg_type:
        print("Unexpected msg_type: " + str(msg_type))

    # \/ Take Photo \/

    # Set flash_time based on exposure time
    flash_time_ms = (exposure_time_us / 1000) + 50

    # Trigger light source/color camera
    if send_trigger() == -1:
        print("Trigger unsuccessful")

    # ensures the flash turns on
    while toggle_flash() != 1:
        continue

    # take a picture
    utime.sleep_ms(25)
    img = sensor.snapshot()         # Take a picture and return the image.
    utime.sleep_ms(int(flash_time_ms - 25))

    # ensures the flash turns off
    while toggle_flash() != 0:
        continue

    # \/ Name & Save Image \/

    # Save raw image, save compressed image, load back in raw image for processing. It is necessary
    # we reload the raw image because compressing it (needed for saving jpeg) overwrites the raw
    # file in the heap, and the heap can't handle two pictures so we then have to reload it.

    # should pull img_number from a text file and read the plant_id from a qr code or beaglebone
    # default mode is pyb.usb_mode('VCP+MSC')
    pyb.usb_mode('VCP+HID')
    utime.sleep_ms(1000)
    last_photo_id_path = "last_photo_id.txt"
    last_photo_id_fd = open(last_photo_id_path, "w+")
    img_number_str = last_photo_id_fd.read()
    print(img_number_str)
    img_number_str = last_photo_id_fd.write("696969")
    print("Written bytes: " + str(img_number_str))
    img_number_str = last_photo_id_fd.read()
    print(img_number_str)
    last_photo_id_fd.close()

    # find the image number, source plant number from beaglebone
    img_number = 4
    plant_id = 1
    img_id = str(img_number) + "plant_" + str(plant_id)
    raw_str = "raw_" + str(img_id)
    raw_write = image.ImageWriter(raw_str)
    raw_write.add_frame(img)
    raw_write.close()

    # save a jpeg
    img.compress(quality = 100)
    img.save("img_" + str(img_id))

    # reload the raw
    raw_read = image.ImageReader(raw_str)
    img = raw_read.next_frame(copy_to_fb = True, loop = False)
    raw_read.close()

    # \/ Analyze Image \/

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
    leaf_blob_index = 0

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
    healthy_leaves = (leaf_blob_index + 1)

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
        # the below function does not take into account the size of a leaf... each leaf is weighted
        # equally
        unhealthy_leaves_mean_sum = unhealthy_leaves_mean_sum + leaf_mean

    # calculates the average value for the unhealthy leaves regardless of leaf size
    if (blob_found == True):
        unhealthy_mean = unhealthy_leaves_mean_sum / (leaf_blob_index + 1)
    unhealthy_leaves = (leaf_blob_index + 1)

    overall_ir =  ((healthy_leaves * healthy_mean) + (unhealthy_leaves * unhealthy_mean)) / (healthy_leaves + unhealthy_leaves)

    # \/ Save Data & Send \/

    send_data(leaf_count = (healthy_leaves, unhealthy_leaves), leaf_health = (healthy_mean, unhealthy_mean), plant_ndvi = 0, plant_ir = overall_ir, warning_str = "none")

    print("healthy mean = %i; unhealthy mean = %i" % (healthy_mean, unhealthy_mean))
    if (unhealthy_mean < 135):
        print("You got some seriously unhealthy leafage there, figure it out")
    elif (unhealthy_mean < 145):
        print("Some leaves are unhappy, although they're soldiering on")
    else:
        print("Even your unhealthy leaves are healthy!")

    sensor.flush()
    utime.sleep_ms(3000)
