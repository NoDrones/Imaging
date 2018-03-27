#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Matt
#
# Created:     29/01/2018
# Copyright:   (c) Matt 2018
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import pymysql,ftplib,time

hostname="162.241.217.12"
username="nuinstig_goat"
password="kzzgBq_o]uVF"
database="nuinstig_goats"
charset = "utf8mb4"
cursorType = pymysql.cursors.DictCursor

def connect():
    return pymysql.connect(host=hostname,
                         user=username,
                         password=password,
                         db=database,
                         charset=charset,
                         cursorclass=cursorType)

    # you must create a Cursor object. It will let
    #  you execute all the queries you need

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

def add_measurement(cursor, values):
    statement = """INSERT INTO `measurements` (tstamp, location_no,
        insects_present, image, ndvi_val, ir_val, healthy_leaf_count,
        unhealthy_leaf_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    cursor.execute(statement, tuple(values))
	
def update_locations(cursor,loc_no,image,tstamp):
	statement = """UPDATE locations SET last_pic_saved = %s,ts_of_last_pic=%s WHERE location_no = %s"""
	cursor.execute(statement,(image,tstamp,loc_no))

def est_connections():
	#Establish database connection
	cnx = connect()
	cur = cnx.cursor()

	#Establish FTP connection & navigate to image dump directory
	ftp = ftplib.FTP(host='nuinstigator.com',user='greg@nuinstigator.com',passwd='safezoneaccess')
	return (cnx,cur,ftp)

def add_vals(cnx,cur):
	tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))
	location_no = 1
	insects_present = True
	image = 'testimg1.jpg'
	ndvi_val = 420
	ir_val = 69
	hlc = 4
	ulc = 2

	vals = (tstamp,location_no,insects_present,image,ndvi_val,ir_val,hlc,ulc)
	add_measurement(cur,vals)
	update_locations(cur,location_no,image,tstamp)
	
	
def add_img(filename,ftp):
	f = open(filename,'rb')
	cmd = 'STOR %s' % filename
	ftp.storbinary(cmd,f)
	f.close()
