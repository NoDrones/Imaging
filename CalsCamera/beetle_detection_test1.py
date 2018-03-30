import sensor, utime, image
'''
def get_overlap_percent(roi1, roi2):
	if len(roi1) != 4:
		raise ValueError("roi1 is not a tuple that contains x, y, width, and height values.")
	if len(roi2) != 4:
		raise ValueError("roi1 is not a tuple that contains x, y, width, and height values.")

	overlapping_pix_count = 0

	for x_1 in range(roi1[0], roi1[0] + roi1[2]):
		for y_1 in range(roi1[1], roi1[1] + roi1[3]):
			if ((x_1 in range(roi2[0], roi2[0] + roi2[2])) & (y_1 in range(roi2[1], roi2[1] + roi2[3]))):
				overlapping_pix_count += 1
				#overlapping_piexls.append((roi1[0] + x_1, roi1[1] + y_1))

	print(overlapping_pix_count)

	total_unique_pix_count = roi1[2] * roi1[3] + roi2[2] * roi2[3] - overlapping_pix_count

	print(total_unique_pix_count)

	percent_overlapping = overlapping_pix_count/total_unique_pix_count

	return percent_overlapping
'''

# Reset sensor
sensor.reset()
sensor.set_auto_gain(False)
sensor.set_auto_exposure(True) #arbitrary af
sensor.set_auto_whitebal(True)


sensor.__write_reg(0x00, 113) #overall gain







########## Take RGB image #########
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.RGB565)
sensor.skip_frames(n = 30)

img_RGB = sensor.snapshot()

img_number = "1_RGB_"
plant_id = 10
img_id = str(img_number) + "plant_" + str(plant_id)
raw_str = "raw_" + str(img_id)
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img_RGB)
raw_write.close()
img_RGB.compress(quality = 100)
img_RGB.save("img_" + str(img_id))
img_RGB = None







########## Take GRAYSCALE image #########

sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(n = 30)

img_GRAY = sensor.snapshot()

img_number = "1_GRAY_"
plant_id = 10
img_id = str(img_number) + "plant_" + str(plant_id)
raw_str = "raw_" + str(img_id)
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img_GRAY)
raw_write.close()
img_GRAY.compress(quality = 80)
img_GRAY.save("img_" + str(img_id))
img_GRAY = None







################ FIND LEAVES #########################

raw_str = "raw_1_RGB_plant_10"
raw_read = image.ImageReader(raw_str)
img_RGB = raw_read.next_frame(copy_to_fb = True, loop = False)
raw_read.close()

stage_one_good_thresholds = [(25, 100, -127, 4, -10, 10)]

leaf_blobs = []

for blob_index, stage_one_good_blob in enumerate(img_RGB.find_blobs(stage_one_good_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
	rect_stats = img_RGB.get_statistics(roi = stage_one_good_blob.rect())

	#img_RGB.draw_rectangle(stage_one_good_blob.rect(), color = (0, 0, 0)) #black

	leaf_blobs.append(stage_one_good_blob)

beetle_thresholds = [(0, 100, 15, 127, -127, -5)]

for blob_index, beetle_blob in enumerate(img_RGB.find_blobs(beetle_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
	rect_stats = img_RGB.get_statistics(roi = beetle_blob.rect(), threshold = beetle_thresholds)
	print(rect_stats)
	if ((rect_stats.a_stdev() >= 2) & (rect_stats.b_stdev() >= 5) & (rect_stats.l_stdev() >= 5)):
		print("here")
		img_RGB.draw_rectangle(beetle_blob.rect(), color = (255, 0, 255))
	#img_RGB.draw_rectangle(beetle_blob.rect(), color = (255, 255, 255))


sensor.flush()
utime.sleep_ms(1000)
img_RGB = None #DESTROY THE IMAGE!



utime.sleep_ms(10000000)





################# FIND BEETLES INSIDE LEAVES #######################

raw_str = "raw_1_GRAY_plant_10"
raw_read = image.ImageReader(raw_str)
img_GRAY = raw_read.next_frame(copy_to_fb = True, loop = False)
raw_read.close()


beetle_cascade = image.HaarCascade("/classifier_iso_min_rotation_low_FA_12_stage.cascade", stages=3)

feature_rois = []
feature_index = 0







for i in range(5):

	#for blob in leaf_blobs:

	#print("Finding features in blob " + str(blob))
	try:
		objects = None
		#objects = img_GRAY.find_features(beetle_cascade, roi=(2*blob.x() - 20, 2*blob.y() - 20, 2*blob.w() + 40, 2*blob.h() + 40), threshold=1, scale_factor=1.2)
		objects = img_GRAY.find_features(beetle_cascade, threshold=.5, scale_factor=1.5)
		print(objects)
		if objects:
			for r in objects:
				feature_rois.append((feature_index, r))
				feature_index += 1
				print("Drawing rects around detected features.")
				img_GRAY.draw_rectangle(r, color = (255, 255, 255))
		else:
			pass

	except Exception as e:
		print(e)

#	for blob in leaf_blobs:
#		img_GRAY.draw_rectangle((2*blob.x() - 20, 2*blob.y() - 20, 2*blob.w() + 40, 2*blob.h() + 40), color = (0, 0, 0)) #black

sensor.flush()
utime.sleep_ms(3000)
img_GRAY = None #DESTROY THE IMAGE!













######################## PROCESS POTENTIAL BEETLES IN COLOR #####################

'''
L = Lightness where 0 is black and 100 is white
A = -127 is green and 128 is red
B = -127 is blue and 128 is yellow.
'''

raw_str = "raw_1_RGB_plant_10"
raw_read = image.ImageReader(raw_str)
img_RGB = raw_read.next_frame(copy_to_fb = True, loop = True)
raw_read.close()

beetle_color_thresholds = [0, 100, 10, 127, 0, 127]

potential_beetles = []

if feature_rois:
	print(feature_rois)
	for feature in feature_rois:
		print("roi: ", round(feature[1][0] / 2), round(feature[1][1]/2), round(feature[1][2]/2), round(feature[1][3]/2))
		try:
			feature_stats = img_RGB.get_statistics(roi = (round(feature[1][0] / 2), round(feature[1][1]/2), round(feature[1][2]/2), round(feature[1][3]/2)))
			print("feature_stats_" + str(feature[0]) + str(feature_stats))

			if feature_stats.a_mean() > 0 & feature_stats.b_mean() < 5:
				potential_beetles.append(feature[1])
		except Exception as e:
			print(e)

if potential_beetles:
	for beetle in potential_beetles: #do this last as to not have colored boxes impact your statistics
		print("potential beetle: " + str(beetle))
		img_RGB.draw_rectangle((int(feature[1][0] / 2), int(feature[1][1]/2), int(feature[1][2]/2), int(feature[1][3]/2)), color = (255, 0, 255))


if feature_rois:
	for feature in feature_rois: #do this last as to not have colored boxes impact your statistics
		print("feature roi: " + str(feature[1]))
		#img_RGB.draw_rectangle((int(feature[1][0] / 2), int(feature[1][1]/2), int(feature[1][2]/2), int(feature[1][3]/2)), color = (0, 255, 255))


sensor.flush()
utime.sleep_ms(500)

sensor.flush()
utime.sleep_ms(3000)





