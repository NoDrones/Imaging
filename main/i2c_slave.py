import utime, pyb, ustruct

i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
i2c_obj.deinit() # Fully reset I2C device...
i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

def send_packed_msg(packed_msg):

    packed_next_msg_size = ustruct.pack("<i", len(packed_msg)) # alternative for size calcs incase this doesnt work `PyBytes_Size(packed_msg)`
    msg_list = [packed_next_msg_size, packed_msg]

    for msg in msg_list:
        attempts, success = 0, False
        while success == False and attempts < 5:
            print("Sending message. Attempt # %i" % attempts) # Attempt to send packed data with 5 second timeout
            attempts = attempts + 1
            try:
                i2c_obj.send(msg, timeout=5000)
                print("Message sent...")
                success = True
            except OSError as err:
                print("Error: " + str(err))
                pass # Don't care about errors - so pass. # Note that there are 3 possible errors. A timeout error, a general purpose error, or a busy error. The error codes are 116, 5, 16 respectively for "err.arg[0]".

        if success == False: return -1
    return 1


# Default next_msg_format_str is the one used to unpack this message || Default next_msg_type_str is the one that matches this message
def send_next_msg_format(next_msg_type_str = "format", next_msg_format_str = "<50s"):

    next_msg_type_bytes = next_msg_type_str.encode('ascii')
    next_msg_format_bytes = next_msg_format_str.encode('ascii')

    # Both receiver and sender should always append an additional string and integer to the format
    # This will always be the expected format str and byte size for the next message
    format_str = "<50s50s"
    packed_next_msg_format = ustruct.pack(format_str, next_msg_type_bytes, next_msg_format_bytes)

    return send_packed_msg(packed_msg = packed_next_msg_format)

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
    # when list_for_msg() is called will be wait_time. This isn't very good naming but I can't be bothered to deal with it.
    while elapsed_time < (wait_time / 2) and success == False:
        try:
            i2c_obj.recv(i2c_data, timeout = 5000)
            print("Received data (stage %i)" % msg_stage)
            success = True
        except OSError as err:
            print("Error: " + str(err))
            elapsed_time = time.ticks() - t_start

    if success == False: return -1

    if msg_stage == 1:
        next_msg_size_bytes = ustruct.unpack("<i", i2c_data)[0]
        packed_msg = listen_for_msg(msg_size_bytes = int(next_msg_size_bytes), msg_stage = 2)
        if packed_msg == -1: # If an error occured in stage 2, exit stage 1
            return -1
            return ustruct.unpack(format_str, packed_msg)

    if msg_stage == 2: return i2c_data

# This function is responsible for receiving messages and carrying out commands
# Before you know what you're receiving call this function, expecting the first communication
# to contain details about the 2nd communication. The assumption is this first communication is
# formatted as '<ss'. If you want to try for longer, specify a longer wait_time.
def receive_msg():

    received_tuple = listen_for_msg()
    if received_tuple == -1: return -1
    next_msg_type_bytes = received_tuple[0]
    next_msg_format_bytes =  received_tuple[1]
    next_msg_type_str = next_msg_type_bytes.decode("ascii")
    next_msg_format_str = next_msg_format_bytes.decode("ascii")

    if "calibration" in next_msg_type_str:
        print("Calibration message incoming...")
        calibration_tuple = listen_for_msg(format_str = next_msg_format_str) # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure, warning_bytes
        calibration_list = list(calibration_tuple)
        calibration_list[-1] = calibration_list[-1].decode('ascii').rstrip('\x00') # strip extra bytes from end of warning string, which is the last value in the list
        #### CALL CALIBRATION FUNCTION ####
        print("Calibration list: ", calibration_list)
        #### CALL CALIBRATION FUNCTION ####
        if "none" not in calibration_list[-1]: print("Calibration Warning: " + calibration_list[-1].decode('ascii')) # Check for warnings
        return (next_msg_type_str)

    elif "data" in next_msg_type_str:
        print("Data message incoming...")
        data_tuple = listen_for_msg(format_str = next_msg_format_str) # data tuple structure: leaf_count_h, leaf_count_u, leaf_health_h, leaf_health_u, plant_ndvi, plant_ir, warning_bytes
        data_list = list(data_tuple)
        data_list[-1] = data_list[-1].decode('ascii').rstrip('\x00') # strip extra bytes from end of warning string, which is the last value in the list
        #### CALL DATA LOGGING FUNCTION ####
        print("Data list: ", data_list)
        #### CALL DATA LOGGING FUNCTION ####
        if "none" not in data_list[-1]: print("Data Warning: " + data_list[-1].decode('ascii')) # Check for warnings
        return (next_msg_type_str) # return the next_msg_format_str # should evaluate this, and if it's not "<s" you better be ready to send something else

    elif "trigger" in next_msg_type_str:
        #### CALL TRIGGER FUNCTION ####
        return (next_msg_type_str)

    else: # If we don't recognize the next_msg_type_str, print it and return it so the main can handle it
        print("Unrecognized message type: " + next_msg_type_str + "\n" + "Received tuple: " +  str(listen_for_msg(format_str = next_msg_format_str)))
        return (next_msg_type_str)