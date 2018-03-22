# Face Detection Example
#
# This example shows off the built-in face detection feature of the OpenMV Cam.
#
# Face detection works by using the Haar Cascade feature detector on an image. A
# Haar Cascade is a series of simple area contrasts checks. For the built-in
# frontalface detector there are 25 stages of checks with each stage having
# hundreds of checks a piece. Haar Cascades run fast because later stages are
# only evaluated if previous stages pass. Additionally, your OpenMV Cam uses
# a data structure called the integral image to quickly execute each area
# contrast check in constant time (the reason for feature detection being
# grayscale only is because of the space requirment for the integral image).

import sensor, time, image

sensor.skip_frames(n = 100)

# Reset sensor
sensor.reset()

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)

sensor.__write_reg(0x00, 113) #overall gain
sensor.__write_reg(0x02, 16) #R gain
sensor.__write_reg(0x03, 31) #G gain
sensor.__write_reg(0x01, 48) #B gain
sensor.__write_reg(0x08, 1) #exposure MSBs
sensor.__write_reg(0x10, 18) #exposure_LSBs

#sensor.set_windowing((320, 240))

sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.RGB565)
sensor.skip_frames(n = 30)

img_RGB = sensor.snapshot()

img_number = "1_RGB_"
plant_id = 10
img_id = str(img_number) + "_plant_" + str(plant_id)
raw_str = "raw_" + str(img_id)
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img_RGB)
raw_write.close()
img_RGB.compress(quality = 100)
img_RGB.save("img_" + str(img_id))
raw_read = image.ImageReader(raw_str)
#img_RGB = raw_read.next_frame(copy_to_fb = False, loop = False)
raw_read.close()

stage_one_good_thresholds = [(25, 100, -127, -3, -15, 3)]

leaf_blobs = []

for blob_index, stage_one_good_blob in enumerate(img_RGB.find_blobs(stage_one_good_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
    rect_stats = img_RGB.get_statistics(roi = stage_one_good_blob.rect())

    img_RGB.draw_rectangle(stage_one_good_blob.rect(), color = (0, 0, 0)) #black

    leaf_blobs.append(stage_one_good_blob)

print(leaf_blobs)




sensor.reset()
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.skip_frames(n = 30)

img_GRAY = sensor.snapshot()

img_number = "1_GRAY_"
plant_id = 10
img_id = str(img_number) + "_plant_" + str(plant_id)
raw_str = "raw_" + str(img_id)
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img_GRAY)
raw_write.close()
img_GRAY.compress(quality = 100)
img_GRAY.save("img_" + str(img_id))
raw_read = image.ImageReader(raw_str)
#img_GRAY = raw_read.next_frame(copy_to_fb = False, loop = False)
raw_read.close()

beetle_cascade = image.HaarCascade("./low_FA_3_stage.cascade", stages=3)

for blob in leaf_blobs:
    objects = img_GRAY.find_features(beetle_cascade, roi=(blob.x() - 10, blob.y() - 10, blob.width() + 20, blob.height() + 20), mthreshold=1.0, scale_factor=1.35)

# Draw objects
for r in objects:
    img_gray.draw_rectangle(r, color = 120)




