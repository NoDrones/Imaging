#Author: Calvin Ryan
import sensor, math, utime


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
	if ((0b00000100 & sensor.__read_reg(0x5C)) == 0):
		b_gain = sensor.__read_reg(0x01) / 0x40
		r_gain = sensor.__read_reg(0x02) / 0x40
		g_gain = sensor.__read_reg(0x03) / 0x40
	else:
		b_gain = sensor.__read_reg(0x01) / 0x80
		r_gain = sensor.__read_reg(0x02) / 0x80
		g_gain = sensor.__read_reg(0x03) / 0x80
	# Exposure time = exposure_value*T(row_interval) ... not sure what T(row_interval) is, but this sounds linear
	exposure_value = sensor.__read_reg(0x08)
	return (gain, r_gain, g_gain, b_gain, exposure_value)

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
	print("Start set custom")
	try:
		sensor.set_auto_whitebal(True)
		print("Setting WB...") #Need to do this while flash is on to keep colors true.
		utime.sleep_ms(1000)
		sensor.set_auto_whitebal(False)
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

		cur_gain = get_gain()[0]

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
