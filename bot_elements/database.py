import mysql.connector
import logging

logging.basicConfig(level=logging.INFO)


class DataBase:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            # print("Connected to MySQL database")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            self.connection = None

    def disconnect(self):
        if self.connection:
            self.connection.close()
            # print("Disconnected from MySQL database")

    def execute_query(self, query: str, params: tuple = (), many: bool = False):
        if not self.connection:
            print("Not connected to MySQL database")
            return -1

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)

            if many:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()

            self.connection.commit()
            cursor.close()
            return result

        except mysql.connector.Error as err:
            print(f"Error executing query: {err}")
            return -1
