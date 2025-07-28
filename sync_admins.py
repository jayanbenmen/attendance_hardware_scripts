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


def sync_admins_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM admins")
        local_cursor.execute("SELECT * FROM admins")
        
        remote_admins = {admin[0]: admin for admin in remote_cursor.fetchall()}
        local_admins = {admin[0]: admin for admin in local_cursor.fetchall()}
        
        new_admins = [admin for admin_id, admin in remote_admins.items() if admin_id not in local_admins]
        updated_admins = [admin for admin_id, admin in remote_admins.items() if admin_id in local_admins and admin != local_admins[admin_id]]
        deleted_admins = [(admin_id,) for admin_id in local_admins if admin_id not in remote_admins]
        
        if new_admins or updated_admins:
            insert_query = """
                INSERT INTO admins (admin_id, username, first_name, last_name, user_id, au_user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
                    user_id = VALUES(user_id),
		    au_user_id = VALUES(au_user_id)
            """
            local_cursor.executemany(insert_query, new_admins + updated_admins)
            
        if deleted_admins:
            delete_query = """
                DELETE FROM admins
                WHERE admin_id = %s
            """
            local_cursor.executemany(delete_query, deleted_admins)
		    
        if new_admins or updated_admins or deleted_admins:
            local_db.commit()
            logger.info(f"{len(new_admins)} new admins, {len(updated_admins)} updated admins, and {len(deleted_admins)} deleted admins synced to local DB.")
        else:
            logger.info("Admins Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing admins from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_admins_remote_to_local()
    print("admins sync completed!")
        







