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


def sync_courses_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM courses")
        local_cursor.execute("SELECT * FROM courses")
        
        remote_courses = {course[0]: course for course in remote_cursor.fetchall()}
        local_courses = {course[0]: course for course in local_cursor.fetchall()}
        
        new_courses = [course for course_id, course in remote_courses.items() if course_id not in local_courses]
        updated_courses = [course for course_id, course in remote_courses.items() if course_id in local_courses and course != local_courses[course_id]]
        deleted_courses = [(course_id,) for course_id in local_courses if course_id not in remote_courses]
        
        if new_courses or updated_courses:
            insert_query = """
                INSERT INTO courses (course_id, course_code, course_title, section, start_time, end_time, schedule_day, room_id, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    course_code = VALUES(course_code),
                    course_title = VALUES(course_title),
                    section = VALUES(section),
                    start_time = VALUES(start_time),
                    end_time = VALUES(end_time),
                    schedule_day = VALUES(schedule_day),
                    room_id = VALUES(room_id),
                    teacher_id = VALUES(teacher_id)
            """
            local_cursor.executemany(insert_query, new_courses + updated_courses)
            
        if deleted_courses:
            delete_query = """
                DELETE FROM courses
                WHERE course_id = %s
            """
            local_cursor.executemany(delete_query, deleted_courses)
		    
        if new_courses or updated_courses or deleted_courses:
            local_db.commit()
            logger.info(f"{len(new_courses)} new courses, {len(updated_courses)} updated courses, and {len(deleted_courses)} deleted courses synced to local DB.")
        else:
            logger.info("Courses Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing courses from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_courses_remote_to_local()
    print("Course sync completed!")
        


