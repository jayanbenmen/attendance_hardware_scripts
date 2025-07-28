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


def sync_students_courses_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM students_courses")
        local_cursor.execute("SELECT * FROM students_courses")
        
        remote_enrollments = {(enrollment[1], enrollment[2]): enrollment for enrollment in remote_cursor.fetchall()}
        local_enrollments = {(enrollment[1], enrollment[2]): enrollment for enrollment in local_cursor.fetchall()}
        
        new_enrollments = [enrollment for key, enrollment in remote_enrollments.items() if key not in local_enrollments]
        deleted_enrollments = [(students_id, courses_id) for students_id, courses_id in local_enrollments if (students_id, courses_id) not in remote_enrollments]
        
        if new_enrollments:
            insert_query = """
                INSERT INTO students_courses (id, students_id, courses_id)
                VALUES (%s, %s, %s)
            """
            local_cursor.executemany(insert_query, [(e[0], e[1], e[2]) for e in new_enrollments])
            
        if deleted_enrollments:
            delete_query = """
                DELETE FROM students_courses
                WHERE students_id = %s 
                AND courses_id = %s
            """
            local_cursor.executemany(delete_query, deleted_enrollments)
		    
        if new_enrollments or deleted_enrollments:
            local_db.commit()
            logger.info(f"{len(new_enrollments)} new enrollments, and {len(deleted_enrollments)} deleted enrollments synced to local DB.")
        else:
            logger.info("Enrollments Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing enrollments from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_students_courses_remote_to_local()
    print("enrollments sync completed!")
        








