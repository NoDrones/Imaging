# Hello World Example
#
# Welcome to the OpenMV IDE! Click on the green run arrow button below to run the script!

import sensor, image, time

sensor.reset()                      # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
sensor.skip_frames(time = 2000)     # Wait for settings take effect.
sensor.set_auto_gain(False)
sensor.set_auto_gain(False) # must be turned off for color tracking
sensor.set_auto_whitebal(False) # must be turned off for color tracking
clock = time.clock()                # Create a clock object to track the FPS.



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

            #cur_exposure_msb = sensor.__read_reg(0x08)
            #cur_exposure_lsb = sensor.__read_reg(0x10)
            #cur_exposure_time = (cur_exposure_msb << 8) + cur_exposure_lsb

            print("current gain: " + str(cur_gain))
            print("l_mean: " + str(l_mean))

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
    clock.tick()                    # Update the FPS clock.
    set_custom_exposure()
    img = sensor.snapshot()         # Take a picture and return the image.

                                    # to the IDE. The FPS should increase once disconnected.
