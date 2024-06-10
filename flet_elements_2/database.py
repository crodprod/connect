from mysql.connector import connect
from platform import system
from dotenv import load_dotenv
import redis

if system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)


class MySQL:
    def __init__(self, host, port, user, password, db_name):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.connection = None
        self.cur = None
        self.data = None
        self.result = None

    def connect(self):
        try:
            self.connection = connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.db_name,
                port=self.port
            )
            self.cur = self.connection.cursor(dictionary=True)
            self.connection.autocommit = True
            self.result = {"status": "ok", "message": f"Successfully connected to {self.db_name}@{self.host}"}

        except Exception as e:
            self.result = {"status": "error", "message": f"Error connecting to {self.db_name}@{self.host}: {e}"}

    def execute(self, query: str, params: tuple = ()):
        try:
            self.cur.execute(
                operation=query,
                params=params
            )

            self.data = self.cur.fetchall()

            if len(self.data) == 1:
                self.data = self.data[-1]

            self.result = {"status": "ok", "message": f"Successfully executed {query} ({params})"}
        except Exception as e:
            self.result = {"status": "error", "message": f"Error executing query: {e}"}

    def reconnect(self):
        self.connection.reconnect()


class RedisTable:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.connection = None
        self.data = None
        self.result = None

    def connect(self):
        try:
            self.connection = redis.StrictRedis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True
            )
            self.connection.exists("0")
            self.result = {"status": "ok", "message": f"Successfully connected to redis@{self.host}"}

        except Exception as e:
            self.result = {"status": "error", "message": str(e)}

    def exists(self, index):
        if self.connection.exists(index):
            return True
        return False

    def get(self, index):
        return self.connection.get(index)
