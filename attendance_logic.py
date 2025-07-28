from py532lib.i2c import Pn532_i2c
from py532lib.frame import *
from py532lib.constants import *

import lgpio
import mariadb
import mysql.connector
import time
import threading
import subprocess
import datetime
import logging
import os
import sys

from datetime import datetime, timedelta
from collections import defaultdict
from buzzer import beep
from active_buzzer import active_beep

from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont

from check_internet import *
from sync_manual_attendance import sync_manual_attendance_remote_to_local
from sync_student_attendance import sync_student_attendance_local_to_remote
from sync_teacher_attendance import sync_teacher_attendance_local_to_remote
from sync_room_logs import sync_room_logs_local_to_remote
from sync_auth_user import sync_auth_user_remote_to_local
from sync_users import sync_users_remote_to_local
from sync_students import sync_students_remote_to_local
from sync_teachers import sync_teachers_remote_to_local
from sync_admins import sync_admins_remote_to_local
from sync_rooms import sync_rooms_remote_to_local
from sync_courses import sync_courses_remote_to_local
from sync_students_courses import sync_students_courses_remote_to_local

# PN532 Setup
pn532 = Pn532_i2c()
pn532.SAMconfigure()

# GPIO setup
buzzer_pin = 18

# Open GPIO chip (usually 0 for Raspberry Pi)
chip = lgpio.gpiochip_open(0)
# lgpio.gpio_write(chip, buzzer_pin, 1) # Default OFF

# Screen Setup
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)

# Setup Logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('/home/rpi2/Thesis/py532lib/rpi2.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Remote database connection
def connect_remote_db():
    return mysql.connector.connect(
        host="",            # Insert public IP of the cloud database server here       
        user="",            # Insert user of the cloud database
        password="",        # Insert password
        database=""         # Insert name of the database
	)

# Local database connection
def connect_local_db():
    return mariadb.connect(
        host="localhost",          
        user="root",               
        password="",        # Insert password of the root user of the local database
        database=""         # Insert database name of local database
	)

# Function for checking active course given the day
def get_day_abbreviation(day_name):
    day_mapping = {
        "Monday": ["MON", "MW"],
        "Tuesday": ["TUE", "TTH"],
        "Wednesday": ["WED", "MW"],
        "Thursday": ["THU", "TTH"],
        "Friday": ["FRI", "FSA"],
        "Saturday": ["SAT", "FSA"],
        "Sunday": ["SUN"]
    }
    return day_mapping.get(day_name, [])

# Timedelta to Time    
def convert_to_time(value):
    if isinstance(value, timedelta):
        time_value = (datetime.min + value).time()
    else:
        time_value = value
    
    return time_value.strftime('%I:%M:%S.%f %p')

# Function to get the current date, day and time
def get_current_date_day_time():
    current_datetime = datetime.now()
    current_date = current_datetime.date()
    current_day = current_datetime.strftime('%A')  
    current_time = current_datetime.time()  
    return current_date, current_day, current_time

# Function for reading ID and serial 
def read_nfc_card():
    try:
        nfc_card = pn532.read_mifare()
        if nfc_card:
            card_data = nfc_card.get_data()
            card_string = ':'.join(format(byte, '02x') for byte in card_data)
            nfc_uid = card_string[-11:].upper()

            return nfc_uid
        else:
            return None
    except Exception as e:
        print(f"Error reading NFC card: {e}")
        return None
   
# Workflow when ID is not blocked        
def nfc_card_workflow(nfc_uid, room_id, room_name):
    db_connection = None
    cursor = None
    try:
        db_connection = connect_local_db()
        cursor = db_connection.cursor()
        
        # Get current date, day, and time
        current_date, current_day, current_time = get_current_date_day_time()
        
        # Get ID of room
        room_id = room_id
        room_name = room_name
       
        # Get course ID of active course
        course_id = check_active_class(room_id, room_name, current_day, current_time)
        

        # Get student and teacher IDs from NFC UID
        student_id = get_student_by_uid(nfc_uid)
        teacher_id = get_teacher_by_uid(nfc_uid)
        
        # For displaying the NFC UID to OLED
        screen_uid = nfc_uid.replace(":", "").lower()
        
        # If there is an active class at the moment
        if course_id:
            course_info = get_course_name_by_id(course_id)
            course_code, section = course_info
            course_details = f"{course_code} {section}"
            
            start_time, end_time, course_hours, course_minutes = get_course_time_duration(course_id)
            current_time_dt = datetime.combine(datetime.today(), current_time)
            
            if course_hours == 1 and course_minutes == 30:
                tap_out_mins = 15
            else:
                tap_out_mins = 30
                
            tap_out_time = start_time + timedelta(minutes = tap_out_mins)
            
            can_tap_out = current_time_dt >= tap_out_time
            
            # If the one who taps is a student
            if student_id:
                student_name = get_student_by_id(student_id)
                first_name, last_name = student_name
                full_name = f"{first_name} {last_name}"

                enrolled = check_enrollment(student_id, course_id)
                if enrolled:
                    attendance_exists = student_attendance_check(student_id, course_id, room_id, current_date)
                    if attendance_exists:
                        time_out_exists = check_student_time_out(student_id, course_id, room_id, current_date)
                        if time_out_exists:
                            print(f"Time-out already recorded for Student")
                            print(full_name)
                            print(f"Course: {course_details}")
                            
                            device.clear()
                            with canvas(device) as draw:
                                draw.text((1, 1), first_name, fill="white")
                                draw.text((1, 10), last_name, fill="white")
                                draw.text((1, 30), "Time-out already", fill="white")
                                draw.text((1, 40), "recorded", fill="white")
                                
                        elif can_tap_out:
                            record_student_time_out(student_id, course_id, room_id, current_date, current_time)
                        else:
                            print("Your attendance has already been recorded")
                            print(full_name)
                            print(f"Course: {course_details}")
                            
                            device.clear()
                            with canvas(device) as draw:
                                draw.text((1, 1), first_name, fill="white")
                                draw.text((1, 10), last_name, fill="white")
                                draw.text((1, 30), "Attendance already", fill="white")
                                draw.text((1, 40), "recorded", fill="white")
                    else:
                        record_student_attendance(student_id, course_id, room_id, start_time, current_date, current_time)
                else:
                    print(f"{full_name} is not enrolled in {course_details}")
                    record_room_log(student_id, None, room_id, current_date, current_time)
                    
            # If the one who taps is a teacher
            elif teacher_id:
                teacher_name = get_teacher_by_id(teacher_id)
                first_name, last_name = teacher_name
                full_name = f"{first_name} {last_name}"
                
                assigned = check_assignment(teacher_id, course_id)
                if assigned:
                    attendance_exists = teacher_attendance_check(teacher_id, course_id, room_id, current_date)
                    if attendance_exists:
                        time_out_exists = check_teacher_time_out(teacher_id, course_id, room_id, current_date)
                        if time_out_exists:
                            print(f"Time-out already recorded for Teacher")
                            print(full_name)
                            print(f"Course: {course_details}")
                            
                            device.clear()
                            with canvas(device) as draw:
                                draw.text((1, 1), first_name, fill="white")
                                draw.text((1, 10), last_name, fill="white")
                                draw.text((1, 30), "Time-out already", fill="white")
                                draw.text((1, 40), "recorded", fill="white")
                        elif can_tap_out:
                            record_teacher_time_out(teacher_id, course_id, room_id, current_date, current_time)							
                        else:
                            print("Your attendance has already been recorded")
                            print(full_name)
                            print(f"Course: {course_details}")
                            
                            device.clear()
                            with canvas(device) as draw:
                                draw.text((1, 1), first_name, fill="white")
                                draw.text((1, 10), last_name, fill="white")
                                draw.text((1, 30), "Attendance already", fill="white")
                                draw.text((1, 40), "recorded", fill="white")
                    else:
                        record_teacher_attendance(teacher_id, course_id, room_id, start_time, current_date, current_time)
                else:
                    print(f"{full_name} is not assigned in {course_details}")
                    record_room_log(None, teacher_id, room_id, current_date, current_time)
                    
            else:
                print("ID not registered.")
                device.clear()
                with canvas(device) as draw:
                    draw.text((1, 1), "Unregistered ID:", fill="white")
                    draw.text((1, 20), screen_uid, font = font, fill="white")
                    
                if check_internet():
                    sync_auth_user_remote_to_local()
                    sync_users_remote_to_local()
                    sync_students_remote_to_local()
                    sync_teachers_remote_to_local()
                    sync_admins_remote_to_local()
                    logger.info(f'Sync complete for au, u, s, t, and a')
                else:
                    logger.info(f'No internet, failed to sync au, u, s, t, and a')
				
        else:
            if student_id:
                record_room_log(student_id, None, room_id, current_date, current_time)
            elif teacher_id:
                record_room_log(None, teacher_id, room_id, current_date, current_time)
            else:
                print("ID not registered.")
                device.clear()
                with canvas(device) as draw:
                    draw.text((1, 1), "Unregistered ID:", fill="white")
                    draw.text((1, 20), screen_uid, font = font, fill="white")
                    
                if check_internet():
                    sync_auth_user_remote_to_local()
                    sync_users_remote_to_local()
                    sync_students_remote_to_local()
                    sync_teachers_remote_to_local()
                    sync_admins_remote_to_local()
                    logger.info(f'Sync complete for au, u, s, t, and a')
                else:
                    logger.info(f'No internet, failed to sync au, u, s, t, and a')
                
        if student_id:
            logger.info(f'NFC workflow success for student {student_id}')
        elif teacher_id:
            logger.info(f'NFC workflow success for teacher {teacher_id}')
        else:
            logger.info(f'NFC workflow success for unregistered user {nfc_uid}')
        
    except Exception as e:
        logger.error(f"Error in NFC card workflow: {e}")
        with canvas(device) as draw:
            draw.text((25, 20), "Restarting...", fill="white")
        time.sleep(5)
        os.system('sudo reboot')
       
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
            
# Lookup student ID based on the serial read
def get_student_by_uid(nfc_uid):
	db_connection = connect_local_db()
	cursor = db_connection.cursor()
	
	query = """
		SELECT student_id, first_name, last_name
		FROM students
		WHERE nfc_uid = %s
	"""
	
	cursor.execute(query, (nfc_uid,))
	student = cursor.fetchone()
	
	cursor.close()
	db_connection.close()
	
	if student:
		student_id = student[0]
		return student_id 
	else:
		return None

# Get student info based on ID Number		
def get_student_by_id(student_id):
	db_connection = connect_local_db()
	cursor = db_connection.cursor()
	
	query = """
		SELECT first_name, last_name
		FROM students
		WHERE student_id = %s
	"""
	
	cursor.execute(query, (student_id,))
	student = cursor.fetchone()
	
	cursor.close()
	db_connection.close()
	
	if student:
		first_name, last_name = student
		return first_name, last_name
	else:
		return None
		
# Lookup teacher ID based on the serial read
def get_teacher_by_uid(nfc_uid):
	db_connection = connect_local_db()
	cursor = db_connection.cursor()
	
	query = """
		SELECT teacher_id, first_name, last_name
		FROM teachers
		WHERE nfc_uid = %s
	"""
	
	cursor.execute(query, (nfc_uid,))
	teacher = cursor.fetchone()
	
	cursor.close()
	db_connection.close()
	
	if teacher:
		teacher_id = teacher[0]
		return teacher_id 
	else:
		return None

# Get teacher info based on ID Number
def get_teacher_by_id(teacher_id):
	db_connection = connect_local_db()
	cursor = db_connection.cursor()
	
	query = """
		SELECT first_name, last_name
		FROM teachers
		WHERE teacher_id = %s
	"""
	
	cursor.execute(query, (teacher_id,))
	teacher = cursor.fetchone()
	
	cursor.close()
	db_connection.close()
	
	if teacher:
		first_name, last_name = teacher
		return first_name, last_name
	else:
		return None
		
def get_room_id_by_room_name(room_name):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    query = """
        SELECT room_id
        FROM rooms
        WHERE room_name = %s
    """
    
    cursor.execute(query, (room_name,))
    room = cursor.fetchone()
    
    cursor.close()
    db_connection.close()
    
    if room:
        return room[0]  
    else:
        return None  
        
def get_course_name_by_id(course_id):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    query = """
        SELECT course_code, section
        FROM courses
        WHERE course_id = %s
    """
    
    cursor.execute(query, (course_id,))
    course = cursor.fetchone()
    
    cursor.close()
    db_connection.close()

    if course:
        course_code, section = course
        return course_code, section
    else:
        return None
        
def get_course_time_duration(course_id):
    try:
        db_connection = connect_local_db()
        cursor = db_connection.cursor()

        query = """
            SELECT start_time, end_time 
            FROM courses
            WHERE course_id = %s
        """
        cursor.execute(query, (course_id,))
        course_times = cursor.fetchone()
        
        start_time, end_time = course_times


        start_time = (datetime.min + start_time).time()
        end_time = (datetime.min + end_time).time()

        start_time_dt = datetime.combine(datetime.today(), start_time)
        end_time_dt = datetime.combine(datetime.today(), end_time)

        duration = end_time_dt - start_time_dt
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return start_time_dt, end_time_dt, hours, minutes
    
    except Exception as e:
        print(f"Error fetching course duration for ID {course_id}: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

# For checking the active class given current day and time
def check_active_class(room_id, room_name, current_day, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
   
    day_abbreviation = get_day_abbreviation(current_day)

    query = """
        SELECT course_id, course_code, course_title, section, schedule_day, start_time, end_time
        FROM courses
        WHERE schedule_day IN ({})
          AND room_id = %s
          AND courses.start_time <= %s AND courses.end_time >= %s

    """.format(', '.join(['%s'] * len(day_abbreviation)))

    params = tuple(day_abbreviation) + (room_id, current_time, current_time)

    cursor.execute(query, params)

    course_details = cursor.fetchone()

    # Check if there are results
    if course_details:
        course_id, course_code, course_title, section, schedule_day, start_time, end_time = course_details
        course_id = course_details[0]
            
        return course_id
    else:
        return None
		    
    # Close the connection
    cursor.close()
    db_connection.close()
    
# Check if student is enrolled in the active course
def check_enrollment(student_id, course_id):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    enrollment = None

    query = """
        SELECT id 
        FROM students_courses
        WHERE students_id = %s AND courses_id = %s
    """
        
    cursor.execute(query, (student_id, course_id))
    enrollment = cursor.fetchone()
    
    # Close the connection
    cursor.close()
    db_connection.close()
        
    return bool(enrollment)

# Check if teacher is asigned in the active course
def check_assignment(teacher_id, course_id):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    assignment = None

    query = """
        SELECT course_id 
        FROM courses
        WHERE teacher_id = %s AND course_id = %s
    """
        
    cursor.execute(query, (teacher_id, course_id))
    assignment = cursor.fetchone()
    
    # Close the connection
    cursor.close()
    db_connection.close()
        
    return bool(assignment)
            
def student_attendance_check(student_id, course_id, room_id, current_date):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    query = """
        SELECT 1 
        FROM student_attendance
        WHERE student_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
    """	
    cursor.execute(query, (student_id, course_id, room_id, current_date))
    attendance_exists = cursor.fetchone()
    
    if attendance_exists:
        return True
    else:    
        return False
    
    # Close the connection
    cursor.close()
    db_connection.close()

def record_student_attendance(student_id, course_id, room_id, start_time, current_date, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    student_name = get_student_by_id(student_id)
    course_info = get_course_name_by_id(course_id)
    
    first_name, last_name = student_name
    full_name = f"{first_name} {last_name}"

    course_code, section = course_info
    course_details = f"{course_code} {section}"
    
    current_time_dt = datetime.combine(datetime.today(), current_time)
    screen_time = current_time.strftime('%I:%M:%S %p')
    
    if current_time_dt <= start_time + timedelta(minutes = 5):
        status = "On Time"
    elif (current_time_dt >= start_time + timedelta(minutes = 5)) and current_time_dt <= start_time + timedelta(minutes = 15):
	    status = "Late"
    else:
	    status = "Absent"

    insert_student_attendance = """
        INSERT INTO student_attendance(day_date, time_in, course_id, room_id, student_id, status, is_synced)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_student_attendance, (current_date, current_time, course_id, room_id, student_id, status, False))
    db_connection.commit()
    logger.info(f'Attendance recorded locally for {full_name} in {course_details}')
    
    device.clear()
    with canvas(device) as draw:
        draw.text((1, 1), first_name, fill="white")
        draw.text((1, 10), last_name, fill="white")
        draw.text((1, 30), "Attendance recorded", fill="white")
        draw.text((1, 40), f"{course_code} {section}", fill="white")
        draw.text((1, 50), f"Time: {screen_time}", fill="white")
    time.sleep(1)
    # Send to cloud
    # ~ if check_internet():
        # ~ sync_student_attendance_local_to_remote()
        # ~ logger.info('Sent to cloud successfully')
        
        # ~ device.clear()
        # ~ with canvas(device) as draw:
            # ~ draw.text((25, 25), "Sent to cloud!", fill="white")
    # ~ else:
        # ~ logger.info('No internet, cannot send to remote DB at the moment')
        # ~ device.clear()
        # ~ with canvas(device) as draw:
            # ~ draw.text((30, 25), "No internet!", fill="white")

    # Close the connection
    cursor.close()
    db_connection.close()
    
def check_student_time_out(student_id, course_id, room_id, current_date):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()

    query = """
        SELECT time_out
        FROM student_attendance
        WHERE student_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
    """
    cursor.execute(query, (student_id, course_id, room_id, current_date))
    time_out_record = cursor.fetchone()
    
    cursor.close()
    db_connection.close()
        
    # Check if time_out is recorded
    if time_out_record and time_out_record[0] is not None:
        return True  
    else:
        return False 


def record_student_time_out(student_id, course_id, room_id, current_date, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    screen_time = current_time.strftime('%I:%M:%S %p')
    
    try:
        student_name = get_student_by_id(student_id)
        course_info = get_course_name_by_id(course_id)
    
        first_name, last_name = student_name
        full_name = f"{first_name} {last_name}"

        course_code, section = course_info
        course_details = f"{course_code} {section}"

        query = """
            UPDATE student_attendance
            SET time_out = %s, is_synced = %s
            WHERE student_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
        """
        cursor.execute(query, (current_time, False, student_id, course_id, room_id, current_date))
        db_connection.commit()
        logger.info(f'Time-out recorded locally for {full_name} in {course_details}')
        
        device.clear()
        with canvas(device) as draw:
            draw.text((1, 1), first_name, fill="white")
            draw.text((1, 10), last_name, fill="white")
            draw.text((1, 30), "Time-out recorded", fill="white")
            draw.text((1, 40), f"{course_code} {section}", fill="white")
            draw.text((1, 50), f"Time: {screen_time}", fill="white")
        time.sleep(1)
        # Send to cloud
        # ~ if check_internet():
            # ~ sync_student_attendance_local_to_remote()
            # ~ logger.info('Sent to cloud successfully')
            
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((25, 25), "Sent to cloud!", fill="white")
        # ~ else:
            # ~ logger.info('No internet, cannot send to remote DB at the moment')
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((30, 25), "No internet!", fill="white")

    except Exception as e:
        print(f"Error updating timeout: {e}")
    
    finally:
        # Close the connection
        cursor.close()
        db_connection.close()
        
def teacher_attendance_check(teacher_id, course_id, room_id, current_date):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    query = """
        SELECT 1
        FROM teacher_attendance
        WHERE teacher_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
    """	
    cursor.execute(query, (teacher_id, course_id, room_id, current_date))
    attendance_exists = cursor.fetchone()
    
    if attendance_exists:
        return True
    else:    
        return False
    
    # Close the connection
    cursor.close()
    db_connection.close()
    
def record_teacher_attendance(teacher_id, course_id, room_id, start_time, current_date, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    teacher_name = get_teacher_by_id(teacher_id)
    course_info = get_course_name_by_id(course_id)
    
    first_name, last_name = teacher_name
    full_name = f"{first_name} {last_name}"
    
    course_code, section = course_info
    course_details = f"{course_code} {section}"
    
    current_time_dt = datetime.combine(datetime.today(), current_time)
    screen_time = current_time.strftime('%I:%M:%S %p')
    
    if current_time_dt <= start_time + timedelta(minutes = 5):
        status = "On Time"
    else:
	    status = "Late"

    insert_teacher_attendance = """
        INSERT INTO teacher_attendance(day_date, time_in, course_id, room_id, teacher_id, status, is_synced)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(insert_teacher_attendance, (current_date, current_time, course_id, room_id, teacher_id, status, False))
    db_connection.commit()
    logger.info(f'Attendance recorded locally for {full_name} in {course_details}')
    
    device.clear()
    with canvas(device) as draw:
        draw.text((1, 1), first_name, fill="white")
        draw.text((1, 10), last_name, fill="white")
        draw.text((1, 30), "Attendance recorded", fill="white")
        draw.text((1, 40), f"{course_code} {section}", fill="white")
        draw.text((1, 50), f"Time: {screen_time}", fill="white")
    time.sleep(1)
    # Send to cloud
    # ~ if check_internet():
        # ~ sync_teacher_attendance_local_to_remote()
        # ~ logger.info('Sent to cloud successfully')
        
        # ~ device.clear()
        # ~ with canvas(device) as draw:
            # ~ draw.text((25, 25), "Sent to cloud!", fill="white")
    # ~ else:
        # ~ logger.info('No internet, cannot send to remote DB at the moment')
        # ~ device.clear()
        # ~ with canvas(device) as draw:
            # ~ draw.text((30, 25), "No internet!", fill="white")

    # Close the connection
    cursor.close()
    db_connection.close()
    
def check_teacher_time_out(teacher_id, course_id, room_id, current_date):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    
    query = """
        SELECT time_out
        FROM teacher_attendance
            WHERE teacher_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
    """
    cursor.execute(query, (teacher_id, course_id, room_id, current_date))
    time_out_record = cursor.fetchone()
    
    cursor.close()
    db_connection.close()
        
    # Check if time_out is recorded
    if time_out_record and time_out_record[0] is not None:
        return True  
    else:
        return False 
        
def record_teacher_time_out(teacher_id, course_id, room_id, current_date, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    screen_time = current_time.strftime('%I:%M:%S %p')
    
    try:
        teacher_name = get_teacher_by_id(teacher_id)
        course_info = get_course_name_by_id(course_id)
    
        first_name, last_name = teacher_name
        full_name = f"{first_name} {last_name}"

        course_code, section = course_info
        course_details = f"{course_code} {section}"

        query = """
            UPDATE teacher_attendance
            SET time_out = %s, is_synced = %s
            WHERE teacher_id = %s AND course_id = %s AND room_id = %s AND day_date = %s
        """
        cursor.execute(query, (current_time, False, teacher_id, course_id, room_id, current_date))
        db_connection.commit()
        logger.info(f'Time-out recorded locally for {full_name} in {course_details}')
        
        device.clear()
        with canvas(device) as draw:
            draw.text((1, 1), first_name, fill="white")
            draw.text((1, 10), last_name, fill="white")
            draw.text((1, 30), "Time-out recorded", fill="white")
            draw.text((1, 40), f"{course_code} {section}", fill="white")
            draw.text((1, 50), f"Time: {screen_time}", fill="white")
        time.sleep(1)
        # Send to cloud
        # ~ if check_internet():
            # ~ sync_teacher_attendance_local_to_remote() 
            # ~ logger.info('Sent to cloud successfully') 
            
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((25, 25), "Sent to cloud!", fill="white")
        # ~ else:
            # ~ logger.info('No internet, cannot send to remote DB at the moment') 
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((30, 25), "No internet!", fill="white")

    except Exception as e:
        print(f"Error updating timeout: {e}")
    
    finally:
        # Close the connection
        cursor.close()
        db_connection.close()
    
def record_room_log(student_id, teacher_id, room_id, current_date, current_time):
    db_connection = connect_local_db()
    cursor = db_connection.cursor()
    screen_time = current_time.strftime('%I:%M:%S %p')
    
    try:
        
        if student_id is not None:
            student_name = get_student_by_id(student_id)
            first_name, last_name = student_name
            full_name = f"{first_name} {last_name}"
        else:
            teacher_name = get_teacher_by_id(teacher_id)
            first_name, last_name = teacher_name
            full_name = f"{first_name} {last_name}"
        
        # Check if log already exists
        record_check = """
            SELECT status
            FROM room_logs
            WHERE day_date = %s 
            AND room_id = %s 
            AND (student_id = %s OR teacher_id = %s)
            ORDER BY time_log DESC LIMIT 1
        """
        cursor.execute(record_check, (current_date, room_id, student_id, teacher_id))
        status_exists = cursor.fetchone()
        
        if status_exists:
            last_status = status_exists[0]
            new_status = "OUT" if last_status == "IN" else "IN"
        else:
            new_status = "IN"
            
        insert_log = """
            INSERT INTO room_logs (day_date, time_log, room_id, student_id, teacher_id, status, is_synced)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_log, (current_date, current_time, room_id, student_id, teacher_id, new_status, False))
        db_connection.commit()
        logger.info(f'Log recorded locally for {full_name} with status: {new_status}')
        device.clear()
        with canvas(device) as draw:
            draw.text((1, 1), first_name, fill="white")
            draw.text((1, 10), last_name, fill="white")
            draw.text((1, 30), "Recording room log only", fill="white")
            draw.text((1, 50), f"Status: {new_status}", fill="white")
        time.sleep(1)
        # Send to cloud
        # ~ if check_internet():
            # ~ sync_room_logs_local_to_remote()  
            # ~ logger.info('Sent to cloud successfully!')
            
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((25, 25), "Sent to cloud!", fill="white")
        # ~ else:
            # ~ logger.info('No internet, cannot send to remote DB at the moment')
            # ~ device.clear()
            # ~ with canvas(device) as draw:
                # ~ draw.text((30, 25), "No internet!", fill="white")
            
    except Exception as e:
        print(f"Error recording room log: {e}")
    
    finally:
        cursor.close()
        db_connection.close()
        
def nfc_listener(room_id, room_name):
    try:
        while True:
            print("")
            print("Waiting for an ID...")
            device.clear()
            with canvas(device) as draw:
                draw.text((15, 20), "Waiting for an ID...", fill="white")
            nfc_uid = read_nfc_card()
            if nfc_uid:
                beep(2000, 0.2)
                # active_beep(0.2)
                logger.info(f'A user tapped with NFC UID: {nfc_uid}')
                if is_user_blocked(nfc_uid):
                    logger.info(f'Blocked user tapped with NFC UID: {nfc_uid}')
                    device.clear()
                    with canvas(device) as draw:
                        draw.text((15, 20), "User is blocked.", fill="white")
                        draw.text((15, 30), "Please wait.", fill="white")
                    time.sleep(2)
                else:
                    if record_tap(nfc_uid):
                        continue # Skip the workflow if the user just got blocked
                    nfc_card_workflow(nfc_uid, room_id, room_name)
            else:
                print("No card detected.")
            time.sleep(1)
    
    # except Exception as e:
        # os.system('sudo reboot')
    
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        
def periodic_sync(sync_interval):
    while True:
        try:
            if check_internet():
                sync_auth_user_remote_to_local()
                sync_users_remote_to_local()
                sync_students_remote_to_local()
                sync_teachers_remote_to_local()
                sync_admins_remote_to_local()
                sync_rooms_remote_to_local()
                sync_courses_remote_to_local()
                sync_students_courses_remote_to_local()
                sync_manual_attendance_remote_to_local()
                sync_student_attendance_local_to_remote()
                sync_teacher_attendance_local_to_remote()
                sync_room_logs_local_to_remote()
                logger.info("Periodic syncing complete")
            else:
                logger.info("Periodic syncing failed. No Internet")
            
            logger.info("Attempt for periodic syncing complete")
            print("")
            print("Waiting for an ID...")
        except Exception as e:
            logger.error(f"Attempt for periodic syncing failed: {e}")
            with canvas(device) as draw:
                draw.text((25, 20), "Restarting...", fill="white")
            os.system('sudo reboot')
        
        time.sleep(sync_interval)
        
# ~ def wait_for_internet_and_sync():
    # ~ try:
        # ~ time.sleep(15)
        # ~ internet_was_down = True
        
        # ~ while True:
            # ~ if check_internet():
                # ~ if internet_was_down:
                    # ~ time.sleep(5)
                    # ~ logger.info("Internet is now available!")
                    # ~ sync_manual_attendance_remote_to_local()
                    # ~ sync_student_attendance_local_to_remote()
                    # ~ sync_teacher_attendance_local_to_remote()
                    # ~ sync_room_logs_local_to_remote()
                    # ~ internet_was_down = False
            # ~ else:
                # ~ internet_was_down = True
            # ~ time.sleep(60)
    # ~ except Exception as e:
        # ~ logger.error("Encountered an error, rebooting!")
        # ~ with canvas(device) as draw:
            # ~ draw.text((25, 20), "Restarting...", fill="white")
        # ~ time.sleep(5)
        # ~ os.system('sudo reboot')
        
tap_counts = defaultdict(list)
blocked_users = {}

def is_user_blocked(nfc_uid):
    """Check if a user is currently blocked."""
    if nfc_uid in blocked_users:
        if time.time() < blocked_users[nfc_uid]:
            return True
        else:
            # Unblock after timeout expires
            del blocked_users[nfc_uid]
    return False
    
def record_tap(nfc_uid, max_taps=4, interval=20, block_duration=60):
    """Record NFC taps and block user if they exceed the limit."""
    current_time = time.time()

    # Clean up old taps
    tap_counts[nfc_uid] = [t for t in tap_counts[nfc_uid] if current_time - t <= interval]
    tap_counts[nfc_uid].append(current_time)

    # Check if user exceeded allowed taps
    if len(tap_counts[nfc_uid]) > max_taps:
        blocked_users[nfc_uid] = current_time + block_duration
        print(f"User blocked for {block_duration} seconds!")
        logger.info(f"Blocked user with UID {nfc_uid}")
        device.clear()
        with canvas(device) as draw:
            draw.text((15, 20), "User blocked for:", fill="white")
            draw.text((15, 30), f"{block_duration} seconds", fill="white")
        time.sleep(2)
        return True
    return False

# Main function
def main():
    current_date, current_day, current_time = get_current_date_day_time()
    
    # Get the room id
    room_name = "D318"
    room_id = get_room_id_by_room_name(room_name)
    sync_interval = 900
    
    # Thread for waiting for IDs
    nfc_thread = threading.Thread(target=nfc_listener, args=(room_id, room_name))
    
    # Thread for syncing local DB and remote DB
    sync_thread = threading.Thread(target=periodic_sync, args=(sync_interval,))
    
    # Thread when no internet then it comes back
    # internet_is_back_thread = threading.Thread(target=wait_for_internet_and_sync)
    
    if check_internet():
        logger.info(f'Connected to internet!')
        device.clear()
        with canvas(device) as draw:
            draw.text((5, 20), "Connected to internet!", fill="white")
    else:
        logger.info(f'No internet!')
        device.clear()
        with canvas(device) as draw:
            draw.text((30, 25), "No internet!", fill="white")
            
    time.sleep(2)
    nfc_thread.start()
    sync_thread.start()
    # internet_is_back_thread.start()
    
    nfc_thread.join()
    sync_thread.join()
    # internet_is_back_thread.join()

# Run the main function
if __name__ == "__main__":
    main()
