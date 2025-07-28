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

def sync_room_logs_local_to_remote():
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
        
        local_cursor.execute("SELECT day_date, time_log, status, room_id, student_id, teacher_id FROM room_logs WHERE is_synced = False")
        new_local_room_log = local_cursor.fetchall()

        
        if new_local_room_log:
            insert_query = """
                INSERT INTO room_logs (day_date, time_log, status, room_id, student_id, teacher_id, is_synced)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            new_room_log_data = [(room_log[0], room_log[1], room_log[2], room_log[3], room_log[4], room_log[5], True) for room_log in new_local_room_log]
            
            remote_cursor.executemany(insert_query, new_room_log_data)
            remote_db.commit()
            logger.info(f"{len(new_local_room_log)} new room logs synced to remote DB.")
            
            update_query = "UPDATE room_logs SET is_synced = True WHERE is_synced = False"
            local_cursor.execute(update_query)
            local_db.commit()
        else:
            logger.info("Room Logs Remote database is already up-to-date with local.")
        
    except Exception as e:
        logger.error(f"Error syncing room logs from local to remote: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_room_logs_local_to_remote()
    print("room logs sync completed!")
        











