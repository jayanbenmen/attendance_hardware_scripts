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


def sync_teachers_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM teachers")
        local_cursor.execute("SELECT * FROM teachers")
        
        remote_teachers = {teacher[0]: teacher for teacher in remote_cursor.fetchall()}
        local_teachers = {teacher[0]: teacher for teacher in local_cursor.fetchall()}
        
        new_teachers = [teacher for teacher_id, teacher in remote_teachers.items() if teacher_id not in local_teachers]
        updated_teachers = [teacher for teacher_id, teacher in remote_teachers.items() if teacher_id in local_teachers and teacher != local_teachers[teacher_id]]
        deleted_teachers = [(teacher_id,) for teacher_id in local_teachers if teacher_id not in remote_teachers]
        
        if new_teachers or updated_teachers:
            insert_query = """
                INSERT INTO teachers (teacher_id, first_name, last_name, nfc_uid, user_id, au_user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
                    nfc_uid = VALUES(nfc_uid),
                    user_id = VALUES(user_id),
		    au_user_id = VALUES(au_user_id)
            """
            local_cursor.executemany(insert_query, new_teachers + updated_teachers)
            
        if deleted_teachers:
            delete_query = """
                DELETE FROM teachers
                WHERE teacher_id = %s
            """
            local_cursor.executemany(delete_query, deleted_teachers)
		    
        if new_teachers or updated_teachers or deleted_teachers:
            local_db.commit()
            logger.info(f"{len(new_teachers)} new teachers, {len(updated_teachers)} updated teachers, and {len(deleted_teachers)} deleted teachers synced to local DB.")
        else:
            logger.info("Teachers Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing teachers from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_teachers_remote_to_local()
    print("teachers sync completed!")
        






