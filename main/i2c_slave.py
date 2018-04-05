import time, utime, pyb, ustruct, gc

gc.enable()
i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
i2c_obj.deinit() # Fully reset I2C device...
i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

def reinitialize():
	try:
		i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
		i2c_obj.deinit() # Fully reset I2C device...
		i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
		return 1
	except:
		return -1

def send_packed_msg(packed_msg):

	packed_next_msg_size = ustruct.pack("<i", len(packed_msg))
	msg_list = [packed_next_msg_size, packed_msg]

	for msg in msg_list:
		attempts, success = 0, False
		while success == False and attempts < 10:
			attempts = attempts + 1
			try:
				i2c_obj.send(msg, timeout=5000)
				success = True
			except:
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

# This function just abstracts the sending of a command to make it more readable in the main
def send_command(command_type = "none"):
	return send_next_msg_format(command_type)

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
			success = True
		except:
			elapsed_time = time.ticks() - t_start

	if success == False: return -1

	if msg_stage == 1:
		next_msg_size_bytes = ustruct.unpack("<i", i2c_data)[0]
		packed_msg = listen_for_msg(msg_size_bytes = int(next_msg_size_bytes), msg_stage = 2)
		if packed_msg == -1: # If an error occured in stage 2, exit stage 1
			return -1
		try:
			return ustruct.unpack(format_str, packed_msg)
		except:
			return -1
			
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
	return (next_msg_type_str, next_msg_format_str)