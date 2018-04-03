import struct,time,requests,dbConnect
from serial import Serial


def check_for_sd():
	try:
		f = open('/media/3472-745B/README')
		f.close()
		print 'SD Card Connected'
		return 1
	except IOError:
		print 'WARNING: SD Card Not Connected.'
		return -1
		
##########################################
### Sends a dummy tuple to test serial port.	
def test_port():
	cmd = (b'Testing',)
	formatstr = '@%is' % len(cmd[0])
	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		return 1
	else:
		return -1
		
#####################################################
## Beaglebone -> Camera Serial Communication
def send_msg(formatstr,msg):
	try:
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
	except:
		return -1
	

########################################################
## Camera -> Beaglebone Serial Communication
## Note: On the Beaglebone (in pyserial), the read() function is blocking
## I.E. It will read until the serial port's timeout is reached, OR
## until the given number of bytes have been read.
def recv_msg():
	#Receive stage 1: Size of the message's format string
	formatstr_size = struct.unpack('@i',port.read(4))[0]
	
	#Handles camera errors
	if formatstr_size>1000:
		print('Message receipt aborted: Camera error occurred')
		errmsg = port.read(port.inWaiting())
		port.flushInput()
		print errmsg
		return (errmsg,)
		
	#Receive stage 2: The message's format string
	numstr = '@%is' % formatstr_size
	formatstr = struct.unpack(numstr,port.read(formatstr_size))[0]
	#Receive stage 3: The data/message
	datasize = struct.calcsize(formatstr)
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
	db_filename = 'plant_%i_%s.jpg' % (plant_id,file_tstamp)
	if sd==1:
		bb_filepath = '/media/3472-745B/' + db_filename
	else:
		bb_filepath = '/media/images/' + db_filename
	try:	
		imgfile = open(bb_filepath,'w')
		imgfile.write(raw_img)
		imgfile.close()
	except:
		print 'WARNING: Image not saved locally.'
		
	#Upload the image to the hosting site
	if web==1:
		dbConnect.add_img(db_filename,bb_filepath)
		dbConnect.update_locations(plant_id,db_filename,db_tstamp)
	else:
		print 'WARNING: Image not uploaded.'
	
	return db_filename

###############################################
## Sends calibration command to the camera
def calibrate_camera():
	port.flushInput()
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
	port.flushInput()
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
		print data
		
		t = time.time()
		db_filename = save_img(raw_img,plant_id,t)
		
		db_tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(t)))
		#db_tuple = (db_tstamp,plant_id,data[0],db_filename,data[1],data[2],data[3],data[4])
		#Collect all of the below data from the data tuple:
		#vals = (tstamp,location_no,insects_present,imgfile,ndvi_val,ir_val,hlc,ulc)
		#dbConnect.add_measurement(vals)
	
	return (data,db_filename)

#Takes in the data returned from the camera
#Returns a tuple ready to be added to the database
def process_data(data_tuple):
	pass

sd = check_for_sd()	
web = dbConnect.check_for_internet()		
#Sets up Serial Connection
def connect_to_camera():
	for i in range(1,5):
		portname = '/dev/ttyACM%i' % i
		try:
			port=Serial(port=portname)
			port.inWaiting()
			test_port()
			port.flushInput()
			return port
		except:
			continue
	
port=connect_to_camera()
	

	



			
		
		


		
	
	




		


	

                



	
		
		
		
