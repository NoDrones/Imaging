import sensor, image, time, utime, pyb, ustruct, os, color_gain, i2c_master, usb_comms

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

def send_plant_id(plant = 0):
	format_str = "<i"
	success = i2c_master.send_next_msg_format(next_msg_type_str = "plant_id", next_msg_format_str = format_str)
	if success == False:
		return -1

	packed_data = ustruct.pack(format_str, plant)
	return i2c_master.send_packed_msg(packed_msg = packed_data)

# \/ Setup Camera \/
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
clock = time.clock()

flash_time_ms = 250 # Set flash_time to be greater than exposure time
warning = "none"
calibrated = False
metadata_str = ""


#CALIBRATE#

# Analog gain introduces less noise than digital gain so we maximize it
sensor.__write_reg(0x4D, 0b11111111)
'''
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_auto_exposure(False)

while toggle_flash() != 1: pass # turn flash on for calibration

if color_gain.set_custom_exposure(high_l_mean_thresh = 22, low_l_mean_thresh = 21) != -1: calibrated = True # Now set the exposure
else: pass #print("Could not complete calibration")

while toggle_flash() != 0: pass # turn flash off after calibration

post_adjust_r_gain = sensor.__read_reg(0x02)
post_adjust_g_gain = sensor.__read_reg(0x03)
post_adjust_b_gain = sensor.__read_reg(0x01)
post_adjust_overall_gain = sensor.__read_reg(0x00)
post_adjust_exposure = (sensor.__read_reg(0x08) << 8) + sensor.__read_reg(0x10)

print("R gain: " + str(post_adjust_r_gain))
print("G gain: " + str(post_adjust_g_gain))
print("B gain: " + str(post_adjust_b_gain))
print("Overall gain: " + str(post_adjust_overall_gain))
print("exposure: " + str(post_adjust_exposure))
print()

'''



sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_auto_exposure(False)
sensor.__write_reg(0x02, 16)
sensor.__write_reg(0x03, 22)
sensor.__write_reg(0x01, 64)
sensor.__write_reg(0x00, 6)
sensor.__write_reg(0x08, 1)
sensor.__write_reg(0x10, 18)

calibrated = True

# TODO: Write color calibration data to sd card


############################################
### PHOTO & DATA COLLECTION TRIGGER
############################################

# collect plant_id and image number from Beaglebone

if calibrated != True: warning = "not calibrated"

while toggle_flash() != 1: pass # turn flash on
shutter_start = time.ticks()
utime.sleep_ms(25)
img = sensor.snapshot() # take a picture
while time.ticks() < (shutter_start + flash_time_ms): pass
while toggle_flash() != 0: pass # turn flash off


img_id_str = str(1) + "_plant_" + str(1)
raw_str = "raw_" + img_id_str

raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img)
raw_write.close()

img.compress(quality = 100)

# reload raw
raw_read = image.ImageReader(raw_str)
img = raw_read.next_frame(copy_to_fb = True, loop = False)
raw_read.close()

# save metadata file
img_metadata_path = "metadata_" + str(1) + "_plant_" + str(1) + ".txt" # prepare to create metadata file for picture
img_metadata_fd = open(img_metadata_path, "w+")
if img_metadata_fd.write(metadata_str) < 1: warning = "insufficient metadata bytes written" # Write metadata to text file
img_metadata_fd.close() # Close file

# receive ir_data before continuing

# now perform measurements on your own image
img_hist = img.get_histogram()
img_stats = img_hist.get_statistics()

healthy_leaves_a_mean_sum = 0
healthy_leaf_a_mean = 0
unhealthy_leaf_a_mean = 0
unhealthy_leaves_a_mean_sum = 0
healthy_blob_found = False
unhealthy_blob_found = False

beetles = []
healthy_leaf_blobs = []
healthy_leaf_bad_blobs = []
unhealthy_leaf_blobs = []
unhealthy_leaf_bad_blobs = []


# green is -a, yellow is +b, blue is -b, red is +a
healthy_leaf_thresholds = [(26, 100, -40, -10, 20, 40), (20, 26, -40, -10, 20, 40), (14, 20, -40, -10, 10, 40), (8, 14, -40, -2, 2, 40)]
bad_thresholds = [(0, 5, -2, 40, -10, 3), (5, 10, -2, 30, -10, 3), (10, 15, -2, 30, -10, 2)]
unhealthy_leaf_thresholds = [(19, 100, -3, 40, 0, 40)]
beetle_thresholds = [(19, 100, -3, 40, 0, 40)]

#######################
# UNHEALTHY LEAVES
#######################

for unhealthy_leaf_blob_index, leaf_blob in enumerate(img.find_blobs(unhealthy_leaf_thresholds, pixels_threshold=100, area_threshold=100, merge = False)):
	unhealthy_blob_found = True
	leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
	unhealthy_leaf_rect_pix_a_sum = leaf_rect_stats.a_mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
	unhealthy_leaf_area = leaf_blob[2] * leaf_blob[3]
	unhealthy_leaf_blobs.append(leaf_blob)

	if (abs(leaf_rect_stats.a_mean() - leaf_rect_stats.b_mean()) <= 10):
		continue #this blob is probably black, white, or a shade of grey

	for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=25, area_threshold=25, merge = False, roi = leaf_blob.rect())):
		bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))

		bad_rect_pix_a_sum = bad_rect_stats.a_mean() * bad_blob[2] * bad_blob[3] # more undoing of mean function
		unhealthy_leaf_rect_pix_a_sum = unhealthy_leaf_rect_pix_a_sum - bad_rect_pix_a_sum # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
		unhealthy_leaf_area = unhealthy_leaf_area - (bad_blob[2] * bad_blob[3]) # tracking the remaining area of the leaf as the bad_rects are removed
		unhealthy_leaf_bad_blobs.append(bad_blob)

	unhealthy_leaf_rect_a_mean = leaf_rect_stats.a_mean() #for comparison!
	unhealthy_leaf_a_mean = unhealthy_leaf_rect_pix_a_sum / unhealthy_leaf_area #this is the valid measurement
	unhealthy_leaves_a_mean_sum = unhealthy_leaves_a_mean_sum + unhealthy_leaf_a_mean

	#FIND BEETLES: WORK IN PROGR
	try:
		for beetle_blob_index, beetle_blob in enumerate(img.find_blobs(beetle_thresholds, roi = (leaf_blob[0] - 10, leaf_blob[1] - 10, leaf_blob[2] + 20, leaf_blob[3] + 20), pixels_threshold=100, area_threshold=100, merge = True, margin = 10)):
			beetle_blob_stats = img.get_statistics(roi = beetle_blob.rect(), threshold = beetle_thresholds)
			if ((beetle_blob_stats.a_stdev() >= 3) & (beetle_blob_stats.b_stdev() >= 3) & (beetle_blob_stats.l_max() - beetle_blob_stats.l_min() >= 33)): #bugs tend to have greater std deviations because they have a unique color against leaves and then also contain stripes.
				beetles.append(beetle_blob)
	except Exception as e: #search with tighter bounds
		try:
			for beetle_blob_index, beetle_blob in enumerate(img.find_blobs(beetle_thresholds, roi = leaf_blob.rect(), pixels_threshold=100, area_threshold=100, merge = True, margin = 10)):
				beetle_blob_stats = img.get_statistics(roi = beetle_blob.rect(), threshold = beetle_thresholds)
				if ((beetle_blob_stats.a_stdev() >= 3) & (beetle_blob_stats.b_stdev() >= 3) & (beetle_blob_stats.l_max() - beetle_blob_stats.l_min() >= 33)): #bugs tend to have greater std deviations because they have a unique color against leaves and then also contain stripes.
					beetles.append(beetle_blob)
		except Exception as e:
			pass
			#okay fine, the error is something else.

#######################
# HEALTHY LEAVES
#######################

for healthy_leaf_blob_index, leaf_blob in enumerate(img.find_blobs(healthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
	healthy_blob_found = True
	leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
	healthy_leaf_rect_pix_a_sum = leaf_rect_stats.a_mean() * leaf_blob[2] * leaf_blob[3] # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
	healthy_leaf_area = leaf_blob[2] * leaf_blob[3]
	healthy_leaf_blobs.append(leaf_blob)

	if (abs(leaf_rect_stats.a_mean() - leaf_rect_stats.b_mean()) <= 10):
		continue #this blob is probably black, white, or a shade of grey

	for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=25, area_threshold=25, merge = False, roi = leaf_blob.rect())):
		bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))

		bad_rect_pix_a_sum = bad_rect_stats.a_mean() * bad_blob[2] * bad_blob[3] # more undoing of mean function
		healthy_leaf_rect_pix_a_sum = healthy_leaf_rect_pix_a_sum - bad_rect_pix_a_sum # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
		healthy_leaf_area = healthy_leaf_area - (bad_blob[2] * bad_blob[3]) # tracking the remaining area of the leaf as the bad_rects are removed
		healthy_leaf_bad_blobs.append(bad_blob)

	healthy_leaf_rect_a_mean = leaf_rect_stats.a_mean() #for comparison!
	healthy_leaf_a_mean = healthy_leaf_rect_pix_a_sum / healthy_leaf_area #this is the valid measurement
	healthy_leaves_a_mean_sum = healthy_leaves_a_mean_sum + healthy_leaf_a_mean

	#print("healthy_leaf_a_mean: " + str(healthy_leaf_a_mean))
	#print("healthy_leaf_area: " + str(healthy_leaf_area))



# calculates the average value for the healthy leaves regardless of leaf size
if healthy_blob_found:
	healthy_leaf_count = healthy_leaf_blob_index + 1
	healthy_a_mean = healthy_leaves_a_mean_sum / (healthy_leaf_count)
else:
	healthy_leaf_count = 0
	healthy_a_mean = "N/A"


if unhealthy_blob_found:
	unhealthy_leaf_count = unhealthy_leaf_blob_index + 1
	unhealthy_a_mean = unhealthy_leaves_a_mean_sum / unhealthy_leaf_count
else:
	unhealthy_leaf_count = 0
	unhealthy_a_mean = "N/A"


print("healthy leaf count: " + str(healthy_leaf_count))

print("unhealthy leaf count: " + str(unhealthy_leaf_count))
print("average healthy_leaf_a_mean: " + str(healthy_a_mean))
print("average unhealthy_leaf_a_mean: " + str(unhealthy_a_mean))
print("beetles: " + str(len(beetles)))

for i in beetles:
	print(i)


for i in beetles:
	img.draw_rectangle(i.rect(), color = (0, 255, 255))

for i in healthy_leaf_blobs:
	img.draw_rectangle(i.rect(), color = (0, 0, 100))

for i in unhealthy_leaf_blobs:
	img.draw_rectangle(i.rect(), color = (100, 100, 100))

for i in healthy_leaf_bad_blobs:
	img.draw_rectangle(i.rect(), color = (100, 0, 0))
'''
for i in unhealthy_leaf_bad_blobs:
	img.draw_rectangle(i.rect(), color = (100, 0, 0))
'''
time.sleep(1000)
sensor.flush()
time.sleep(1000)
