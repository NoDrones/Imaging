import sensor, image, time, pyb

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False, gain_db = 32) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
sensor.set_auto_exposure(False, exposure_us = 420)
clock = time.clock()


l_red = pyb.LED(1)
l_green = pyb.LED(2)
l_blue = pyb.LED(3)
l_IR = pyb.LED(4)

l_red.on() #red heartbeat
time.sleep(200)
l_red.off() #red heartbeat

l_green.on() #green heartbeat
time.sleep(200)
l_green.off() #green heartbeat

img = sensor.snapshot()         # Take a picture and return the image.

'''
L = Lightness where 0 is black and 100 is white
A = -127 is green and 128 is red
B = -127 is blue and 128 is yellow.
'''

#Discriminate against median to determine lighting conditions
#3 bins:
#median < 20 = dimly lit (18 maybe?)
#20 =< median =< 40 = well lit
#median > 40 = over lit

#thresholds LAB -> [Llo, Lhi, Alo, Ahi, Blo, Bhi]
#stage_one_thresholds = [(0, 100, -127, -10, 0, 60)]

img_hist = img.get_histogram()
img_stats = img_hist.get_statistics()

healthy_leaf_thresholds = [(180, 255)]
unhealthy_leaf_thresholds = [(70, 120)]
bad_thresholds = [( 0, 40)]

healthy_leaves_mean_sum = 0
unhealthy_leaves_mean_sum = 0

blob_found = False

for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(healthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
    blob_found = True
    print("leaf blob found: ")
    print(leaf_blob.rect())
    img.draw_rectangle(leaf_blob.rect(), color = 255)
    leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
    # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
    leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3]
    leaf_area = leaf_blob[2] * leaf_blob[3]

    for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
        print("bad blob found: ")
        print(bad_blob.rect())
        img.draw_rectangle(bad_blob.rect(), color = 127)
        bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
        # more undoing of mean function
        bad_rect_pix_sum = bad_rect_stats.mean() * bad_blob[2] * bad_blob[3]
        # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
        leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum
        # tracking the remaining area of the leaf as the bad_rects are removed
        leaf_area = leaf_area - (bad_blob[2] * bad_blob[3])

    leaf_rect_mean = leaf_rect_stats.mean()
    leaf_mean = leaf_rect_pix_sum / leaf_area
    print("healthy leaf mean = %i [outer mean = %i]" % (leaf_mean, leaf_rect_mean))
    # the below function does not take into account the size of a leaf... each leaf is weighted equally
    healthy_leaves_mean_sum = healthy_leaves_mean_sum + leaf_mean

# calculates the average value for the healthy leaves regardless of leaf size
if (blob_found == True):
    healthy_mean = healthy_leaves_mean_sum / (leaf_blob_index + 1)

blob_found = False

for leaf_blob_index, leaf_blob in enumerate(img.find_blobs(unhealthy_leaf_thresholds, pixels_threshold=200, area_threshold=200, merge = False)):
    blob_found = True
    print("leaf blob found: ")
    print(leaf_blob.rect())
    img.draw_rectangle(leaf_blob.rect(), color = 255)
    leaf_rect_stats = img.get_statistics(roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))
    # want to undo the mean function so we can adjust the leaf mean to remove the effect of bad blobs
    leaf_rect_pix_sum = leaf_rect_stats.mean() * leaf_blob[2] * leaf_blob[3]
    leaf_area = leaf_blob[2] * leaf_blob[3]
    for bad_blob_index, bad_blob in enumerate(img.find_blobs(bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, roi = (leaf_blob[0], leaf_blob[1], leaf_blob[2], leaf_blob[3]))):
        print("bad blob found: ")
        print(bad_blob.rect())
        img.draw_rectangle(bad_blob.rect(), color = 127)
        bad_rect_stats = img.get_statistics(roi = (bad_blob[0], bad_blob[1], bad_blob[2], bad_blob[3]))
        # more undoing of mean function
        bad_rect_pix_sum = bad_rect_stats.mean()*bad_blob[2]*bad_blob[3]
        # tracking the sum of pixels that are in the leaf_rect, but are not in any bad_rects
        leaf_rect_pix_sum = leaf_rect_pix_sum - bad_rect_pix_sum
        # tracking the remaining area of the leaf as the bad_rects are removed
        leaf_area = leaf_area - (bad_blob[2] * bad_blob[3])

    leaf_rect_mean = leaf_rect_stats.mean()
    leaf_mean = leaf_rect_pix_sum / leaf_area
    print("unhealthy leaf mean = %i [outer mean = %i]" % (leaf_mean, leaf_rect_mean))
    # the below function does not take into account the size of a leaf... each leaf is weighted equally
    unhealthy_leaves_mean_sum = unhealthy_leaves_mean_sum + leaf_mean

# calculates the average value for the healthy leaves regardless of leaf size
if (blob_found == True):
    unhealthy_mean = unhealthy_leaves_mean_sum / (leaf_blob_index + 1)

print("healthy mean = %i; unhealthy mean = %i" % (healthy_mean, unhealthy_mean))
if (unhealthy_mean < 135):
    print("You got some seriously unhealthy leafage there, figure it out")
elif (unhealthy_mean < 145):
    print("Some leaves are unhappy, although they're soldiering on")
else:
    print("Even your unhealthy leaves are healthy!")


print(img.compressed_for_ide(quality = 25))

sensor.flush()
time.sleep(3000)
