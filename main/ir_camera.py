import sensor, image, time, utime, pyb, ustruct, os, ir_gain, i2c_slave

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ir = 0, warning_str = "none"):

	format_str = "<2i3f50s"
	success = i2c_slave.send_next_msg_format(next_msg_type_str = "data")
	if success == False:
		return -1

	warning_bytes = warning_str.encode('ascii')
	packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ir, warning_bytes)

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

	healthy_leaf_thresholds, unhealthy_leaf_thresholds, bad_thresholds = (170, 255), (80, 120), (0, 50)
	flash_time_ms = 250 # Set flash_time to be greater than exposure time
	warning = "none"
	calibrated = False
	metadata_str = ""

	while(1): #Begin the loop that listens for Beaglebone commands
		# since we are expecting a command, we don't need to worry about the second value in tuple (next_msg_format_str)
		command = i2c_slave.receive_msg()[0]

		if "calibrate" in command:
			# Analog gain introduces less noise than digital gain so we maximize it
			sensor.__write_reg(0x4D, 0b11111111)
			while toggle_flash() != 1: pass # turn flash on for calibration
			sensor.set_auto_gain(False) # must be turned off for color tracking
			sensor.set_auto_whitebal(False) # must be turned off for color tracking
			sensor.set_auto_exposure(False)

			if ir_gain.set_custom_exposure() == -1: warning = "set_custom_exposure error"
			while toggle_flash() != 0: pass # turn flash off after calibration

			# Fill metadata_str with calibration information
			new_metadata_tuple = ir_gain.get_gain()
			for morsel in new_metadata_tuple:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str + warning + "\n" #(gain,r_gain,g_gain,b_gain,exposure_value,calibration_warning,"\n")

			# Append thresholds to metadata_str
			new_metadata_tuple = (healthy_leaf_thresholds[0], healthy_leaf_thresholds[1], unhealthy_leaf_thresholds[0], unhealthy_leaf_thresholds[1], bad_thresholds[0], bad_thresholds[1])
			for morsel in new_metadata_tuple:
				metadata_str = metadata_str + str(morsel) + ","
			metadata_str = metadata_str[:-1] + "\n" #(healthy_leaf_thresholds_lo,healthy_leaf_thresholds_hi,unhealthy_leaf_thresholds_lo,unhealthy_leaf_thresholds_hi,bad_thresholds_lo,bad_thresholds_hi,"\n")
			calibrated = True

		elif "trigger" in command:

			# is this the best way to get the plant_id?
			(msg_type, next_msg_format_str) = i2c_slave.receive_msg()
			if "plant_id" in msg_type: plant_id = i2c_slave.listen_for_msg(format_str = next_msg_format_str)[0]
			else: 
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

			img_hist = img.get_histogram()
			img_stats = img_hist.get_statistics()

			healthy_leaves_mean_sum, unhealthy_leaves_mean_sum = 0, 0
			healthy_leaves, unhealthy_leaves = 0, 0
			healthy_mean, unhealthy_mean = 0, 0
			blob_found, leaf_blob_index = False, 0

			for leaf_blob_index, leaf_blob in enumerate(img.find_blobs([healthy_leaf_thresholds], pixels_threshold=200, area_threshold=200, merge = False)):
				blob_found = True
				print("leaf blob found: " + str(leaf_blob.rect()))
				img.draw_rectangle(leaf_blob.rect(), color = 255)
				leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
				leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
				leaf_area = leaf_blob[2] * leaf_blob[3]

				for bad_blob_index, bad_blob in enumerate(img.find_blobs([bad_thresholds], pixels_threshold=50, area_threshold=50, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
					print("bad blob found: " + str(bad_blob.rect()))
					img.draw_rectangle(bad_blob.rect(), color = 127)
					bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
					bad_rect_pix_sum = bad_rect_stats.mean() * bad_blob[2] * bad_blob[3] # more undoing of mean function
					leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
					leaf_area = leaf_area - (bad_blob[2] * bad_blob[3]) # tracking the remaining area of the leaf as the bad_rects are removed

				print("healthy leaf mean = %i [outer mean = %i]" % (leaf_rect_pix_sum / leaf_area, leaf_rect_stats.mean()))
				healthy_leaves_mean_sum = healthy_leaves_mean_sum + leaf_rect_pix_sum / leaf_area # the below function does not take into account the size of a leaf... each leaf is weighted equally

			# calculates the average value for the healthy leaves regardless of leaf size
			if (blob_found == True):
				healthy_mean = healthy_leaves_mean_sum / (leaf_blob_index + 1)

			healthy_leaves = (leaf_blob_index + 1)
			blob_found = False

			for leaf_blob_index, leaf_blob in enumerate(img.find_blobs([unhealthy_leaf_thresholds], pixels_threshold=200, area_threshold=200, merge = False)):
				blob_found = True
				print("leaf blob found: " + str(leaf_blob.rect()))
				img.draw_rectangle(leaf_blob.rect(), color = 255)
				leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
				leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
				leaf_area = leaf_blob[2] * leaf_blob[3]
				for bad_blob_index, bad_blob in enumerate(img.find_blobs([bad_thresholds], pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
					print("bad blob found: ", bad_blob.rect())
					img.draw_rectangle(bad_blob.rect(), color = 127)
					bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
					bad_rect_pix_sum = bad_rect_stats.mean()*bad_blob[2]*bad_blob[3] # more undoing of mean function
					leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
					leaf_area = leaf_area - (bad_blob[2] * bad_blob[3]) # tracking the remaining area of the leaf as the bad_rects are removed

				print("unhealthy leaf mean = %i [outer mean = %i]" % (leaf_rect_pix_sum / leaf_area, leaf_rect_stats.mean()))
				unhealthy_leaves_mean_sum = unhealthy_leaves_mean_sum + leaf_rect_pix_sum / leaf_area # the below function does not take into account the size of a leaf... each leaf is weighted equally

			if (blob_found == True): # calculates the average value for the unhealthy leaves regardless of leaf size
				unhealthy_mean = unhealthy_leaves_mean_sum / (leaf_blob_index + 1)
				unhealthy_leaves = (leaf_blob_index + 1)

			overall_ir =  ((healthy_leaves * healthy_mean) + (unhealthy_leaves * unhealthy_mean)) / (healthy_leaves + unhealthy_leaves)

			# Send and save data
			send_data(leaf_count = (healthy_leaves, unhealthy_leaves), leaf_health = (healthy_mean, unhealthy_mean), plant_ir = overall_ir, warning_str = warning)
			new_data_tuple = (healthy_leaves, unhealthy_leaves, healthy_mean, unhealthy_mean, overall_ir)
			for morsel in new_data_tuple:
				data_str = data_str + str(morsel) + ","
			data_str = data_str + warning + "\n" #(gain,r_gain,g_gain,b_gain,exposure_value,calibration_warning,"\n")

			img_data_path = "data_" + str(next_img_number) + "_plant_" + str(plant_id) + ".txt" # prepare to create metadata file for picture
			img_data_fd = open(img_data_path, "w+")
			if img_data_fd.write(data_str) < 1: warning = "insufficient data bytes written" # Write metadata to text file
			img_data_fd.close() # Close file

			print("healthy mean = %i; unhealthy mean = %i" % (healthy_mean, unhealthy_mean))

			sensor.flush()
		else:
			print("No recognizable command, continuing to listen")