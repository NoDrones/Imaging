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
# In general you shouldn't specify next_msg_format_str - as long as we always call send_msg_format()
# at the begining of each communication it is unneccesary. Only specify this variable if you plan on
# sending a custom message after without calling send_msg_format() first.
def send_calibration(warning_str = "none"):

	format_str = "<4fi50s"
	success = i2c_master.send_next_msg_format(next_msg_type_str = "calibration", next_msg_format_str = format_str)
	if success == False: return -1

	warning_bytes = warning_str.encode('ascii')
	(overall_gain, r_gain, g_gain, b_gain, exposure_value) = color_gain.get_gain()
	packed_calibration = ustruct.pack(format_str + "s", overall_gain, r_gain, g_gain, b_gain, exposure_value, warning_bytes)

	return i2c_master.send_packed_msg(packed_msg = packed_calibration)

#################
# This function only utilizes the first half of our normal message protocol, send_next_msg_format() is just a flag
# to prepare the reciever for whatever comes next, for a trigger this flag is all we need.
def send_trigger():
	# Don't need to specify a next_msg_format_str because this message is treated differently
	success = i2c_master.send_next_msg_format(next_msg_type_str = "trigger")
	if success == False: return -1
	return 1

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

<<<<<<< HEAD
	# \/ Setup Camera \/

	sensor.reset()
	sensor.set_pixformat(sensor.RGB565)
	sensor.set_framesize(sensor.QVGA)
	sensor.skip_frames(time = 2000)
	clock = time.clock()

	while(1): #Begin the loop that listens for Beaglebone commands
		command = usb_comms.listen_for_trigger()

		#################################################################
		### CALIBRATION TRIGGER 
		#################################################################
		
		if command=='Calibrate':
			# Analog gain introduces less noise than digital gain so we maximize it
			sensor.__write_reg(0x4D, 0b11111111)
			sensor.set_auto_gain(False) # must be turned off for color tracking
			sensor.set_auto_whitebal(False) # must be turned off for color tracking
			sensor.set_auto_exposure(False)

			while toggle_flash() != 1: pass # turn flash on for calibration
			color_gain.set_custom_exposure() # Now set the exposure
			while toggle_flash() != 0: pass # turn flash off after calibration

			# ensure flash is off
			while toggle_flash() != 0:
				continue

			# \/ Send Calibration & Wait \/

			success = send_calibration()
			print("Failed to send calibration." if success == -1 else "Calibration sent.")

			# Flash_time should be based on exposure time
			flash_time_ms = 250

			# receive what we expect to be a trigger
			msg_type = i2c_master.receive_msg()
			if msg_type == -1:
				print("Could not receive message.")
			elif "trigger" not in msg_type:
				print("Unexpected msg_type: " + str(msg_type))
			
			
			success = usb_comms.send_msg('@20s',(b'Calibration Complete',))
			if success==1:
				continue

		############################################
		### PHOTO & DATA COLLECTION TRIGGER
		############################################
		elif command=='Go':
					
			# \/ Take Photo \/

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

			# \/ Get Data \/

			# receive ir_data before continuing
			msg_type = i2c_master.receive_msg()
			if msg_type == -1:
				print("Could not receive message.")
			elif "data" not in msg_type:
				print("Unexpected msg_type: " + str(msg_type))

			# now perform measurements on your own image
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

			##############SAVE DATA AND IMAGE TO SD CARD###############
			##############SAVE DATA AND IMAGE TO SD CARD###############

			##############SEND DATA AND IMAGE TO BEAGLEBONE###############
			##############SEND DATA AND IMAGE TO BEAGLEBONE###############
			sensor.flush()

		elif command=='Stop':
			success = usb_comms.send_msg('@17s',(b'Sequence Complete',))
			if success==1:
				break
				
		else:
			success = usb_comms.send_msg('@22s',(b'Command Not Recognized',))
			continue