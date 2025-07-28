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


def sync_users_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM users")
        local_cursor.execute("SELECT * FROM users")
        
        remote_users = {user[0]: user for user in remote_cursor.fetchall()}
        local_users = {user[0]: user for user in local_cursor.fetchall()}
        
        new_users = [user for user_id, user in remote_users.items() if user_id not in local_users]
        updated_users = [user for user_id, user in remote_users.items() if user_id in local_users and user != local_users[user_id]]
        deleted_users = [(user_id,) for user_id in local_users if user_id not in remote_users]
        
        if new_users or updated_users:
            insert_query = """
                INSERT INTO users (user_id, email, pw, user_type, au_user_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    email = VALUES(email),
                    pw = VALUES(pw),
                    user_type = VALUES(user_type),
                    au_user_id = VALUES(au_user_id)
            """
            local_cursor.executemany(insert_query, new_users + updated_users)
            
        if deleted_users:
            delete_query = """
                DELETE FROM users
                WHERE user_id = %s
            """
            local_cursor.executemany(delete_query, deleted_users)
		    
        if new_users or updated_users or deleted_users:
            local_db.commit()
            logger.info(f"{len(new_users)} new users, {len(updated_users)} updated users, and {len(deleted_users)} deleted users synced to local DB.")
        else:
            logger.info("Users Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing auth_user from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_users_remote_to_local()
    print("users sync completed!")
        




