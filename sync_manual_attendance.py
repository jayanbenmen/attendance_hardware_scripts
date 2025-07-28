import mariadb
import mysql.connector
import logging

# Setup Logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('/home/rpi2/Thesis/py532lib/rpi2.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def sync_manual_attendance_remote_to_local():
    try:
        remote_db = mysql.connector.connect(
            host="",            # Insert public IP of the cloud database server here       
            user="",            # Insert user of the cloud database
            password="",        # Insert password
            database=""         # Insert name of the database
	    )
        local_db = mariadb.connect(
            host="localhost",          
            user="root",               
            password="",        # Insert password of the root user of the local database
            database=""         # Insert database name of local database
	    )
	    
        remote_cursor = remote_db.cursor()
        local_cursor = local_db.cursor()
        
        remote_cursor.execute("SELECT day_date, time_in, time_out, status, course_id, room_id, student_id, is_synced FROM manual_attendance WHERE room_id = 3")
        local_cursor.execute("SELECT day_date, time_in, time_out, status, course_id, room_id, student_id, is_synced FROM student_attendance")
        
        remote_manual_attendance = {(attendance[0], attendance[4], attendance[6]): attendance for attendance in remote_cursor.fetchall()}
        local_student_attendance = {(attendance[0], attendance[4], attendance[6]): attendance for attendance in local_cursor.fetchall()}
        
        new_manual_attendance = [attendance for key, attendance in remote_manual_attendance.items() if key not in local_student_attendance]
        if new_manual_attendance:
            insert_query = """
		        INSERT INTO student_attendance (day_date, time_in, time_out, status, course_id, room_id, student_id, is_synced)
		        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
		        ON DUPLICATE KEY UPDATE
		            is_synced = is_synced
		    """
            local_cursor.executemany(insert_query, new_manual_attendance)
            local_db.commit()
            logger.info(f"{len(new_manual_attendance)} new manual student attendance records synced to local DB.")
        else:
            logger.info("Student Attendance Local database is already up-to-date with remote Manual Attendance.")
    except Exception as e:
        logger.error(f"Error syncing manual attendance from remote to local: {e}")
        
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_manual_attendance_remote_to_local()
    print("manual attendance sync completed!")
