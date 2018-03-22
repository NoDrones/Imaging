#Author: Calvin Ryan
import sensor, image, time, pyb, ustruct, math, utime


def get_gain():
    gain_reg_val = sensor.__read_reg(0x00)
    #print("gain_reg_val: " + str(gain_reg_val))
    bitwise_gain_range = (gain_reg_val & 0b11110000) >> 4 #get the highest four bits which correspond to gain range. Depends on the bits set. Can be 0 > 4 for a total of 5 ranges.
    #print("bitwise_gain_range: " + str(bin(bitwise_gain_range)))
    gain_range = ((bitwise_gain_range & 0b1000) >> 3) + ((bitwise_gain_range & 0b0100) >> 2) + ((bitwise_gain_range & 0b0010) >> 1) + (bitwise_gain_range & 0b0001) #get an int for the number of bits set
    #print("read_gain_range: " + str(gain_range))
    gain_LSBs = gain_reg_val & 0b00001111 #The 4 lsbs represent the fine tuning gain control.
    #print("gain_LSBs: " + str(gain_LSBs))
    gain_curve_index = 16 * gain_range + gain_LSBs # this gives you an index from 0 > 79 which is the range of points you need to describe every possible gain setting along the new gain curve
    #print("gain_curve_index: " + str(gain_curve_index))
    gain = 10 ** (30 * gain_curve_index / 79 / 20) #10** = 10 ^, calculate the gain along the new exponential gain curve I defined earlier on
    #print("gain: " + str(gain))
    return gain

def set_gain(gain_db):
    # gain_correlation_equation = 20*log(gain_db) = 30*(index)/79
    gain_curve_index = (79 * 20 * math.log(gain_db, 10)) / 30 #return an index from the new exponential gain curve...
    #... Can be 0 > 79 which is the # of points needed to describe every gain setting along the new curve
    #print("gain_curve_index: " + str(gain_curve_index))
    gain_range = int(gain_curve_index/16) #find a 0 > 4 value for the gain range. This range is defined by the 4 msbs. Thus we divide and round down by the LSB of the 4 MSBs (16)
    #print("gain_range: " + str(gain_range))
    gain_LSBs = int(gain_curve_index - 16 * gain_range) & 0b00001111 #Find how many LSBs above the gain range the index is. This is your fine tuning gain control
    #print("gain_LSBs: " + str(bin(gain_LSBs)))
    bitwise_gain_range = (0b1111 << gain_range) & 0b11110000 #make the gain range bitwise
    #print("bitwise_gain_range: " + str(bin(bitwise_gain_range)))
    gain_reg_val = bitwise_gain_range | gain_LSBs #OR
    #print("gain to set: " + str(bin(gain_reg_val)))
    sensor.__write_reg(0x00, gain_reg_val)
    return gain_reg_val

def set_custom_exposure(high_l_mean_thresh = 17, low_l_mean_thresh = 16):
    try:
        print("Starting Exposure Adjustment...")
        b_gain = sensor.__read_reg(0x01)
        r_gain = sensor.__read_reg(0x02)
        g_gain = sensor.__read_reg(0x03)
        r_gain = round(r_gain/4)
        g_gain = round(g_gain/4)
        b_gain = round(b_gain/4)
        sensor.__write_reg(0x01, b_gain)
        sensor.__write_reg(0x02, r_gain)
        sensor.__write_reg(0x03, g_gain)

        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        l_mean = img_stats.l_mean()
        count = 0

        cur_gain = get_gain()

        while(((l_mean > high_l_mean_thresh) | (l_mean < low_l_mean_thresh))) & (count < 256) & (cur_gain >= 0):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            l_mean = img_stats.l_mean()

            if ((cur_gain < 1) | (cur_gain > 32)):
                break

            if l_mean > high_l_mean_thresh:
                new_gain = cur_gain - .1
            elif l_mean < low_l_mean_thresh:
                new_gain = cur_gain + .1
            else:
                break #we're in the range now!

            set_gain(new_gain)
            cur_gain = new_gain
            count += 1

        if (count < 310) | (cur_gain == 0):
            print("Exposure Adjustment Complete.")
            return l_mean
        else:
            print("Exposure Adjustment Incomplete.")
            return -1

    except Exception as e:
        print(e)
        print("Error occured!")
        return -2


if __name__ == "__main__":

    ########### SETUP STUFF
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time = 2000)
    clock = time.clock()

    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)
    i2c_obj.deinit() # Fully reset I2C device...
    i2c_obj = pyb.I2C(2, pyb.I2C.SLAVE, addr=0x12)

    #get in focus balance. You have two seconds.
    t_start = time.ticks()
    t_elapsed = 0
    while(t_elapsed < 1): #ignore bc 1 ms
        img = sensor.snapshot()
        t_elapsed = time.ticks() - t_start

    sensor.set_auto_gain(False) # must be turned off for color tracking
    sensor.set_auto_whitebal(False) # must be turned off for color tracking
    sensor.set_auto_exposure(False)
    sensor.set_contrast(+3)

    print()
    pre_adjust_r_gain = sensor.__read_reg(0x02)
    pre_adjust_g_gain = sensor.__read_reg(0x03)
    pre_adjust_b_gain = sensor.__read_reg(0x01)
    pre_adjust_overall_gain = sensor.__read_reg(0x00)
    pre_adjust_exposure = (sensor.__read_reg(0x08) << 8) + sensor.__read_reg(0x10)

    print("R gain: " + str(pre_adjust_r_gain))
    print("G gain: " + str(pre_adjust_g_gain))
    print("B gain: " + str(pre_adjust_b_gain))
    print("Overall gain: " + str(pre_adjust_overall_gain))
    print("exposure: " + str(pre_adjust_exposure))
    print('------------------------------------')

    set_l_mean = set_custom_exposure() #default thresholds
    print(set_l_mean)

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

    img = sensor.snapshot()

    # should pull img_number from a text file and read the plant_id from a qr code or beaglebone
    # default mode is pyb.usb_mode('VCP+MSC')
    '''
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

    img_number = 1
    plant_id = 1
    img_id = str(img_number) + "_plant_" + str(plant_id)
    raw_str = "raw_" + str(img_id)
    raw_write = image.ImageWriter(raw_str)
    raw_write.add_frame(img)
    raw_write.close()
    img.compress(quality = 100)
    img.save("img_" + str(img_id))

    raw_read = image.ImageReader(raw_str)
    img = raw_read.next_frame(copy_to_fb = True, loop = False)
    raw_read.close()
    '''
    '''
    L = Lightness where 0 is black and 100 is white
    A = -127 is green and 128 is red
    B = -127 is blue and 128 is yellow.
    '''

    img_stats = img.get_statistics()





    ########### FIND BAD BLOBS

    unhealthy_full_l_mean = 0
    unhealthy_full_a_mean = 0
    unhealthy_full_b_mean = 0
    unhealthy_centroid_l_mean = 0
    unhealthy_centroid_a_mean = 0
    unhealthy_centroid_b_mean = 0
    unhealthy_blob_l_mean = 0
    unhealthy_blob_a_mean = 0
    unhealthy_blob_b_mean = 0
    healthy_full_l_mean = 0
    healthy_full_a_mean = 0
    healthy_full_b_mean = 0
    healthy_centroid_l_mean = 0
    healthy_centroid_a_mean = 0
    healthy_centroid_b_mean = 0
    healthy_blob_l_mean = 0
    healthy_blob_a_mean = 0
    healthy_blob_b_mean = 0

    blob_index = -1

    stage_one_bad_thresholds = [(20, 100, -10, 127, 3, 128)]

    for blob_index, stage_one_bad_blob in enumerate(img.find_blobs(stage_one_bad_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
        rect_stats = img.get_statistics(roi = stage_one_bad_blob.rect())

        print("stage_one_bad_blob: " + str(stage_one_bad_blob))
        print("density: " + str(stage_one_bad_blob.density()))
        print("full: " + str(rect_stats))
        unhealthy_full_l_mean += rect_stats[0]
        unhealthy_full_a_mean += rect_stats[8]
        unhealthy_full_b_mean += rect_stats[16]

        side_l = stage_one_bad_blob.density() * min(stage_one_bad_blob[2], stage_one_bad_blob[3])

        partial_hist = img.get_histogram(roi = (stage_one_bad_blob.cx() - round(side_l/2), stage_one_bad_blob.cy() - round(side_l/2), round(side_l), round(side_l)))
        partial_stats = partial_hist.get_statistics()
        print("partial: "+ str(partial_stats))
        unhealthy_centroid_l_mean += partial_stats[0]
        unhealthy_centroid_a_mean += partial_stats[8]
        unhealthy_centroid_b_mean += partial_stats[16]

        blob_stats = img.get_statistics(roi = stage_one_bad_blob.rect(), thresholds = stage_one_bad_thresholds)
        print("blob: "+ str(blob_stats))
        print("\n")

        unhealthy_blob_l_mean += blob_stats[0]
        unhealthy_blob_a_mean += blob_stats[8]
        unhealthy_blob_b_mean += blob_stats[16]

        img.draw_rectangle(stage_one_bad_blob.rect(), color = (255, 255, 255)) #purple
        #img.draw_rectangle((stage_one_bad_blob.cx() - round(side_l/2), stage_one_bad_blob.cy() - round(side_l/2), round(side_l), round(side_l)), color = (255, 85, 0))

    if blob_index != -1:
        unhealthy_full_l_mean = unhealthy_full_l_mean/(blob_index + 1)
        unhealthy_full_a_mean = unhealthy_full_a_mean/(blob_index + 1)
        unhealthy_full_b_mean = unhealthy_full_b_mean/(blob_index + 1)
        unhealthy_centroid_l_mean = unhealthy_centroid_l_mean/(blob_index + 1)
        unhealthy_centroid_a_mean = unhealthy_centroid_a_mean/(blob_index + 1)
        unhealthy_centroid_b_mean = unhealthy_centroid_b_mean/(blob_index + 1)
        unhealthy_blob_l_mean = unhealthy_blob_l_mean/(blob_index + 1)
        unhealthy_blob_a_mean = unhealthy_blob_a_mean/(blob_index + 1)
        unhealthy_blob_b_mean = unhealthy_blob_b_mean/(blob_index + 1)


    print("------------------------------------------------------------------------")



    ########### FIND GOOD BLOBS

    #stage_one_good_thresholds = [(img_stats.l_mean() - 1, 100, -127, img_stats.a_mean() - 4, img_stats.b_mean() - 8, 60)]
    stage_one_good_thresholds = [(25, 100, -127, -3, -15, 3)]

    for blob_index, stage_one_good_blob in enumerate(img.find_blobs(stage_one_good_thresholds, pixels_threshold=100, area_threshold=100, merge = False, margin = 15)):
        rect_stats = img.get_statistics(roi = stage_one_good_blob.rect())


        print("stage_one_good_blob: " + str(stage_one_good_blob))
        print("density: " + str(stage_one_good_blob.density()))
        print("full: "+ str(rect_stats))
        healthy_full_l_mean += rect_stats[0]
        healthy_full_a_mean += rect_stats[8]
        healthy_full_b_mean += rect_stats[16]

        side_l = stage_one_good_blob.density() * min(stage_one_good_blob[2], stage_one_good_blob[3])

        partial_hist = img.get_histogram(roi = (stage_one_good_blob.cx() - round(side_l/2), stage_one_good_blob.cy() - round(side_l/2), round(side_l), round(side_l)))
        partial_stats = partial_hist.get_statistics()
        print("partial: "+ str(partial_stats))

        healthy_centroid_l_mean += partial_stats[0]
        healthy_centroid_a_mean += partial_stats[8]
        healthy_centroid_b_mean += partial_stats[16]

        blob_stats = img.get_statistics(roi = stage_one_good_blob.rect(), thresholds = stage_one_good_thresholds)
        print("blob: "+ str(blob_stats))
        print("\n")

        healthy_blob_l_mean += blob_stats[0]
        healthy_blob_a_mean += blob_stats[8]
        healthy_blob_b_mean += blob_stats[16]

        img.draw_rectangle(stage_one_good_blob.rect(), color = (0, 0, 0)) #black
        #img.draw_rectangle((stage_one_good_blob.cx() - round(side_l/2), stage_one_good_blob.cy() - round(side_l/2), round(side_l), round(side_l)), color = (255, 85, 0))

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
        healthy_blob_l_mean = healthy_blob_l_mean/(blob_index + 1)
        healthy_blob_a_mean = healthy_blob_a_mean/(blob_index + 1)
        healthy_blob_b_mean = healthy_blob_b_mean/(blob_index + 1)


    print(img.compress_for_ide(quality = 100))

    print("~~~~~~~~~~~~~~~ RESULTS: ~~~~~~~~~~~~~~~~")
    print("good thresholds: " + str(stage_one_good_thresholds))
    print("bad thresholds: " + str(stage_one_bad_thresholds))
    print("unhealthy full l mean: " + str(unhealthy_full_l_mean))
    print("unhealthy full a mean: " + str(unhealthy_full_a_mean))
    print("unhealthy full b mean: " + str(unhealthy_full_b_mean))
    #print("unhealthy centroid l mean: " + str(unhealthy_centroid_l_mean))
    #print("unhealthy centroid a mean: " + str(unhealthy_centroid_a_mean))
    #print("unhealthy centroid b mean: " + str(unhealthy_centroid_b_mean))
    print("unhealthy blob l mean: " + str(unhealthy_blob_l_mean))
    print("unhealthy blob a mean: " + str(unhealthy_blob_a_mean))
    print("unhealthy blob b mean: " + str(unhealthy_blob_b_mean))
    print("healthy full l mean: " + str(healthy_full_l_mean))
    print("healthy full a mean: " + str(healthy_full_a_mean))
    print("healthy full b mean: " + str(healthy_full_b_mean))
    #print("healthy centroid l mean: " + str(healthy_centroid_l_mean))
    #print("healthy centroid a mean: " + str(healthy_centroid_a_mean))
    #print("healthy centroid b mean: " + str(healthy_centroid_b_mean))
    print("healthy blob l mean: " + str(healthy_blob_l_mean))
    print("healthy blob a mean: " + str(healthy_blob_a_mean))
    print("healthy blob b mean: " + str(healthy_blob_b_mean))



