import struct,time,dbConnect
from serial import Serial

#####################################################
## Beaglebone -> Camera Serial Communication
def send_msg(formatstr,msg):
	#Stage 1: Send Length of message's format string
	#But it has to send it as an ascii string (and not an int) because fuck you
	formatstr_size = len(formatstr)
	numstr = '%03d' % formatstr_size
	stg1_msg = struct.pack('@3s',numstr)
	port.write(stg1_msg)

	#Stage 2: Send The message's format string
	stg2_formatstr = '@%is' % (formatstr_size)
	stg2_msg = struct.pack(stg2_formatstr,formatstr)
	port.write(stg2_msg)

	#Stage 3: Send The data
	stg3_msg = struct.pack(formatstr,*msg)
	port.write(stg3_msg)
	
	return 1
	

########################################################
## Camera -> Beaglebone Serial Communication
## Note: On the Beaglebone (in pyserial), the read() function is blocking
## I.E. It will read until the serial port's timeout is reached, OR
## until the given number of bytes have been read.
def recv_msg():
	#Receive stage 1: Size of the message's format string
	formatstr_size = struct.unpack('@i',port.read(4))[0]
	print formatstr_size
	#Receive stage 2: The message's format string
	numstr = '@%is' % formatstr_size
	formatstr = struct.unpack(numstr,port.read(formatstr_size))[0]
	print formatstr
	#Receive stage 3: The data/message
	datasize = struct.calcsize(formatstr)
	print datasize
	data = struct.unpack(formatstr,port.read(datasize))

	if data:
		return data
	else:
		return -1

############################################
## Camera sends jpg bytes to Beaglebone
def recv_img():
	sz = struct.unpack('@i',port.read(4))[0]
	print 'Reading %i bytes: ' % sz
	raw_img = port.read(sz)
	return raw_img

############################################
## Saves image to disk and uploads to FTP server
def save_img(raw_img, plant_id,t):
	
	
	file_tstamp = time.strftime('%m%d_%H-%M-%S', time.localtime(int(t)))
	db_tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(t)))
	
	#Write the image to a file
	filename = 'plant_%i_%s.jpg' % (plant_id,file_tstamp)
	filepath = '/media/3472-745B/' + filename
	imgfile = open(filepath,'w')
	imgfile.write(raw_img)
	imgfile.close()
	
	#Upload the image to the hosting site
	dbConnect.add_img(filename,filepath)
	#Update locations table
	#dbConnect.update_locations(plant_id,filename,db_tstamp)
	
	return filename

###############################################
## Sends calibration command to the camera
def calibrate_camera():
	cmd = (b'calibrate',)
	formatstr = '@%is' % len(cmd[0])

	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		print data[0].decode()
		return 1
	else:
		return -1
			
######################################################
## Sends command to camera to take pics & collect data
## Takes in 2 ints with plant_id and image number
def collect_data(plant_id):


	## Send initialization trigger
	cmd = (b'trigger',)
	formatstr = '@%is' % len(cmd[0])
	success = send_msg(formatstr,cmd)
	
	#Send image information
	data_to_send = (plant_id,)
	success = send_msg('@i',data_to_send)
	
	if success==1:
		raw_img = recv_img()
		data = recv_msg()
		t = time.time()
		
		
		imgfile = save_img(raw_img,plant_id,t)
		#print '%s saved & uploaded!' % imgfile

		
		###########################
		#ADD DATA TO DATABASE HERE
		###########################
		tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))
		#Collect all of the below data from the data tuple:
		#vals = (tstamp,location_no,insects_present,imgfile,ndvi_val,ir_val,hlc,ulc)
		#dbConnect.add_measurement(vals)
		#dbConnect.update_locations(location_no,imgfile,tstamp)
	
	return (data,imgfile)
			


##########################################
### Sends a dummy tuple to test serial port.	
def test_port():
	cmd = (b'Testing',)
	formatstr = '@%is' % len(cmd[0])
	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		print data[0].decode()
		return 1
	else:
		return -1

		
##########################################
## What will soon be the main loop: sends calibration command, moves motor, and collects data.
def mainloop():
	calibrate_camera()
	time.sleep(2)
	for i in range(1,5):
		for j in range(1,10):
			### Move motor to position i
			(data,imgfile) = collect_data(j,i)
			time.sleep(3)
			
	
	#Reset?

		
try:#Set up PySerial connection	
	port = Serial(port='/dev/ttyACM0',baudrate=115200,timeout=5)
	test_port()
except:
	try:
		port = Serial(port='/dev/ttyACM1',baudrate=115200,timeout=5)	
		test_port()
	except:
		print 'Camera not connected.'
		
	
	




		


	

                



	
		
		
		
