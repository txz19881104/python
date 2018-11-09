# -*- coding: utf-8 -*-
import collections 
import threading
import time  
import json
import queue
import database 
import pymysql
from request import BaseRequest
from urllib import parse

category_map = [
    '热血',
    '格斗',
    '魔法',
    '侦探',
    '竞技',
    '恐怖',
    '战国',
    '魔幻',
    '冒险',
    '校园',
    '搞笑',
    '少女',
    '少男',
    '科幻',
    '港产',
    '其他' 
]
priority_queue = queue.PriorityQueue()#存放网址的队列  
threads = []


#队列优先级
class Job(object):
    def __init__(self, priority, description, url=None):
        self.priority = priority
        self.description = description
        self.url = url
        return

    def __lt__(self, other):
        return self.priority < other.priority



class EntertainmentSpider(object):
    """娱乐基类"""
    def __init__(self):
        self._user     = None        # 用户名
        self._passward = None        # 密码
        self._url      = None        # 网址

    def _log_in(self):
        pass        

    #设置基础信息
    def _set_info(self, url, username=None, password=None):
        self._user     = username        # 用户名
        self._passward = password        # 密码
        self._url      = url             # 网址


    def _EntertainmentInsert(self, table, sql_dict):
        """插入内容到数据库

        Parameters
        ----------
        table    : str or unicode
                    数据库表名
        sql_dict : dict
                    数据库各字段的字典
            
        Returns
        -------
        success: True
        failed : False
        """

        result  = True
        key     = None
        value   = None

        for (k,v) in sql_dict.items(): 
            if key != None:
                key   = "%s,%s"%(key, k)
            else:
                key   = "%s"%(k)

            if value != None:
                value = "%s,%s"%(value, v)
            else:
                value   = "%s"%(v)

        # SQL 插入语句        
        sql = "INSERT INTO %s.%s(%s) VALUES (%s);" %("EntertainmentDB", table, key, value)
        if database.gHandleDatabase.InsertData(sql):
            pass
        else:
            print("%s intsert failed!" %(sql)) 
            result = False

        return result

    def _EntertainmentInsertMany(self, table, key, value):
        """插入内容到数据库

        Parameters
        ----------
        table    : str or unicode
                    数据库表名
        sql_dict : dict
                    数据库各字段的字典
            
        Returns
        -------
        success: True
        failed : False
        """

        # SQL 插入语句        
        sql = "INSERT INTO %s.%s(%s) VALUES %s" %("EntertainmentDB", table, key, "(%s,%s,%s,%s);")
        if database.gHandleDatabase.InsertDataMany(sql, value):
            pass
        else:
            print("%s intsert failed!" %(sql)) 
            return False

        time.sleep(0.1)

        return True

    def _EntertainmentSelect(self, sql):
        """插入内容到数据库

        Parameters
        ----------
        sql    : str or unicode
                 数据库选择语句
            
        Returns
        -------
        success: True
        failed : False
        """

        results = database.gHandleDatabase.SelectData(sql)
        if None == results:
            print(sql)            

        return results


    def _EntertainmentUpdate(self, sql):
        """插入内容到数据库

        Parameters
        ----------
        sql    : str or unicode
                 数据库选择语句
            
        Returns
        -------
        success: True
        failed : False
        """

        results = database.gHandleDatabase.UpdataDate(sql)
        if None == results:
            print(sql)            

        return results


class Comics(EntertainmentSpider):
    """漫画类,所有漫画网站的基类"""
    def __init__(self):
        self.lst_kkmh_content = []
        """
        dict[list]
            {
                'href': '',             # 每个章节的地址
                'title': '',            # 每个章节的名字
                'src': '',              # 每个章节的封面地址
                'download_url': [list], # 当前章节的所有内容的地址
            }
        """
        self.keyword = ""               # 下载关键字
        self.id      = 0                # 每部漫画保存在数据库中都有唯一的id
        self.type    = category_map[0]  # 漫画类型
        self.download_path = ""


    def _InsertImg(self, chapter_num, dct_img_book, download_path=None):
        """下载封面图片和漫画

        Parameters
        ----------
        chapter_num   : int
                        章节号
        download_path : str or unicode
                        存储路径
        dct_img_book : str or unicode
                        需要存储的数据，格式为   
            {
                'href': '',             # 每个章节的地址
                'title': '',            # 每个章节的名字
                'src': '',              # 每个章节的封面地址
                'download_url': [list], # 当前章节的所有内容的地址
            }               
        Returns
        -------
        success: True
        failed : False
        """

        #标题及封面路径
        title         = dct_img_book['title']
        ID            = self.id
        chapter_num   = dct_img_book['chapter']
        path = '%s/Comics/%s/%s/' %(download_path, self.keyword, title)
        
        """
        #下载封面图片
        
        file_name     = 'fengmian.jpg'
        if not BaseRequest.DownloadData(src, download_path, file_name):
            print("download fengmian.jpg failed")
            return False
        """

        #下载漫画内容，图片按1开始自增
        success_count = 0
        count = 1
        for url in dct_img_book['download_url']:
            file_name = '%d.jpg' %(count)
            
            if not BaseRequest.DownloadData(url, path, file_name):
                print("download %s failed %d time" % (file_name, i))
            else:
                #print("download %s%s success %d" % (path,file_name,success_count))
                success_count = success_count + 1
                count += 1


        #将章节信息保存到章节表中
        sql_dict = collections.OrderedDict()
        sql_dict['chapter_num']   = chapter_num                                      #章节号
        sql_dict['chapter_name']  = "\"" + title + "\""                              #章节名称
        sql_dict['pic_count']       = success_count                                    #图片数量
        #sql_dict['Img']          = "\"" + dct_img_book['src'] + "\""               #封面图片
        sql_dict['fk_id']      = ID                                               #外键，关联漫画名称表，与其id相同
        
        #插入数据到章节表中
        for i in range(10):
            if not self._EntertainmentInsert('tbl_comic_chapter', sql_dict):
                print("inster tbl_comic_chapter table failed!")
                time.sleep(2)
            else:
                break

        key   = "page_num, fk_comic_id, fk_comic_chapter_id, img_src"
        value = []
        count = 1
        #下载漫画内容，图片按1开始自增，批量插入
        for i in range(success_count+1):
            file_name = '%d.jpg' %(count)
            count = count + 1
            src = "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Comics/" + self.keyword + "/"  + title + "/" + file_name
            data=(i+1, ID, chapter_num, src)  
            value.append(data) 
                #sql_src = collections.OrderedDict()
                #sql_src['Page_Num']  = count
                #sql_src['Comic_ID'] = self.id
                #sql_src['Comic_ChapterNum'] = chapter_num
                #sql_src['Img_src']  = "\"" + url + "\""
        
        #过快的插入会导致插入失败，如果发现失败，等待两秒，然后再次插入
        for i in range(10):
            #插入数据到章节表中
            if not self._EntertainmentInsertMany('tbl_comic_img', key, value):
                print("inster tbl_comic_img table failed!")
                time.sleep(2)
            else:
                break

        return True

    def _UpdateImg(self, dct_img_book):
        """更新漫画图片

        Parameters
        ----------

        dct_img_book : str or unicode
                        需要存储的数据，格式为   
            {
                'href': '',             # 每个章节的地址
                'title': '',            # 每个章节的名字
                'src': '',              # 每个章节的封面地址
                'download_url': [list], # 当前章节的所有内容的地址
            }               
        Returns
        -------
        success: True
        failed : False
        """ 
        count         = 0
        ID            = dct_img_book['ID']
        chapter_num   = dct_img_book['chapter']

        #下载漫画内容，图片按1开始自增
        for url in dct_img_book['download_url']:
            count += 1
            Img_src  = "\"" + url + "\""
            for i in range(10):
                sql = "update EntertainmentDB.tbl_comic_img set img_src = %s  where fk_comic_chapter_id = %d and fk_comic_id = %d and page_num = %d;" %(Img_src, chapter_num, ID, count)
                if not self._EntertainmentUpdate(sql):
                    print("%s insert failed!" %(sql))
                else:
                    break
        return True


class Fiction(EntertainmentSpider):
    """小说类,所有漫画网站的基类"""
    def __init__(self):
        self.lst_kkmh_content = []
        """
        dict[list]
            {
                'href': '',             # 每个章节的地址
                'title': '',            # 每个章节的名字
                'src': '',              # 每个章节的封面地址
                'download_url': [list], # 当前章节的所有内容的地址
            }
        """
        self.keyword = None             # 下载关键字
        self.id      = 0                # 每部漫画保存在数据库中都有唯一的id
        self.type    = category_map[0]  # 漫画类型


    def _InsertFiction(self, chapter_num, dct_img_book, download_path=None):
        """下载封面图片和漫画

        Parameters
        ----------
        chapter_num   : int
                        章节号
        download_path : str or unicode
                        存储路径
        dct_img_book : str or unicode
                        需要存储的数据，格式为   
            {
                'href': '',             # 每个章节的地址
                'title': '',            # 每个章节的名字
                'src': '',              # 每个章节的封面地址
                'download_url': [list], # 当前章节的所有内容的地址
            }               
        Returns
        -------
        success: True
        failed : False
        """

        #标题及封面路径
        title         = dct_img_book['title']
        content       = dct_img_book['content']
        ID            = self.id
        chapter_num   = dct_img_book['chapter']
        path = '%s/Fiction/%s/' %(download_path, self.keyword)
        #下载封面图片
        count         = 0

        #下载漫画内容，图片按1开始自增
        file_name = '%s.txt' %(title)
        BaseRequest.SaveData(path, file_name, content)

        #将章节信息保存到章节表中
        sql_dict = collections.OrderedDict()
        sql_dict['chapter_num']   = chapter_num              #章节号
        sql_dict['chapter_name']  = "\"" + title + "\""      #章节名称
        sql_dict['content_src']   = "\"" + "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Fiction/" + self.keyword + "/"  + file_name + "\""      #小说内容
        sql_dict['fk_id']      = ID                       #外键，关联漫画名称表，与其id相同
        
        #sql = "INSERT INTO EntertainmentDB.FictionChapter(ChapterNum,ChapterName,Content,Dept_ID) VALUES (%s,%s,%s,%s);" %(sql_dict['ChapterNum'],sql_dict['ChapterName'],content,ID)
        #if database.gHandleDatabase.InsertData(sql):
        #    pass
        #else:
        #    print("%s intsert failed!" %(sql)) 
        #    result = False

        #return True

        #插入数据到章节表中
        for i in range(10):
            if not self._EntertainmentInsert('tbl_fiction_chapter', sql_dict):
                print("inster tbl_fiction_chapter table failed!")
                time.sleep(2)
            else:
                break


        return True
