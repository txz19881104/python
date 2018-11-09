#引入文件
import json
import pymysql
import threading

from DBUtils.PooledDB import PooledDB
from DBUtils.PersistentDB import PersistentDB
global gHandleDatabase 
#lock = threading.Lock()
#lock.acquire()
#lock.release()
class SaveToDatabase(object):
    def __init__(self, host, user, passwd, db, port, charset):
        self.host    = host        # ip地址
        self.user    = user        # 用户名
        self.passwd  = passwd      # 密码
        self.db      = db          # 数据库
        #self.table   = table       # 表名
        self.port    = port        # 端口号
        self.charset = charset     # 字符集
        self.connect = None        # 数据库连接
        self.cursor  = None        # 数据库光标
        self.pool    = None        # 连接池


    def CreateDBPool(self):
        # 打开数据库连接池，num为连接池里的最少连接数
        self.pool = PersistentDB(creator=pymysql, maxusage = 1000 ,host=self.host,user=self.user,passwd=self.passwd,db=self.db,port=self.port, charset=self.charset) #5为连接池里的最少连接数

    
    def InsertData(self, sql):
        #插入一条数据

        # 打开数据库连接
        #connect = pymysql.connect(host=self.host,user=self.user,password=self.passwd,db=self.db,port=self.port, charset=self.charset)
        connect = None

        try:
            connect = self.pool.connection()
            connect.ping()

        except Exception as e:
            connect_count = 1
            while connect_count <= 5:
                try:
                    connect = pymysql.connect(host=self.host,user=self.user,password=self.passwd,db=self.db,port=self.port, charset=self.charset)                                               
                    connect.ping()
                    break
                except Exception as e:
                    print(e)
                    connect_count += 1
            if connect_count > 5:
                print("connect database failed!")
                return False

        # 使用cursor()方法获取操作游标 
        cursor = connect.cursor()

        try:

            # 执行sql语句
            cursor.execute(sql)
            # 提交到数据库执行
            connect.commit()
        except Exception as e:
            # 如果发生错误则回滚
            connect.rollback()
            cursor.close()
            connect.close()
            print(e)
            return False

        cursor.close()
        connect.close()

        return True

    
    def InsertDataMany(self, sql, value):
        #插入多条数据

        # 打开数据库连接
        #connect = pymysql.connect(host=self.host,user=self.user,password=self.passwd,db=self.db,port=self.port, charset=self.charset)
        connect = None

        try:
            connect = self.pool.connection()
            connect.ping()

        except Exception as e:
            connect_count = 1
            while connect_count <= 5:
                try:
                    connect = pymysql.connect(host=self.host,user=self.user,password=self.passwd,db=self.db,port=self.port, charset=self.charset,connect_timeout=10)                                               
                    connect.ping()
                    break
                except Exception as e:
                    print(e)
                    connect_count += 1
            if connect_count > 5:
                print("connect database failed!")
                return False

        # 使用cursor()方法获取操作游标 
        cursor = connect.cursor()

        try:
            # 执行sql语句
            cursor.executemany(sql, value)

            # 提交到数据库执行
            connect.commit()
        except Exception as e:
            # 如果发生错误则回滚
            connect.rollback()
            cursor.close()
            connect.close()
            print(e)
            return False

        cursor.close()
        connect.close()

        return True


    def SelectData(self, sql):
        #读取数据

        # 打开数据库连接
        connect = pymysql.connect(host=self.host,user=self.user,password=self.passwd,db=self.db,port=self.port, charset=self.charset)

        #connect = self.pool.connection()
        # 使用cursor()方法获取操作游标 
        cursor = connect.cursor()

        results = None
        try:
           # 执行SQL语句
           cursor.execute(sql)
           # 获取所有记录列表
           results = cursor.fetchall()
           
        except:
           print("Error: unable to fecth data")

        cursor.close()
        connect.close()

        return results


    def UpdataDate(self, sql):
        #更新数据

        # 打开数据库连接
        connect = self.pool.connection()
        # 使用cursor()方法获取操作游标 
        cursor = connect.cursor()

        results = None
        try:
            # 执行SQL语句
            cursor.execute(sql)
            # 提交到数据库执行
            connect.commit()
           
        except Exception as e:
            # 如果发生错误则回滚
            connect.rollback()
            cursor.close()
            connect.close()
            print(e)
            return False

        cursor.close()
        connect.close()

        return True
        
