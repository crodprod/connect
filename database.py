from mysql.connector import connect
from platform import system
from dotenv import load_dotenv
from logging import basicConfig, info, error
import redis

if system() == "Windows":
    env_path = r"D:\CROD_MEDIA\.env"
else:
    env_path = r"/root/crod/.env"
load_dotenv(dotenv_path=env_path)


class MySQL:
    def __init__(self, host, port, user, password, db_name):
        info(f'MySQL: Initialization ({host}, {port}, {user}, {password}, {db_name})')
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.connection = None
        self.cur = None
        self.data = None
        self.result = None
        info(f'MySQL: Initialization completed!')

    def connect(self):
        info(f'MySQL: Connecting to database')
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
            info(f'MySQL: Connected to database successfully!')
        except Exception as e:
            self.result = {"status": "error", "message": f"Error connecting to {self.db_name}@{self.host}: {e}"}
            error(f'MySQL: Not connected to database: {e}')

    def execute(self, query: str, params: tuple = ()):
        info(f'MySQL: Executing {query} with params {params}')
        try:
            self.cur.execute(
                operation=query,
                params=params
            )

            self.data = self.cur.fetchall()

            if len(self.data) == 1:
                self.data = self.data[-1]

            self.result = {"status": "ok", "message": f"Successfully executed {query} ({params})"}
            info(f'MySQL: Executed successfully!')
        except Exception as e:
            self.result = {"status": "error", "message": f"Error executing query: {e}"}
            error(f'MySQL: Not executed: {e}')

    def reconnect(self):
        info(f'MySQL: Reconnecting to database')
        self.connection.reconnect()

    def disconnect(self):
        self.connection.disconnect()
        info(f'MySQL: Connection closed')


class RedisTable:
    def __init__(self, host, port, password):
        info(f'Redis: Initialization ({host}, {port}, {password})')
        self.host = host
        self.port = port
        self.password = password
        self.connection = None
        self.data = None
        self.result = None

    def connect(self):
        info(f'Redis: Connecting to database')
        try:
            self.connection = redis.StrictRedis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True
            )
            self.connection.exists("0")
            self.result = {"status": "ok", "message": f"Successfully connected to redis@{self.host}"}
            info(f'Redis: Connected to database successfully!')

        except Exception as e:
            self.result = {"status": "error", "message": str(e)}
            error(f'Redis: Not connected to database: {e}')

    def exists(self, index):
        info(f'Redis: checking for {index} exist')
        if self.connection.exists(index):
            return True
        return False

    def get(self, index):
        info(f'Redis: Getting {index}')
        return self.connection.get(index)

    def set(self, sign, index):
        info(f'Redis: Setting {sign} with index {index}')
        self.connection.set(index, sign)

    def delete(self, index):
        info(f'Redis: Deleting {index}')
        self.connection.delete(index)
