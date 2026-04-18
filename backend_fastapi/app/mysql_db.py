import time

import pymysql
import pymysql.cursors

from app.config import settings


def get_mysql_connection() -> pymysql.Connection:
    """Return a connected PyMySQL connection, retrying up to 5 times."""
    retries = 5
    while retries > 0:
        try:
            connection = pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                connect_timeout=5,
                cursorclass=pymysql.cursors.DictCursor,
            )
            return connection
        except pymysql.MySQLError:
            retries -= 1
            if retries == 0:
                raise
            time.sleep(3)
    raise ConnectionError("Could not connect to the MySQL database.")
