import image,time,pyb,ustruct

pyb.usb_mode('VCP+HID')
port = pyb.USB_VCP()
port.setinterrupt(-1)

#####################
#send_msg:
#Takes in a format string (str), message (tuple), and 
#Sends a message in three stages:
#	Stage 1: length of the message's format string as a 4-byte int
#	Stage 2: the message's format string as a str
#	Stage 3: the message itself as a tuple
#Assumes msg is a tuple of the form (x1,x2,...,xn) with any strings encoded as bytes and no "nested" tuples
#EVEN IF YOU ARE JUST SENDING ONE STRING, PUT IT IN A TUPLE BY ITSELF as (b'string',)
#fmtstr is a str
#Condition data as such before calling the function
def send_msg(format_str, msg):
	#Stage 1: Length of message's format string
	format_str_size = len(format_str)
	stg1_msg = ustruct.pack('@i', format_str_size)
	
	stg2_format_str = '@%is' % (format_str_size) # Format-stringception
	stg2_msg = ustruct.pack(stg2_format_str, format_str.encode()) #Stage 2: Send The message's format string
	
	stg3_msg = ustruct.pack(format_str, *msg) #Stage 3: The data tuple
	
	#Write the message(s) to the port
	try:
		port.write(stg1_msg)
		port.write(stg2_msg)
		port.write(stg3_msg)
		return 1
	except:
		return -1

		
##################################################
def recv_msg():

	#Best way to read a line from the USB_VCP - simulates a "blocking" read like pySerial uses
	def getln():
		t_start = time.ticks()
		elapsed_time = 0
		while elapsed_time < 20000: # 20 second timeout
			if port.any():
				msg = port.readline()
				return msg # Returns raw bytes message
			elapsed_time = time.ticks() - t_start
		return -1 # Returns failure
		
	try:
		stg1 = getln()
		format_str_size = ustruct.unpack('@3s', stg1)[0] # Receive stage 1- the size of the format string
		format_str_size = int(format_str_size.decode()) #Turns it back into an actual number

		format_stringception = '@%is' % format_str_size # The format string of the data's format string = format_stringception
		#Receive stage 2 - the format string
		stg2 = getln()
		format_str = ustruct.unpack(format_stringception, stg2)[0]
		format_str = format_str.decode()
		
		#Receive stage 3 - the Data
		stg3 = getln()
		data = ustruct.unpack(format_str, stg3)
				
		return data	
	except: return -1
		
#Takes in an uncompressed img 		
def send_img(img):
	try:
		size = img.size()
		packed_size = ustruct.pack('@i', size)
		port.write(packed_size)
		port.send(img)  #using port.write() doesn't send the full object for some reason - must have some bytes limit
		return 1
	except:
		return -1
	


#Timeout not implemented - may be unnecessary
def listen_for_trigger():
	while(1):
		if port.isconnected(): # Listen for the command/trigger
			try:
				command = recv_msg()[0].decode()
				return command
			except: return -1
				
				
				
				
				
				


		
		
		

		
										
				
	
	

