import sensor, image, time, utime, pyb, ustruct, os, color_gain, i2c_master,usb_comms

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0, warning_str = "none"):

	format_str = "<2i4f50s"
	success = i2c_master.send_next_msg_format(next_msg_type_str = "data")
	if success == False:
		return -1

	warning_bytes = warning_str.encode('ascii')
	packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir, warning_bytes)

	return i2c_master.send_packed_msg(packed_msg = packed_data)

#################
# Call this function to toggle the flash state, it will return the new flash state.
# The return value is the inverse of the pin value because of the inverting drive circuit
def toggle_flash():
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

	# \/ Setup Camera \/

# \/ Setup Camera \/
	sensor.reset()
	sensor.set_pixformat(sensor.RGB565)
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

	# green is -a, yellow is +b, blue is -b, red is +a
	leaf_thresholds = (25, 100, -127, -3, -15, 3)
	bad_thresholds = (20, 100, -10, 127, 3, 127)
	flash_time_ms = 250 # Set flash_time to be greater than exposure time
	warning = "none"
	calibrated = False
	metadata_str = ""

	while(1): #Begin the loop that listens for Beaglebone commands
		command = usb_comms.listen_for_trigger()

		#################################################################
		### CALIBRATION TRIGGER
		#################################################################

		if command == 'calibrate':

			# \/ Send Calibrate Command \/

			success = i2c_master.send_command(command_type = "calibrate")
			if success == -1: print("calibrate command send failed")

			# Analog gain introduces less noise than digital gain so we maximize it
			sensor.__write_reg(0x4D, 0b11111111)
			while toggle_flash() != 1: pass # turn flash on for calibration

			sensor.set_auto_gain(False)
			sensor.set_auto_whitebal(False)
			sensor.set_auto_exposure(False)
			if color_gain.set_custom_exposure() != -1: calibrated = True # Now set the exposure
			else: print("Could not complete calibration")

			while toggle_flash() != 0: pass # turn flash off after calibration

			# receive what we expect to be calibration values
			(msg_type, msg_format) = i2c_master.receive_msg()
			if msg_type == -1:
				print("Could not receive message.")
			elif "calibration_values" not in msg_type:
				print("Unexpected msg_type: " + str(msg_type))
			else:
				ir_calibration_tuple = listen_for_msg(format_str = next_msg_format_str) # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure, warning_bytes
				ir_calibration_list = list(ir_calibration_tuple)
				# check warning bytes
				ir_calibration_list[-1] = ir_calibration_list[-1].decode('ascii').rstrip('\x00')
				if 'none' not in ir_calibration_list[-1]:
					print("Calibration Warning Received: " + ir_calibration_list[-1])

			# Fill metadata_str with calibration information
			new_metadata_tuple = color_gain.get_gain()
			for morsel in new_metadata_tuple:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str + warning + "\n" #(gain,r_gain,g_gain,b_gain,exposure_value,calibration_warning,"\n")

			# Append thresholds to metadata_str - only necessary in color camera since thresholds change
			new_metadata_tuple = (leaf_thresholds[0], leaf_thresholds[1], leaf_thresholds[2], leaf_thresholds[3], leaf_thresholds[4], leaf_thresholds[5], bad_thresholds[0], bad_thresholds[1], bad_thresholds[2], bad_thresholds[3], bad_thresholds[4], bad_thresholds[5])
			for morsel in new_metadata_tuple:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str[:-1] + "\n" #(leaf_thresholds_l_lo,leaf_thresholds_l_hi,leaf_thresholds_a_lo,leaf_thresholds_a_hi,leaf_thresholds_b_lo,leaf_thresholds_b_hi,bad_threshold_l_lo,bad_threshold_l_hi,bad_threshold_a_lo,bad_threshold_a_hi,bad_threshold_b_lo,bad_threshold_b_hi)

			calibrated = True

			# TODO: Write color calibration data to sd card

			success = usb_comms.send_msg('@20s',(b'Calibration Complete',))
			if success == 1:
				continue

		############################################
		### PHOTO & DATA COLLECTION TRIGGER
		############################################
		elif command == 'trigger':

			if calibrated != True: print("Not calibrated!!!")

			# \/ Take Photo \/

			success = i2c_master.send_command(command_type = "trigger")
			if success == -1: print("trigger command send failed")

			while toggle_flash() != 1: pass # turn flash on
			shutter_start = time.ticks()
			utime.sleep_ms(25)
			img = sensor.snapshot() # take a picture
			while time.ticks() < (shutter_start + flash_time_ms): pass
			while toggle_flash() != 0: pass # turn flash off

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

			img.compress(quality = 100)
			# Send image back to beaglebone

			# reload raw
			raw_read = image.ImageReader(raw_str)
            img = raw_read.next_frame(copy_to_fb = True, loop = False)
            raw_read.close()

			# save metadata file
			img_metadata_path = "metadata_" + str(next_img_number) + "_plant_" + str(plant_id) + ".txt" # prepare to create metadata file for picture
			img_metadata_fd = open(img_metadata_path, "w+")
			if img_metadata_fd.write(metadata_str) < 1: warning = "insufficient metadata bytes written" # Write metadata to text file
			img_metadata_fd.close() # Close file

			# receive ir_data before continuing
			(msg_type, next_msg_format_str) = i2c_master.receive_msg()
			if msg_type == -1: warning = "i2c error"
			elif "data" not in msg_type: warning = "error receiving data"
			else:
				ir_data_tuple = listen_for_msg(format_str = next_msg_format_str) # calibration tuple structure: overall_gain, r_gain, b_gain, g_gain, exposure, warning_bytes
				ir_data_list = list(ir_data_tuple)
				# check warning bytes
				ir_data_list[-1] = data_list[-1].decode('ascii').rstrip('\x00')
				if 'none' not in ir_data_list[-1]:
					warning = "ir data warning: " + ir_data_list[-1]

			# now perform measurements on your own image
			img_hist = img.get_histogram()
			img_stats = img_hist.get_statistics()

			leaves_mean_a_sum = 0
			a_mean = 0
			blob_found = False

			for leaf_blob_index, leaf_blob in enumerate(img.find_blobs([leaf_thresholds], pixels_threshold=200, area_threshold=200, merge = False)):
				blob_found = True
				print("leaf blob found: ")
				print(leaf_blob.rect())
				img.draw_rectangle(leaf_blob.rect(), color = (0, 0, 100))
				leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
				# want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
				leaf_rect_pix_a_sum = leaf_rect_stats.a_mean() * leaf_blob[2] * leaf_blob[3]
				leaf_area = leaf_blob[2] * leaf_blob[3]
				for bad_blob_index, bad_blob in enumerate(img.find_blobs([bad_thresholds], pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
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
			leaf_count = leaf_blob_index + 1
			if (blob_found): a_mean = leaves_mean_a_sum / (leaf_count)

			# Send and save data
			new_data_tuple = (a_mean, lead_count)
			for morsel in new_data_tuple:
				data_str = data_str + str(morsel) + ","
			data_str = data_str + warning + "\n" #(gain,r_gain,g_gain,b_gain,exposure_value,calibration_warning,"\n")

			# Send data back to beaglebone (new_data_tuple, ir_data_list)

			img_data_path = "data_" + str(next_img_number) + "_plant_" + str(plant_id) + ".txt" # prepare to create metadata file for picture
			img_data_fd = open(img_data_path, "w+")
			if img_data_fd.write(data_str) < 1: warning = "insufficient data bytes written" # Write metadata to text file
			img_data_fd.close() # Close file

			sensor.flush()

		else:
			success = usb_comms.send_msg('@22s',(b'Command Not Recognized',))
			continue
