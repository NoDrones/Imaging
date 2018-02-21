# Hello World Example
#
# Welcome to the OpenMV IDE! Click on the green run arrow button below to run the script!

import sensor, image, time

sensor.reset()                      # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
sensor.skip_frames(time = 2000)     # Wait for settings take effect.
sensor.set_auto_gain(False) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
clock = time.clock()                # Create a clock object to track the FPS.



def set_custom_exposure(high_l_median_thresh = 7, low_l_median_thresh = 6):
    try:
        img = sensor.snapshot()         # Take a picture and return the image.
        img_stats = img.get_statistics()
        l_median = img_stats.l_median()

        while((l_median > high_l_median_thresh) | (l_median < low_l_median_thresh)):

            img = sensor.snapshot()         # Take a picture and return the image.
            img_stats = img.get_statistics()
            l_median = img_stats.l_median()

            cur_exposure_msb = sensor.__read_reg(0x08)
            cur_exposure_lsb = sensor.__read_reg(0x10)
            cur_exposure = (cur_exposure_msb << 8) + cur_exposure_lsb

            #print("current exposure: " + str(cur_exposure))
            #print("l_median: " + str(l_median))

            if l_median > high_l_median_thresh:
                new_exposure = cur_exposure - 4
            elif l_median < low_l_median_thresh:
                new_exposure = cur_exposure + 4
            else:
                break #we're in the range now!

            sensor.set_auto_exposure(False, value = new_exposure)
        return 1
    except:
        print("Error occured!")
        return -1


while(True):
    clock.tick()                    # Update the FPS clock.
    set_custom_exposure()
    img = sensor.snapshot()         # Take a picture and return the image.

                                    # to the IDE. The FPS should increase once disconnected.
