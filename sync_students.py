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


def sync_students_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM students")
        local_cursor.execute("SELECT * FROM students")
        
        remote_students = {student[0]: student for student in remote_cursor.fetchall()}
        local_students = {student[0]: student for student in local_cursor.fetchall()}
        
        new_students = [student for student_id, student in remote_students.items() if student_id not in local_students]
        updated_students = [student for student_id, student in remote_students.items() if student_id in local_students and student != local_students[student_id]]
        deleted_students = [(student_id,) for student_id in local_students if student_id not in remote_students]
        
        if new_students or updated_students:
            insert_query = """
                INSERT INTO students (student_id, first_name, last_name, nfc_uid, user_id, au_user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
                    nfc_uid = VALUES(nfc_uid),
                    user_id = VALUES(user_id),
		    au_user_id = VALUES(au_user_id)
            """
            local_cursor.executemany(insert_query, new_students + updated_students)
            
        if deleted_students:
            delete_query = """
                DELETE FROM students
                WHERE student_id = %s
            """
            local_cursor.executemany(delete_query, deleted_students)
		    
        if new_students or updated_students or deleted_students:
            local_db.commit()
            logger.info(f"{len(new_students)} new students, {len(updated_students)} updated students, and {len(deleted_students)} deleted students synced to local DB.")
        else:
            logger.info("Students Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing students from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_students_remote_to_local()
    print("students sync completed!")
        





