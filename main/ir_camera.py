import sensor, image, time, utime, pyb, ustruct, os, ir_gain, i2c_slave

def send_data(leaf_count = (0, 0), leaf_health = (0, 0), plant_ndvi = 0, plant_ir = 0, warning_str = "none"):

	format_str = "<2i4f50s"
	success = i2c_slave.send_next_msg_format(next_msg_type_str = "data")
	if success == False:
		return -1

	warning_bytes = warning_str.encode('ascii')
	packed_data = ustruct.pack(format_str, leaf_count[0], leaf_count[1], leaf_health[0], leaf_health[1], plant_ndvi, plant_ir, warning_bytes)

	return i2c_slave.send_packed_msg(packed_msg = packed_data)

#################
# In general you shouldn't specify next_msg_format_str - as long as we always call send_msg_format()
# at the begining of each communication it is unneccesary. Only specify this variable if you plan on
# sending a custom message after without calling send_msg_format() first.

def send_calibration(warning_str = "none"):

	format_str = "<4fi50s"
	success = i2c_slave.send_next_msg_format(next_msg_type_str = "calibration", next_msg_format_str = format_str)
	if success == False: return -1

	warning_bytes = warning_str.encode('ascii')
	(overall_gain, r_gain, g_gain, b_gain, exposure_value) = ir_gain.get_gain()
	packed_calibration = ustruct.pack(format_str + "s", overall_gain, r_gain, g_gain, b_gain, exposure_value, warning_bytes)

	return i2c_slave.send_packed_msg(packed_msg = packed_calibration)

#################
# This function only utilizes the first half of our normal message protocol, send_next_msg_format() is just a flag
# to prepare the reciever for whatever comes next, for a trigger this flag is all we need.
def send_trigger():
	# Don't need to specify a next_msg_format_str because this message is treated differently
	success = i2c_slave.send_next_msg_format(next_msg_type_str = "trigger")
	if success == False: return -1
	return 1

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

	sensor.reset()
	sensor.set_pixformat(sensor.GRAYSCALE)
	sensor.set_framesize(sensor.QVGA)
	sensor.skip_frames(time = 2000)
	clock = time.clock()

	# Analog gain introduces less noise than digital gain, we should use this before anything else
	print("Initial analog gain register = " + bin(sensor.__read_reg(0x4D)))
	print("Maxing out analog gain register and setting AWB/AGC...")
	sensor.__write_reg(0x4D, 0b11111111)
	print("Analog gain register pre AWB/AGC setting = " + bin(sensor.__read_reg(0x4D)))

	sensor.set_auto_gain(False) # must be turned off for color tracking
	sensor.set_auto_whitebal(False) # must be turned off for color tracking
	sensor.set_auto_exposure(False)

	print("Analog gain register post AWB/AGC setting = " + bin(sensor.__read_reg(0x4D))) # Analog gain introduces less noise than digital gain, we should use this before anything else

	while toggle_flash() != 1: pass # turn flash on for calibration
	ir_gain.set_custom_exposure() # Now set the exposure
	while toggle_flash() != 0: pass # turn flash off after calibration

	# \/ Receive Calibration \/
	# Calling receive_message will also trigger action if directed by sender, such as performing calibration, or passing on/storing data, or taking a photo/flashing the light source
	# The returned msg_type can be used to verify the expected action took place if desired, and react if necessary (such as repeat a process)

	# IR camera waits for calibration directions from the color camera
	msg_type = i2c_slave.receive_msg()
	if msg_type == -1: print("Could not receive message.")
	elif "calibration" not in msg_type: print("Unexpected msg_type: " + str(msg_type))

	flash_time_ms = 250 # Set flash_time to be greater than exposure time

	if send_trigger() == -1: print("Trigger unsuccessful") 	# Trigger light source/color camera

	while toggle_flash() != 1: continue # ensures the flash turns on

	utime.sleep_ms(25)
	img = sensor.snapshot()         # Take a picture and return the image.
	utime.sleep_ms(int(flash_time_ms - 25))

	# ensures the flash turns off
	while (toggle_flash() != 0): continue

	## \/ Name & Save Image \/
	# Save raw image, save compressed image, load back in raw image for processing.
	# should pull img_number from a text file and read the plant_id from a qr code or beaglebone || default mode is pyb.usb_mode('VCP+MSC')
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

	img_number, plant_id = 4, 1
	img_id = str(img_number) + "plant_" + str(plant_id)
	raw_str = "raw_" + str(img_id)
	raw_write = image.ImageWriter(raw_str)
	raw_write.add_frame(img)
	raw_write.close()

	img.compress(quality = 100)
	img.save("img_" + str(img_id))

	raw_read = image.ImageReader(raw_str)
	img = raw_read.next_frame(copy_to_fb = True, loop = False)
	raw_read.close()

	img_hist = img.get_histogram()
	img_stats = img_hist.get_statistics()

	healthy_leaf_thresholds, unhealthy_leaf_thresholds, bad_thresholds = [(170, 255)], [(80, 120)], [( 0, 50)]
	healthy_leaves_mean_sum, unhealthy_leaves_mean_sum = 0, 0
	healthy_mean, unhealthy_mean = 0, 0
	blob_found, leaf_blob_index = False, 0

	for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(healthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
		blob_found = True
		print("leaf blob found: " + str(leaf_blob.rect()))
		img.draw_rectangle(leaf_blob.rect(), color = 255)
		leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
		leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
		leaf_area = leaf_blob[2] * leaf_blob[3]

		for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=50, area_threshold=50, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
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

	for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(unhealthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
		blob_found = True
		print("leaf blob found: " + str(leaf_blob.rect()))
		img.draw_rectangle(leaf_blob.rect(), color = 255)
		leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
		leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
		leaf_area = leaf_blob[2] * leaf_blob[3]
		for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
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

	send_data(leaf_count = (healthy_leaves, unhealthy_leaves), leaf_health = (healthy_mean, unhealthy_mean), plant_ndvi = 0, plant_ir = overall_ir, warning_str = "none")

	print("healthy mean = %i; unhealthy mean = %i" % (healthy_mean, unhealthy_mean))
	if (unhealthy_mean < 135): print("You got some seriously unhealthy leafage there, figure it out")
	elif (unhealthy_mean < 145): print("Some leaves are unhappy, although they're soldiering on")
	else: print("Even your unhealthy leaves are healthy!")

	sensor.flush()
	utime.sleep_ms(3000)
