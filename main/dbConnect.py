#-------------------------------------------------------------------------------
# Name:		   module1
# Purpose:
#
# Author:	   Matt
#
# Created:	   29/01/2018
# Copyright:   (c) Matt 2018
# Licence:	   <your licence>
#-------------------------------------------------------------------------------

import pymysql,ftplib,time,requests

hostname="162.241.217.12"
username="nuinstig_goat"
password="kzzgBq_o]uVF"
database="nuinstig_goats"
charset = "utf8mb4"
cursorType = pymysql.cursors.DictCursor

def shutdown():
	connection.close()
	ftp.quit()


def check_for_internet():
	url = 'http://google.com'
	try:
		requests.get(url)
		print 'Internet connection established.'
		return 1
	except:
		print 'WARNING: No Internet connection.'
		return -1
web = check_for_internet()		

def connect():
	return pymysql.connect(host=hostname,
						 user=username,
						 password=password,
						 db=database,
						 charset=charset,
						 cursorclass=cursorType)

	# you must create a Cursor object. It will let
	#  you execute all the queries you need
   
def est_db_connection():
	#Establish database connection
	cnx = connect()
	cur = cnx.cursor()
	return (cnx,cur)

if web==1:
	(connection,cursor) = est_db_connection()

#Establish FTP connection & navigate to image dump directory
def est_ftp_connection():
	ftp = ftplib.FTP(host='nuinstigator.com',user='greg@nuinstigator.com',passwd='safezoneaccess')
	return ftp
   
if web==1:
	ftp = est_ftp_connection()

def select(table, selection=None, pred=None):
	statement = "SELECT "
	if selection is not None:
		statement += selection
	else:
		statement += "*"
	statement += ("FROM " + table)
	if pred is None:
		return statement
	else:
		statement += pred
	return statement
	
#Takes in a processed tuple
def add_measurement(values):

	#Values tuple should look like below:
	#(tstamp,location_no,insects_present,image,ir_val,healthy_leaf_count,unhealthy_leaf_count,color_healthy_mean,color_unhealthy_mean,ir_leaf_count,warning)
	
	statement = """INSERT INTO `measurements` (
		tstamp, location_no,insects_present,
		image,ir_val,healthy_leaf_count,
		unhealthy_leaf_count,color_healthy_mean,color_unhealthy_mean,
		ir_leaf_count,total_leaf_area,healthy_leaf_area,
		unhealthy_leaf_area,warning) 
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
	cnx = connection
	cur = cursor
	while(1):
		try:
			cur.execute(statement, values)
			cnx.commit()
			break
		except pymysql.err.OperationalError:
			if check_for_internet()==1:
				(cnx,cur) = est_db_connection()
				continue
			else:
				return -1
	return 1
	
def update_locations(loc_no,image,tstamp):
	statement = """UPDATE locations SET last_pic_saved = %s,ts_of_last_pic=%s WHERE location_no = %s"""
	cnx = connection
	cur = cursor
	while(1):
		try:
			cur.execute(statement,(image,tstamp,loc_no))
			cnx.commit()
			break
		except pymysql.err.OperationalError:
			if check_for_internet()==1:
				(cnx,cur) = est_db_connection()
				continue
			else:
				return -1
	return 1
	
def add_img(db_filename,bb_filepath):
	f = open(bb_filepath,'rb')
	cmd = 'STOR %s' % db_filename
	while(1):
		try:
			ftp.storbinary(cmd,f)
			break
		except:
			ftp = est_ftp_connection()
			continue
			
	f.close()
	


