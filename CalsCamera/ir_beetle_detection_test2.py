import sensor, image, time, utime, pyb, ustruct, os, ir_gain

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
sensor.set_auto_gain(False) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
sensor.set_auto_exposure(False)
while toggle_flash() != 1: pass # turn flash on for calibration

if ir_gain.set_custom_exposure() == -1: warning = "set_custom_exposure error"
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
sensor.__write_reg(0x03, 17)
sensor.__write_reg(0x01, 17)
sensor.__write_reg(0x00, 2)
sensor.__write_reg(0x08, 1)
sensor.__write_reg(0x10, 18)

while toggle_flash() != 1: continue # ensures the flash turns on
utime.sleep_ms(25)
img = sensor.snapshot() # Take a picture and return the image.
utime.sleep_ms(int(flash_time_ms - 25))
while (toggle_flash() != 0): continue # ensures the flash turns off

img_id_str = str(1) + "_plant_" + str(1)
raw_str = "raw_" + img_id_str
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img)
raw_write.close()

healthy_leaves_mean_sum, unhealthy_leaves_mean_sum = 0, 0
healthy_leaves, unhealthy_leaves = 0, 0
healthy_mean, unhealthy_mean = 0, 0
blob_found, leaf_blob_index = False, 0

healthy_leaf_thresholds = (18, 100, -127, -3, 0, 127)
unhealthy_leaf_thresholds = (18, 100, -127, -3, 0, 127)
bad_thresholds = (0, 20, -10, 127, 3, 127)
beetle_thresholds = (0, 100, 15, 127, -127, -5)

beetles = []

##################
# HEALTHY LEAVES
##################

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

healthy_mean = healthy_leaves_mean_sum / (leaf_blob_index + 1)
healthy_leaves = (leaf_blob_index + 1)
blob_found = False

##################
# UNHEALTHY LEAVES
##################

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

unhealthy_mean = unhealthy_leaves_mean_sum / (leaf_blob_index + 1)
unhealthy_leaves = (leaf_blob_index + 1)

overall_ir =  ((healthy_leaves * healthy_mean) + (unhealthy_leaves * unhealthy_mean)) / (healthy_leaves + unhealthy_leaves)





#print("healthy leaf count: " + str(healthy_leaf_count))
#print("unhealthy leaf count: " + str(unhealthy_leaf_count))
#print("average healthy_leaf_a_mean: " + str(healthy_a_mean))
#print("average unhealthy_leaf_a_mean: " + str(unhealthy_a_mean))


for i in beetles:
	print(i)


for i in beetles:
	img.draw_rectangle(i.rect(), color = (0, 255, 255))

'''
for i in unhealthy_leaf_blobs:
	img.draw_rectangle(i.rect(), color = (100, 100, 100))

for i in healthy_leaf_blobs:
	img.draw_rectangle(i.rect(), color = (0, 0, 100))

for i in healthy_leaf_bad_blobs:
	img.draw_rectangle(i.rect(), color = (100, 0, 0))

for i in unhealthy_leaf_bad_blobs:
	img.draw_rectangle(i.rect(), color = (100, 0, 0))
'''

sensor.flush()
time.sleep(1000)
