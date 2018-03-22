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

import sensor, utime, image

sensor.skip_frames(n = 100)

# Reset sensor
sensor.reset()

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(True)


sensor.__write_reg(0x00, 113) #overall gain
'''
sensor.__write_reg(0x02, 16) #R gain
sensor.__write_reg(0x03, 31) #G gain
sensor.__write_reg(0x01, 48) #B gain
'''
sensor.__write_reg(0x08, 1) #exposure MSBs
sensor.__write_reg(0x10, 18) #exposure_LSBs


#sensor.set_windowing((320, 240))

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
print(raw_str)
raw_read = image.ImageReader(raw_str)
img_RGB = raw_read.next_frame(copy_to_fb = True, loop = False)
raw_read.close()

stage_one_good_thresholds = [(25, 100, -127, 2, -15, 15)]

leaf_blobs = []

for blob_index, stage_one_good_blob in enumerate(img_RGB.find_blobs(stage_one_good_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
    rect_stats = img_RGB.get_statistics(roi = stage_one_good_blob.rect())

    img_RGB.draw_rectangle(stage_one_good_blob.rect(), color = (0, 0, 0)) #black

    leaf_blobs.append(stage_one_good_blob)

print(leaf_blobs)

sensor.flush()
utime.sleep_ms(1000)
img_RGB = None #DESTROY THE IMAGE!






sensor.reset()
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.skip_frames(n = 30)

img_GRAY = sensor.snapshot()

img_number = "1_GRAY_"
plant_id = 10
img_id = str(img_number) + "plant_" + str(plant_id)
raw_str = "raw_" + str(img_id)
raw_write = image.ImageWriter(raw_str)
raw_write.add_frame(img_GRAY)
raw_write.close()
img_GRAY.compress(quality = 100)
img_GRAY.save("img_" + str(img_id))
raw_read = image.ImageReader(raw_str)
img_GRAY = raw_read.next_frame(copy_to_fb = True, loop = False)
raw_read.close()


beetle_cascade = image.HaarCascade("./low_FA_3_stage.cascade", stages=3)

feature_rois = []

for blob in leaf_blobs:

    img_GRAY.draw_rectangle(blob.rect(), color = 0) #black

    try:
        print("Finding features in blob " + str(blob))
        objects = img_GRAY.find_features(beetle_cascade, roi=(blob.x() - 10, blob.y() - 10, blob.w() + 20, blob.h() + 20), threshold=1.0, scale_factor=1.35)

        if objects:
            for r in objects:
                feature_rois.append(r)
                print("Drawing rects around detected features.")
                img_GRAY.draw_rectangle(r, color = 255)
        else:
            pass

    except Exception as e:
        print(e)

sensor.flush()
utime.sleep_ms(3000)
img_GRAY = None #DESTROY THE IMAGE!


'''
L = Lightness where 0 is black and 100 is white
A = -127 is green and 128 is red
B = -127 is blue and 128 is yellow.
'''



raw_str = "raw_1_RGB_plant_10"
raw_read = image.ImageReader(raw_str)
img_RGB = raw_read.next_frame(copy_to_fb = True, loop = True)
raw_read.close()

beetle_color_thresholds = [0, 100, 0, 127, 0, 127]

for i, feature in enumerate(feature_rois):
    feature_stats = img_RGB.get_statistics(roi = feature)
    print("feature_stats_" + "i" + str(feature_stats))
for i, feature in enumerate(feature_rois): #do this last as to not have colored boxes impact your statistics
    print("feature roi: " + "i" + str(feature))
    img_RGB.draw_rectangle(feature, color = (0, 255, 255))


sensor.flush()
utime.sleep_ms(3000)
img_RGB = None





