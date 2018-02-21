#Author: Calvin Ryan
import sensor, image, time, pyb, math

def set_custom_exposure(high_l_mean_thresh = 10, low_l_mean_thresh = 9):
    try:
        print("Starting Exposure Adjustment...")
        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        l_mean = img_stats.l_mean()
        count = 0

        while(((l_mean > high_l_mean_thresh) | (l_mean < low_l_mean_thresh))) & (count < 1000):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            l_mean = img_stats.l_mean()

            cur_exposure_msb = sensor.__read_reg(0x08)
            cur_exposure_lsb = sensor.__read_reg(0x10)
            cur_exposure = (cur_exposure_msb << 8) + cur_exposure_lsb

            print("current exposure: " + str(cur_exposure))
            print("l_mean: " + str(l_mean))

            if l_mean > high_l_mean_thresh:
                new_exposure = cur_exposure - 2
            elif l_mean < low_l_mean_thresh:
                new_exposure = cur_exposure + 2
            else:
                break #we're in the range now!

            sensor.set_auto_exposure(False, value = new_exposure)
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

    l_red = pyb.LED(1)
    l_green = pyb.LED(2)
    l_blue = pyb.LED(3)
    l_IR = pyb.LED(4)

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


    img_stats = img.get_statistics()

    sensor.set_auto_gain(False) # must be turned off for color tracking
    sensor.set_auto_whitebal(False) # must be turned off for color tracking
    set_l_mean = set_custom_exposure() #default thresholds
    sensor.set_contrast(+3)

    l_red.toggle() #heartbeat
    l_green.toggle() #green heartbeat

    img = sensor.snapshot()

    '''
    L = Lightness where 0 is black and 100 is white
    A = -127 is green and 128 is red`
    B = -127 is blue and 128 is yellow.
    '''

    img_hist = img.get_histogram()
    img_stats = img_hist.get_statistics()


    stage_one_thresholds = [(img_stats.l_mean() - 1, 100, -127, img_stats.a_mean() - 4, img_stats.b_mean() - 8, 60)]

    stage_one_blobs = []

    for blob_index, stage_one_blob in enumerate(img.find_blobs(stage_one_thresholds, pixels_threshold=250, area_threshold=250, merge = True, margin = 15)):
        blob_hist = img.get_histogram(roi = (stage_one_blob[0] - 10, stage_one_blob[1] - 10, stage_one_blob[2] + 20, stage_one_blob[3] + 20))
        blob_stats = blob_hist.get_statistics()

        print("1st check: " + str(stage_one_blob))

        #if (blob_stats.l_mean() > img_stats.l_mean())):
        #if (abs(blob_stats.a_mean() - blob_stats.b_mean()) > 6) & ((blob_stats.l_mean() > img_stats.l_lq()) & (blob_stats.l_mean() < img_stats.l_uq())): #& (blob_stats.a_max() - blob_stats.a_min() > 20) & (blob_stats.b_max() - blob_stats.b_min() > 20): #if the a and b histograms are close together it means the color is probably white and should be discarded
        if ((abs(blob_stats.a_mean() - blob_stats.b_mean()) > 6) & (blob_stats.l_mean() > set_l_mean + 2) & (blob_stats.l_mean() < (set_l_mean + 3 * blob_stats.l_stdev()))):
            print("2nd check: " + str(stage_one_blob))

            img.draw_rectangle(stage_one_blob.rect(), color = (255, 255, 0)) #yellow
            img.draw_rectangle((stage_one_blob[0] - 10, stage_one_blob[1] - 10, stage_one_blob[2] + 20, stage_one_blob[3] + 20), color = (255, 0, 255)) #purple

            for x in range(stage_one_blob[2] + 20):
                for y in range(stage_one_blob[3] + 20):
                    try:
                        pix_location = [stage_one_blob[0] - 10 + x, stage_one_blob[1] - 10 + y]
                        pix_vals = img.get_pixel(pix_location[0], pix_location[1])
                        lab_pix_vals = image.rgb_to_lab(pix_vals)

                        if ((lab_pix_vals[1] < (blob_stats.a_mean() + 2 * blob_stats.a_stdev())) & (lab_pix_vals[0] >= (blob_stats.l_mean() - .1 * blob_stats.l_stdev()))): #& (abs(lab_pix_vals[2] - lab_pix_vals[1]) > 10) & (lab_pix_vals[0] > (blob_stats.l_mean() - 10)):
                            pass
                        else:
                            img.set_pixel(pix_location[0], pix_location[1], (255, 0, 0))
                    except:
                        pass #pixel doesn't exist


            stage_two_thresholds = [(0, 100, -127, 0, -40, 10)]

            for blob_index, stage_two_blob in enumerate(img.find_blobs(stage_two_thresholds, roi = (stage_one_blob[0] - 10, stage_one_blob[1] - 10, stage_one_blob[2] + 20, stage_one_blob[3] + 20), pixels_threshold= 100, area_threshold=100, merge = False)):
                img.draw_rectangle(stage_two_blob.rect(), color = (255, 255, 0)) #yellow
                img.draw_circle(stage_two_blob.cx(), stage_two_blob.cy(), int(stage_two_blob.density() * min(stage_two_blob[2], stage_two_blob[3])))

            lab_pix_grid_vals = []
            '''
            #smoothing
            for x in range(stage_one_blob[2] + 20):
                for y in range(stage_one_blob[3] + 20):`
                    try:
                        pix_location = [stage_one_blob[0] - 10 + x, stage_one_blob[1] - 10 + y]
                        for x_sub in range(3):
                            for y_sub in range(3):
                                #print(str(x_sub) + ", " + str(y_sub))
                                pix_vals = img.get_pixel(pix_location[0] - 1 + x_sub, pix_location[1] - 1 + y_sub)
                                lab_pix_grid_vals.append(image.rgb_to_lab(pix_vals))

                        # |------------
                        # | 0 | 3 | 6 |
                        # |------------
                        # | 1 | 4 | 7 |
                        # |------------
                        # | 2 | 5 | 8 |
                        # |------------

                        average0 = (lab_pix_grid_vals[0] + lab_pix_grid_vals[1] + lab_pix_grid_vals[2])/(3, 3, 3)
                        average1 = (lab_pix_grid_vals[1] + lab_pix_grid_vals[2] + lab_pix_grid_vals[5])/(3, 3, 3)
                        average2 = (lab_pix_grid_vals[2] + lab_pix_grid_vals[5] + lab_pix_grid_vals[8])/(3, 3, 3)
                        average3 = (lab_pix_grid_vals[5] + lab_pix_grid_vals[8] + lab_pix_grid_vals[7])/(3, 3, 3)
                        average4 = (lab_pix_grid_vals[8] + lab_pix_grid_vals[7] + lab_pix_grid_vals[6])/(3, 3, 3)
                        average5 = (lab_pix_grid_vals[8] + lab_pix_grid_vals[7] + lab_pix_grid_vals[6])/(3, 3, 3)
                        average6 = (lab_pix_grid_vals[7] + lab_pix_grid_vals[6] + lab_pix_grid_vals[3])/(3, 3, 3)
                        average7 = (lab_pix_grid_vals[6] + lab_pix_grid_vals[3] + lab_pix_grid_vals[0])/(3, 3, 3)
                        average_list = [average0, average1, average2, average3, average4, average5, average6, average7 ]
                        dif_list = [abs(lab_pix_grid_vals[4] - average0), abs(lab_pix_grid_vals[4] - average1), abs(lab_pix_grid_vals[4] - average2), abs(lab_pix_grid_vals[4] - average3), abs(lab_pix_grid_vals[4] - average4), abs(lab_pix_grid_vals[4] - average5), abs(lab_pix_grid_vals[4] - average6), abs(lab_pix_grid_vals[4] - average7)]

                        min_dif_index = min(dif_list)

                        img.set_pixel(pix_location[0], pix_location[1], average_list(dif_list.index(min_dif_index)))

                    except:
                        pass #pixel dsoesn't exist
            '''




            #if ((abs(blob_stats.a_mean() - blob_stats.b_mean()) > 10) | ((blob_stats.l_mean() > img_stats.l_lq()) & (blob_stats.l_mean() < img_stats.l_uq()))) & (blob_stats.a_max() - blob_stats.a_min() > 20) & (blob_stats.b_max() - blob_stats.b_min() > 20): #if the a and b histograms are close together it means the color is probably white and should be discarded
            '''
            img.draw_cross(stage_one_blob.cx(), stage_one_blob.cy())
            blob_slope = math.tan(stage_one_blob.rotation())
            print("slope: " + str(blob_slope))
            img.draw_cross(0,0, size = 10) #this is weird. origin is in the top left corner
            img.draw_cross(310, 230, size = 10, color = (0, 0, 255)) #this is weird. positive window limit is in the bottom right corner.
            img.draw_line((stage_one_blob.cx(), stage_one_blob.cy(), stage_one_blob.cx() + 40, stage_one_blob.cy() - round(blob_slope * 40)), color = (255, 255, 0))
            img.draw_line((stage_one_blob.cx(), stage_one_blob.cy(), stage_one_blob.cx() - 40, stage_one_blob.cy() + round(blob_slope * 40)), color = (255, 255, 0))
            print("density: " + str(stage_one_blob.density()))
            '''

    '''
    img_writer = image.ImageWriter('./snap_' + str(time.ticks()) + '.bin')
    img_writer.add_frame(img)
    img_writer.close()
    '''

    print(img.compress_for_ide(quality = 50))


    #save_jpeg.save('./snap_' + str(time.ticks()))



