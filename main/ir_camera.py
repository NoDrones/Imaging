import sensor, image, time, utime, pyb, ustruct, os, ir_gain, i2c_slave, gc

def send_data(leaf_count = 0, leaf_mean = 0, warning_str = "none"):

	format_str = "<if50s"
	success = i2c_slave.send_next_msg_format(next_msg_type_str = "data", next_msg_format_str = format_str)
	if success == False:
		return -1

	warning_bytes = warning_str.encode('ascii')
	packed_data = ustruct.pack(format_str, leaf_count, leaf_mean, warning_bytes)

	return i2c_slave.send_packed_msg(packed_msg = packed_data)

#################
# Call this function to toggle the flash state, it will return the new flash state.
# The return value is the inverse of the pin value because of the inverting drive circuit
def toggle_flash(): # Call this function to toggle the flash state, it will return the new flash state. The return value is the inverse of the pin value because of the inverting drive circuit
	ir_flash = pyb.Pin("P3", pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
	if ir_flash.value() == 1:
		ir_flash.low() # or p.value(0) to make the pin low (0V)
		return 1
	elif ir_flash.value() == 0:
		ir_flash.high() # or p.value(1) to make the pin high (3.3V)
		return 0
	else:
		return -1

if __name__ == "__main__":

	gc.enable()

	# \/ Setup Camera \/
	sensor.reset()
	sensor.set_pixformat(sensor.GRAYSCALE)
	sensor.set_framesize(sensor.QVGA)
	sensor.skip_frames(time = 2000)
	clock = time.clock()
	# If something that used to work isnt now try using 'VCP+MSC'
	pyb.usb_mode('VCP+HID')
	utime.sleep_ms(1000)
	last_photo_id_path = "last_photo_id.txt"
	last_photo_id_fd = open(last_photo_id_path, "r+")
	img_number_str = last_photo_id_fd.read() # Read image number to file
	if len(img_number_str) == 0: img_number_str = "0" # If no number is read, start at 0
	last_photo_id_fd.close() # Close file

	flash_time_ms = 250 # Set flash_time to be greater than exposure time
	warning = "none"
	calibrated = False
	metadata_str = ""

	leaf_thresholds = [(45, 50), (50, 55), (55, 60), (60, 65), (70, 75), (80, 85), (85, 90), (90, 95), (95, 100), (100, 105), (105, 110), (110, 115), (115, 120), (120, 255)]
	bad_thresholds = [(0, 15), (15, 25), (25, 35), (35, 45)]

	while(1): #Begin the loop that listens for Beaglebone commands
		# since we are expecting a command, we don't need to worry about the second value in tuple (next_msg_format_str)
		command_tuple = i2c_slave.receive_msg()
		if "int" in str(type(command_tuple)):
			command = "none"
		else:
			command = command_tuple[0]

		if "calibrate" in command:
			# Analog gain introduces less noise than digital gain so we maximize it
			sensor.__write_reg(0x4D, 0b11111111)
			sensor.set_auto_gain(False) # must be turned off for color tracking
			sensor.set_auto_whitebal(False) # must be turned off for color tracking
			sensor.set_auto_exposure(False)
			while toggle_flash() != 1: pass # turn flash on for calibration

			if ir_gain.set_custom_exposure() == -1: warning = "set_custom_exposure error"
			while toggle_flash() != 0: pass # turn flash off after calibration

			# Fill metadata_str with calibration information
			new_metadata_tuple = ir_gain.get_gain()
			for morsel in new_metadata_tuple:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str + warning + "\n" #(gain,r_gain,g_gain,b_gain,exposure_value,calibration_warning,"\n")

			new_metadata_list = []

			# Append thresholds to metadata_str - only necessary in color camera since thresholds change
			for i in range(len(leaf_thresholds)):
				for j in range(2):
					new_metadata_list.append(leaf_thresholds[i][j])
			for i in range(len(bad_thresholds)):
				for j in range(2):
					new_metadata_list.append(bad_thresholds[i][j])
			
			# Append thresholds to metadata_str
			for morsel in new_metadata_list:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str[:-1] + "\n"
			calibrated = True

		elif "trigger" in command:
			try:
				msg_type = i2c_slave.receive_msg()[0]
				if "plant_id" in msg_type: plant_id = i2c_slave.listen_for_msg(format_str = "<i")[0]
				else:
					plant_id = 0
					warning = "did not receive plant_id"
			except:
				plant_id = 0
				warning = "did not receive plant_id"

			data_str = ""

			while toggle_flash() != 1: continue # ensures the flash turns on
			utime.sleep_ms(25)
			img = sensor.snapshot() # Take a picture and return the image.
			utime.sleep_ms(int(flash_time_ms - 25))
			while (toggle_flash() != 0): continue # ensures the flash turns off

			# set next_img_number, save raw and jpeg, reload raw
			next_img_number = int(img_number_str) + 1
			last_photo_id_fd = open(last_photo_id_path, "w+") # Open file and truncate
			if last_photo_id_fd.write(str(next_img_number)) < 1: warning = "insufficient next_img_number bytes written" # Write next_img_number
			last_photo_id_fd.close() # Close file

			img_id_str = str(next_img_number) + "_plant_" + str(plant_id)
			raw_str = "raw_" + img_id_str
			raw_write = image.ImageWriter(raw_str)
			raw_write.add_frame(img)
			raw_write.close()

			# save metadata file
			img_metadata_path = "metadata_" + str(next_img_number) + "_plant_" + str(plant_id) + ".txt" # prepare to create metadata file for picture
			img_metadata_fd = open(img_metadata_path, "w+")
			if img_metadata_fd.write(metadata_str) < 1: warning = "insufficient metadata bytes written" # Write metadata to text file
			img_metadata_fd.close() # Close file

			leaf_count = 0
			leaf_area = 0
			leaf_mean = 0
			leaves_mean_sum = 0
			blob_found = False

			leaf_blobs = []
			bad_blobs = []



			##################
			# FIND LEAVES
			##################

			for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(leaf_thresholds, pixels_threshold=100, area_threshold=100, merge = False)):
				blob_found = True
				leaf_blobs.append(leaf_blob)
				leaf_rect_stats = img.get_statistics(roi = leaf_blob.rect())
				leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
				leaf_area = leaf_blob[2] * leaf_blob[3]

				for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=25, area_threshold=25, merge = False, roi = leaf_blob.rect())):
					bad_blobs.append(bad_blob)
					bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
					bad_rect_pix_sum = bad_rect_stats.mean() * bad_blob[2] * bad_blob[3] # more undoing of mean function
					leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
					leaf_area = leaf_area - (bad_blob[2] * bad_blob[3]) # tracking the remaining area of the leaf as the bad_rects are removed

				leaves_mean_sum = leaves_mean_sum + leaf_rect_pix_sum / leaf_area # the below function does not take into account the size of a leaf... each leaf is weighted equally

			if blob_found:
				leaf_count = (leaf_blob_index + 1)
				leaf_mean = leaves_mean_sum / leaf_count

			# Send and save data
			if not send_data(leaf_count = leaf_count, leaf_mean = leaf_mean, warning_str = warning):
				i2c_slave.reinitialize()
				warning = "data send error"
				
			new_data_tuple = (leaf_count, leaf_mean)
			for morsel in new_data_tuple:
				data_str = data_str + str(morsel) + ","
			data_str = data_str + warning + "\n" #(leaf_count, leaf_mean, warning"\n")

			img_data_path = "data_" + str(next_img_number) + "_plant_" + str(plant_id) + ".txt" # prepare to create metadata file for picture
			img_data_fd = open(img_data_path, "w+")
			if img_data_fd.write(data_str) < 1: warning = "insufficient data bytes written" # Write metadata to text file
			img_data_fd.close() # Close file

			print("leaf count = %i; leaf mean = %i" % (leaf_count, leaf_mean))

			sensor.flush()

		else:
			print("No recognizable command, continuing to listen")
