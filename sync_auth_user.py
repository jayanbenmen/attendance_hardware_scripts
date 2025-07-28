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


def sync_auth_user_remote_to_local():
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
        
        remote_cursor.execute("SELECT * FROM auth_user")
        local_cursor.execute("SELECT * FROM auth_user")
        
        remote_auth_user = {auth_user[0]: auth_user for auth_user in remote_cursor.fetchall()}
        local_auth_user = {auth_user[0]: auth_user for auth_user in local_cursor.fetchall()}
        
        new_auth_user = [auth_user for id, auth_user in remote_auth_user.items() if id not in local_auth_user]
        updated_auth_user = [auth_user for id, auth_user in remote_auth_user.items() if id in local_auth_user and auth_user != local_auth_user[id]]
        deleted_auth_user = [(id,) for id in local_auth_user if id not in remote_auth_user]
        
        if new_auth_user or updated_auth_user:
            insert_query = """
                INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    password = VALUES(password),
                    last_login = VALUES(last_login),
                    is_superuser = VALUES(is_superuser),
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
                    email = VALUES(email),
                    is_staff = VALUES(is_staff),
                    is_active = VALUES(is_active),
                    date_joined = VALUES(date_joined)
            """
            local_cursor.executemany(insert_query, new_auth_user + updated_auth_user)
            
        if deleted_auth_user:
            delete_query = """
                DELETE FROM auth_user
                WHERE id = %s
            """
            local_cursor.executemany(delete_query, deleted_auth_user)
		    
        if new_auth_user or updated_auth_user or deleted_auth_user:
            local_db.commit()
            logger.info(f"{len(new_auth_user)} new auth users, {len(updated_auth_user)} updated auth users, and {len(deleted_auth_user)} deleted auth users synced to local DB.")
        else:
            logger.info("Auth User Local database is already up-to-date with remote.")
        
    except Exception as e:
        logger.error(f"Error syncing auth_user from remote to local: {e}")
    
    finally:
        remote_cursor.close()
        local_cursor.close()
        remote_db.close()
        local_db.close()
        
if __name__ == "__main__":
    sync_auth_user_remote_to_local()
    print("auth_user sync completed!")
        



