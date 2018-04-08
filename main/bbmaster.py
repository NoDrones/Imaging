
import struct,time,requests,dbConnect
from serial import Serial

###############################################
## Checks if the Beaglebone's SD card is recognized.
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
	
	db_filename = 'plant_%i_%s.jpg' % (plant_id,file_tstamp)
	if sd==1:
		bb_filepath = '/media/3472-745B/' + db_filename
	else:
		bb_filepath = '/media/images/' + db_filename
	try:	
		imgfile = open(bb_filepath,'w')
		imgfile.write(raw_img)
		imgfile.close()
		#Upload the image to the hosting site
		if web==1:
			dbConnect.add_img(db_filename,bb_filepath)
			dbConnect.update_locations(plant_id,db_filename,db_tstamp)
		else:
			print 'WARNING: Image not uploaded.'
		
	except:
		print 'WARNING: Image not saved locally.'
		
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
## Takes in an int with plant_id
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
		if 'IR Data Received' in recv_msg():
			data = recv_msg()
			t = time.time()
			db_filename = save_img(raw_img,plant_id,t) #Add image to database & update plant_id's most recent img
			db_tuple = process_data(data,t,db_filename,plant_id) #Process received data tuple
			dbConnect.add_measurement(db_tuple) #Add measurements to database

	return (data,db_filename)
	
#############################################################
#Takes in the data returned from the camera
#Returns a tuple ready to be added to the database
def process_data(data_tuple,t,db_imgfile,plant_id):

	
	#Returned tuple is in the following format:
	#(0)IR_leaves,(1) IR_mean, (2)ir_leaf_area (3)ir_warning str
	#(4) healthy_leaf_count, (5) unhealthy_leaf_count, (6) healthy_a_mean, (7) unhealthy_a_mean, (8) beetle_count, (9) healthy_leaf_area, (10) unhealthy_leaf_area, (11) color warning
	#2 integers,3 floats,string,2 integers,2 floats,1 integer string
	
	#Database tuple should be as follows:
	#(tstamp,location_no,insects_present,image,ir_val,healthy_leaf_count,unhealthy_leaf_count,color_healthy_mean,color_unhealthy_mean,ir_leaf_count,warning)
	db_tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(t)))
	insects_present = data_tuple[8]
	ir_val = data_tuple[1]
	healthy_leaf_count = data_tuple[4]
	unhealthy_leaf_count = data_tuple[5]
	color_healthy_mean = data_tuple[6]
	color_unhealthy_mean = data_tuple[7]
	ir_leaf_count = data_tuple[0]
	ir_leaf_area = data_tuple[2]
	healthy_leaf_area = data_tuple[9]
	unhealthy_leaf_area = data_tuple[10]
	
	warning = data_tuple[11].rstrip('\x00')
	#tstamp, location_no,insects_present,
	#image,ir_val,healthy_leaf_count,
	#unhealthy_leaf_count,color_healthy_mean,color_unhealthy_mean,
	#ir_leaf_count,ir_leaf_area,healthy_leaf_area,
	#unhealthy_leaf_area,warning
	return (db_tstamp,plant_id,insects_present,db_imgfile,ir_val,healthy_leaf_count,unhealthy_leaf_count,color_healthy_mean,color_unhealthy_mean,ir_leaf_count,ir_leaf_area,healthy_leaf_area,unhealthy_leaf_area,warning)

	
###########################################33	
#Sets up Serial Connection
def connect_to_camera():
	for i in range(0,10):
		portname = '/dev/ttyACM%i' % i
		try:
			port=Serial(port=portname,timeout=10)
			port.inWaiting()
			test_port()
			port.flushInput()
			return port
		except:
			continue


sd = check_for_sd()	
web = dbConnect.check_for_internet()			
port=connect_to_camera()
	


#######################################################
###### MOTOR CONTROL
#######################################################

#*****************************************************
# pwmChannel1 = "P9_14" # Clockwise
# pwmChannel2 = "P8_13" # Counterclockwise
# optoChannel = "P9_15"

# revsPerPlant = 13
# totalPlants = 6
# #*****************************************************

# currentRevs = 0
# currentPlant = 0

# GPIO.setup(optoChannel, GPIO.IN)

# PWM.start(pwmChannel1, 0, 10000)
# print ("here")
# while currentPlant < totalPlants:
    # print ("plant: " + str(currentPlant))
    # PWM.set_duty_cycle(pwmChannel1, 10)
    # while currentRevs < revsPerPlant:
        # print (currentRevs)
        # GPIO.wait_for_edge(optoChannel, GPIO.FALLING)
        # currentRevs += 1
    # PWM.set_duty_cycle(pwmChannel1, 0)
    # currentPlant += 1
    # currentRevs = 0
    # time.sleep(5)
	
	# if currentPlant==1:
		# calibrate_camera()
	# else:
		# while(1):
			# try:
				# (data,img) = collect_data(currentPlant)
				# print data
				# break
			# except:
				# time.sleep(4)
				# continue
		
    # #*****************************************************
    # # send trigger to start taking pics
    # # some sort of trigger to move on - this trigger needs to come from knowing we are done with pics
    # #*****************************************************
	
# PWM.stop(pwmChannel1)
# PWM.cleanup()
# time.sleep(10)
# currentRevs = 0
# PWM.start(pwmChannel2, 0, 10000)
# PWM.set_duty_cycle(pwmChannel2, 10)
# # print ("going back")
# # while currentRevs < (totalPlants * revsPerPlant):
    # # print (currentRevs)
    # # GPIO.wait_for_edge(optoChannel, GPIO.FALLING)
    # # currentRevs += 1
# PWM.stop(pwmChannel2)
# PWM.cleanup()	



##########################################
#####GUI STUFF
##########################################

# from Tkinter import *
# from PIL import Image,ImageTk

# root = Tk()
# root.wm_title('Autonomous Farm Robot')
# root.config(background= '#FFFFFF')

# root.geometry('{}x{}'.format(460, 350))

# topframe = Frame(root,width=400,height=200)
# imgframe = Frame(root,width=400,height=200)

# root.grid_rowconfigure(1,weight=1)
# root.grid_columnconfigure(0,weight=1)

# topframe.grid(row=0,sticky='ns')
# imgframe.grid(row=1,sticky='ns')

# def calib_button():
	# calibrate_camera()
	
# def measurement_btn(piclabel,plant_id):
	# (data,newimg) = collect_data(plant_id)
	# try:
		# imgfilename = '/media/images/' + newimg
		# img = Image.open(imgfilename)
	# except:
		# imgfilename = '/media/3472-745B/' + newimg
		# img = Image.open(imgfilename)

	# photo = ImageTk.PhotoImage(img)
	# piclabel.configure(image=photo)
	# piclabel.image = photo
		

# calibrate_button = Button(topframe,text='Calibrate Camera',command = calib_button)
# calibrate_button.grid(row=0,column=0,columnspan=4)

# Button(topframe,text='0',width=8,command=lambda: measurement_btn(piclabel,0)).grid(row=1,column=0)
# Button(topframe,text='1',width=8,command=lambda: measurement_btn(piclabel,1)).grid(row=1,column=1)
# Button(topframe,text='2',width=8,command=lambda: measurement_btn(piclabel,2)).grid(row=1,column=2)
# Button(topframe,text='3',width=8,command=lambda: measurement_btn(piclabel,3)).grid(row=1,column=3)
# Button(topframe,text='4',width=8,command=lambda: measurement_btn(piclabel,4)).grid(row=2,column=0)
# Button(topframe,text='5',width=8,command=lambda: measurement_btn(piclabel,5)).grid(row=2,column=1)
# Button(topframe,text='6',width=8,command=lambda: measurement_btn(piclabel,6)).grid(row=2,column=2)
# Button(topframe,text='7',width=8,command=lambda: measurement_btn(piclabel,7)).grid(row=2,column=3)
# Button(topframe,text='8',width=8,command=lambda: measurement_btn(piclabel,8)).grid(row=3,column=0)
# Button(topframe,text='9',width=8,command=lambda: measurement_btn(piclabel,9)).grid(row=3,column=1)
# Button(topframe,text='10',width=8,command=lambda: measurement_btn(piclabel,10)).grid(row=3,column=2)
# Button(topframe,text='11',width=8,command=lambda: measurement_btn(piclabel,11)).grid(row=3,column=3)
# Button(topframe,text='12',width=8,command=lambda: measurement_btn(piclabel,12)).grid(row=4,column=0)
# Button(topframe,text='13',width=8,command=lambda: measurement_btn(piclabel,13)).grid(row=4,column=1)
# Button(topframe,text='14',width=8,command=lambda: measurement_btn(piclabel,14)).grid(row=4,column=2)
# Button(topframe,text='15',width=8,command=lambda: measurement_btn(piclabel,15)).grid(row=4,column=3)


# img = Image.open('/media/images/plant_0_0404_17-13-27.jpg')
# photo = ImageTk.PhotoImage(img)
# piclabel = Label(imgframe,image = photo)
# piclabel.image = photo
# piclabel.grid(row=0,column=0)

# root.mainloop()

	
		


		
	
	




		


	

                



	
		
		
		
