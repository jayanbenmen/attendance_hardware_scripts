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

def sync_student_attendance_local_to_remote():
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

        local_cursor.execute("SELECT day_date, time_in, time_out, course_id, room_id, student_id, status FROM student_attendance WHERE is_synced = False")
        new_local_s_attendance = local_cursor.fetchall()

        if new_local_s_attendance:
            insert_query = """
                INSERT INTO student_attendance (day_date, time_in, time_out, course_id, room_id, student_id, status, is_synced)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
		    time_in = VALUES(time_in),
                    time_out = VALUES(time_out),
		    status = VALUES(status)
            """
            new_s_attendance_data = [(attendance[0], attendance[1], attendance[2], attendance[3], attendance[4], attendance[5], attendance[6], True) for attendance in new_local_s_attendance]
            
            remote_cursor.executemany(insert_query, new_s_attendance_data)
            remote_db.commit()  

            logger.info(f"{len(new_local_s_attendance)} new student attendance records synced to remote DB.")

            update_query = "UPDATE student_attendance SET is_synced = True WHERE is_synced = False"
            local_cursor.execute(update_query)
            local_db.commit()  
        else:
            logger.info("Student Attendance Remote database is already up-to-date with local.")

    except mysql.connector.Error as e:
        logger.error(f"Error syncing student attendance from local to remote (MySQL): {e}")
    except mariadb.Error as e:
        logger.error(f"Error syncing student attendance from local to remote (MariaDB): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        try:
            remote_cursor.close()
            local_cursor.close()
            remote_db.close()
            local_db.close()
        except:
            pass  

if __name__ == "__main__":
    sync_student_attendance_local_to_remote()
    print("Student attendance sync completed!")
