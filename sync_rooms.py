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


def sync_rooms_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM rooms")
        local_cursor.execute("SELECT * FROM rooms")
        
        remote_rooms = {room[0]: room for room in remote_cursor.fetchall()}
        local_rooms = {room[0]: room for room in local_cursor.fetchall()}
        
        new_rooms = [room for room_id, room in remote_rooms.items() if room_id not in local_rooms]
        updated_rooms = [room for room_id, room in remote_rooms.items() if room_id in local_rooms and room != local_rooms[room_id]]
        deleted_rooms = [(room_id,) for room_id in local_rooms if room_id not in remote_rooms]
        
        if new_rooms or updated_rooms:
            insert_query = """
                INSERT INTO rooms (room_id, room_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE 
                    room_name = VALUES(room_name)
            """
            local_cursor.executemany(insert_query, new_rooms + updated_rooms)
            
        if deleted_rooms:
            delete_query = """
                DELETE FROM rooms
                WHERE room_id = %s
            """
            local_cursor.executemany(delete_query, deleted_rooms)
		    
        if new_rooms or updated_rooms or deleted_rooms:
            local_db.commit()
            logger.info(f"{len(new_rooms)} new rooms, {len(updated_rooms)} updated rooms, and {len(deleted_rooms)} deleted rooms synced to local DB.")
        else:
            logger.info("Rooms Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing rooms from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_rooms_remote_to_local()
    print("rooms sync completed!")
        







