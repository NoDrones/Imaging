#Author: Calvin Ryan
import sensor, image, time, pyb, math

def set_custom_exposure(high_l_mean_thresh = 14, low_l_mean_thresh = 13):
    try:
        print("Starting Exposure Adjustment...")
        b_gain = sensor.__read_reg(0x01)
        r_gain = sensor.__read_reg(0x02)
        g_gain = sensor.__read_reg(0x03)
        r_gain = round(r_gain/3)
        g_gain = round(g_gain/3)
        b_gain = round(b_gain/3)
        sensor.__write_reg(0x01, b_gain)
        sensor.__write_reg(0x02, r_gain)
        sensor.__write_reg(0x03, g_gain)

        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        l_mean = img_stats.l_mean()
        count = 0
        cur_gain = sensor.__read_reg(0x00)

        while(((l_mean > high_l_mean_thresh) | (l_mean < low_l_mean_thresh))) & (count < 1000):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            l_mean = img_stats.l_mean()

            #print("current gain: " + str(cur_gain))
            #print("l_mean: " + str(l_mean))

            if l_mean > high_l_mean_thresh:
                new_gain = cur_gain - 1
            elif l_mean < low_l_mean_thresh:
                new_gain = cur_gain + 1
            else:
                break #we're in the range now!

            sensor.__write_reg(0x00, new_gain)
            cur_gain = new_gain
            count += 1

        if count < 1000:
            print("Exposure Adjustment Complete.")
            return l_mean
        else:
            print("Exposure Adjustment Incomplete.")
            return -1

    except:
        print("Error occured!")
        return -2


if __name__ == "__main__":

    ########### SETUP STUFF

    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time = 2000)
    clock = time.clock()

    #get in focus balance. You have two seconds.
    t_start = time.ticks()
    t_elapsed = 0
    while(t_elapsed < 1): #ignore bc 1 ms
        img = sensor.snapshot()
        t_elapsed = time.ticks() - t_start


    sensor.set_auto_gain(False) # must be turned off for color tracking
    sensor.set_auto_whitebal(False) # must be turned off for color tracking
    sensor.set_auto_exposure(False)

    set_l_mean = set_custom_exposure() #default thresholds
    sensor.set_contrast(+3)

    img = sensor.snapshot()

    '''
    L = Lightness where 0 is black and 100 is white
    A = -127 is green and 128 is red`
    B = -127 is blue and 128 is yellow.
    '''

    img_stats = img.get_statistics()





    ########### FIND BAD BLOBS

    stage_one_bad_thresholds = [(30, 100, 0, 127, 10, 128)]

    unhealthy_full_l_mean = 0
    unhealthy_full_a_mean = 0
    unhealthy_full_b_mean = 0
    unhealthy_centroid_l_mean = 0
    unhealthy_centroid_a_mean = 0
    unhealthy_centroid_b_mean = 0
    healthy_full_l_mean = 0
    healthy_full_a_mean = 0
    healthy_full_b_mean = 0
    healthy_centroid_l_mean = 0
    healthy_centroid_a_mean = 0
    healthy_centroid_b_mean = 0

    blob_index = -1

    for blob_index, stage_one_bad_blob in enumerate(img.find_blobs(stage_one_bad_thresholds, pixels_threshold=200, area_threshold=200, merge = False, margin = 15)):
        blob_hist = img.get_histogram(roi = (stage_one_bad_blob[0], stage_one_bad_blob[1], stage_one_bad_blob[2], stage_one_bad_blob[3]))
        blob_stats = blob_hist.get_statistics()

        print("stage_one_bad_blob: " + str(stage_one_bad_blob))
        print("density: " + str(stage_one_bad_blob.density()))
        print("full: " + str(blob_stats))
        unhealthy_full_l_mean += blob_stats[0]
        unhealthy_full_a_mean += blob_stats[8]
        unhealthy_full_b_mean += blob_stats[16]

        side_l = stage_one_bad_blob.density() * min(stage_one_bad_blob[2], stage_one_bad_blob[3])

        partial_hist = img.get_histogram(roi = (stage_one_bad_blob.cx() - round(side_l/2), stage_one_bad_blob.cy() - round(side_l/2), round(side_l), round(side_l)))
        partial_stats = partial_hist.get_statistics()
        print("partial: "+ str(partial_stats))
        print("\n")
        unhealthy_centroid_l_mean += partial_stats[0]
        unhealthy_centroid_a_mean += partial_stats[8]
        unhealthy_centroid_b_mean += partial_stats[16]

        img.draw_rectangle(stage_one_bad_blob.rect(), color = (255, 0, 255)) #purple
        img.draw_rectangle((stage_one_bad_blob.cx() - round(side_l/2), stage_one_bad_blob.cy() - round(side_l/2), round(side_l), round(side_l)), color = (255, 85, 0))

    if blob_index != -1:
        unhealthy_full_l_mean = unhealthy_full_l_mean/(blob_index + 1)
        unhealthy_full_a_mean = unhealthy_full_a_mean/(blob_index + 1)
        unhealthy_full_b_mean = unhealthy_full_b_mean/(blob_index + 1)
        unhealthy_centroid_l_mean = unhealthy_centroid_l_mean/(blob_index + 1)
        unhealthy_centroid_a_mean = unhealthy_centroid_a_mean/(blob_index + 1)
        unhealthy_centroid_b_mean = unhealthy_centroid_b_mean/(blob_index + 1)


    print("------------------------------------------------------------------------")



    ########### FIND GOOD BLOBS

    #stage_one_good_thresholds = [(img_stats.l_mean() - 1, 100, -127, img_stats.a_mean() - 4, img_stats.b_mean() - 8, 60)]
    stage_one_good_thresholds = [(30, 100, -127, 0, -10, 10)]

    for blob_index, stage_one_good_blob in enumerate(img.find_blobs(stage_one_good_thresholds, pixels_threshold=200, area_threshold=200, merge = False, margin = 15)):
        blob_hist = img.get_histogram(roi = (stage_one_good_blob[0], stage_one_good_blob[1], stage_one_good_blob[2], stage_one_good_blob[3]))
        blob_stats = blob_hist.get_statistics()


        print("stage_one_good_blob: " + str(stage_one_good_blob))
        print("density: " + str(stage_one_good_blob.density()))
        print("full: "+ str(blob_stats))
        healthy_full_l_mean += blob_stats[0]
        healthy_full_a_mean += blob_stats[8]
        healthy_full_b_mean += blob_stats[16]

        side_l = stage_one_good_blob.density() * min(stage_one_good_blob[2], stage_one_good_blob[3])

        partial_hist = img.get_histogram(roi = (stage_one_good_blob.cx() - round(side_l/2), stage_one_good_blob.cy() - round(side_l/2), round(side_l), round(side_l)))
        partial_stats = partial_hist.get_statistics()
        print("partial: "+ str(partial_stats))
        print("\n")
        healthy_centroid_l_mean += partial_stats[0]
        healthy_centroid_a_mean += partial_stats[8]
        healthy_centroid_b_mean += partial_stats[16]

        img.draw_rectangle(stage_one_good_blob.rect(), color = (255, 255, 0)) #yellow
        img.draw_rectangle((stage_one_good_blob.cx() - round(side_l/2), stage_one_good_blob.cy() - round(side_l/2), round(side_l), round(side_l)), color = (255, 85, 0))

        ########## COLOR IT ALL IN

        for x in range(stage_one_good_blob[2]):
            for y in range(stage_one_good_blob[3]):
                pix_location = (stage_one_good_blob[0] + x, stage_one_good_blob[1] + y)
                pix_vals = img.get_pixel(pix_location[0], pix_location[1])
                lab_pix_vals = image.rgb_to_lab(pix_vals)

                if ((lab_pix_vals[1] < (blob_stats.a_mean() + 2 * blob_stats.a_stdev())) & (lab_pix_vals[0] >= (blob_stats.l_mean() - .1 * blob_stats.l_stdev()))): #& (abs(lab_pix_vals[2] - lab_pix_vals[1]) > 10) & (lab_pix_vals[0] > (blob_stats.l_mean() - 10)):
                    pass
                else:
                    pass
                    #img.set_pixel(pix_location[0], pix_location[1], (255, 0, 0))

    if blob_index != -1:
        healthy_full_l_mean = healthy_full_l_mean/(blob_index + 1)
        healthy_full_a_mean = healthy_full_a_mean/(blob_index + 1)
        healthy_full_b_mean = healthy_full_b_mean/(blob_index + 1)
        healthy_centroid_l_mean = healthy_centroid_l_mean/(blob_index + 1)
        healthy_centroid_a_mean = healthy_centroid_a_mean/(blob_index + 1)
        healthy_centroid_b_mean = healthy_centroid_b_mean/(blob_index + 1)



    print(img.compress_for_ide(quality = 50))

    print("~~~~~~~~~~~~~~~ RESULTS: ~~~~~~~~~~~~~~~~")
    print("unhealthy full l mean: " + str(unhealthy_full_l_mean))
    print("unhealthy full a mean: " + str(unhealthy_full_a_mean))
    print("unhealthy full b mean: " + str(unhealthy_full_b_mean))
    print("unhealthy centroid l mean: " + str(unhealthy_centroid_l_mean))
    print("unhealthy centroid a mean: " + str(unhealthy_centroid_a_mean))
    print("unhealthy centroid b mean: " + str(unhealthy_centroid_b_mean))
    print("healthy full l mean: " + str(healthy_full_l_mean))
    print("healthy full a mean: " + str(healthy_full_a_mean))
    print("healthy full b mean: " + str(healthy_full_b_mean))
    print("healthy centroid l mean: " + str(healthy_centroid_l_mean))
    print("healthy centroid a mean: " + str(healthy_centroid_a_mean))
    print("healthy centroid b mean: " + str(healthy_centroid_b_mean))



