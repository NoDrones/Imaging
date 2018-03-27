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
def save_img(raw_img, plant_id):
	#Write the image to a file
	filename = 'testimg%i.jpg' % plant_id
	imgfile = open(filename,'w')
	imgfile.write(raw_img)
	imgfile.close()
	
	#Upload the image to the hosting site
	dbConnect.add_img(filename,ftp)
	
	return filename

###############################################
## Sends calibration command to the camera
def calibrate_camera():
	cmd = (b'Calibrate',)
	formatstr = '@%is' % len(cmd[0])

	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		print data[0].decode()
		return 1
	else:
		return -1
			
################################################
## Sends command to camera to take pics & collect data
def collect_data(plant_id):
	cmd = (b'Go',)
	formatstr = '@%is' % len(cmd[0])
	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		#ADD DATA TO DATABASE HERE (dbConnect.add_vals(cnx,cur))
		print data
		raw_img = recv_img()
		imgfile = save_img(raw_img,plant_id)
		print '%s saved & uploaded!' % imgfile
		return (data,imgfile)

def stop():
	cmd = (b'Stop',)
	formatstr = '@%is' % len(cmd[0])
	success = send_msg(formatstr,cmd)
	if success==1:
		data = recv_msg()
		print data[0].decode()
		return 1
	else:
		return -1
		
def mainloop():
	### Move motor to calibration position
	calibrate_camera()
	
	for i in range(1,10):
		### Move motor to position i
		(data,imgfile) = collect_data(i)
	
	#Reset?

		
#Set up PySerial connection	
try:
	port = Serial(port='/dev/ttyACM0',baudrate=115200,timeout=5)
	port.inWaiting()
except:
	port = Serial(port='/dev/ttyACM1',baudrate=115200,timeout=5)	


#Set up Database and FTP connections
(cnx,cur,ftp) = dbConnect.est_connections()
		


	

                



	
		
		
		
