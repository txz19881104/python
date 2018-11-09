# -*- coding: utf-8 -*-
# ------------------------------------------
#   版本：1.0
#   日期：2018-06-01
#   作者：Txz
# ------------------------------------------

import base
import json
import collections 
import time
import threading
import queue 
from request import BaseRequest
from urllib import parse
from base import Fiction
from base import Job
from base import priority_queue
from base import threads

#打开num个线程
def StartFictionThread(num):
    for i in range(num):  
        dt = DatamineThreadFiction(priority_queue)#线程任务就是从源代码中解析出<title>标签内的内容  
        #dt.setDaemon(True)  
        dt.start() 
        threads.append(dt)
#漫画
class DatamineThreadFiction(threading.Thread):  
    def __init__(self,queue):  
        threading.Thread.__init__(self)  
        self.queue = queue 

    #线程处理
    def run(self): 
        IsHaveData = True 
        while IsHaveData:
            chunk = None
            #如果300秒没有数据则退出线程

            try:   
                chunk = self.queue.get(block=True, timeout=60) 
            except queue.Empty:
                IsHaveData = False
                continue

            chunkData = chunk.description


            #下载漫画
            if chunkData["type"] == "download":
                data       = chunkData["data"]
                subtype    = chunkData["subtype"]
                selfFiction= chunkData["self"]
                title      = data["title"]
                url_a_book = data["url"]
                count      = data["count"]
                href       = data["href"]
                ID         = data["ID"]

                
                dct_book = {}

                soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'gbk')
                if soup_a_book != None:
                    print(count, title)
                    #找到每一章节的图片地址并保存
                    if "http://www.biquge.com.tw" in url_a_book:
                        content_book = soup_a_book.find('div',{'id':'content'})
                        content = ""
                        for x in content_book.contents:
                            if "qidian" not in str(x) and "http" not in str(x):
                                content = content + ''.join(str(x))

                        content = content.replace("\"", "“")
                        content = content.replace("\'", "\‘") 
                        content = content.replace("\\xC2\\xA0", "&nbsp;") 
                        content = content.replace("\xa0", "&nbsp;")

                        

                    #将数据存储到结构体中,用于后续保存
                    dct_book = {'href':href, 'title':title, 'chapter':count, 'content':content}
                    dic_queue = {}
                    if subtype == "download":
                        dic_queue = {"type": "insert", "data": dct_book, "self": selfFiction}
                    elif subtype == "update":
                        dic_queue = {"type": "update", "data": dct_book, "self": selfFiction}

                    self.queue.put(Job(1, dic_queue))

                else:
                    print("%s download faild"%(title))

            #插入到数据库
            elif chunkData["type"] == "insert":
                dct_book   = chunkData["data"]
                selfFiction = chunkData["self"]

                if not selfFiction._InsertFiction(dct_book['chapter'], dct_book, selfFiction.download_path):
                    print("insert %s failed" %(dct_book["title"]))
            



class FictionBQG(Fiction):
    """https://www.kuaikanmanhua.com 快看漫画"""
    def _GetContentByKeyword(self, keyword, mode, download_path=None):
        """通过关键字查找到需要的内容，然后将返回的内容记录在kkmh_content结构中

        Parameters
        ----------
        keyword : str or unicode
            搜索文字

        mode    : str or unicode 
            download : 下载
            updata   ：更新图片
        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """

        #请求keyword网页
        self.keyword       = keyword
        self.download_path = download_path

        url_keyword        = self._url + '/modules/article/soshu.php?searchkey=' +  parse.quote(keyword, encoding='gbk', errors='replace') 
        content_keyword    = BaseRequest.GetUrlSoup(url_keyword, 'gbk')
        if content_keyword == None:
            return False

        #将返回的内容解析
        find_result = []
        if content_keyword.find('caption'):
            a_result = content_keyword.find_all('tr',{'id':'nr'})
            if a_result == None:
                return False

            for result in a_result:
                find_result.append({"name":result.td.a.contents[0], "url": result.td.a['href']})        
        else:
            a_url = content_keyword.find('meta',{'property':'og:url'})
            if a_url == None:
                return False

            a_name = content_keyword.find('meta',{'property':'og:novel:book_name'})
            if a_name == None:
                return False
            find_result.append({"name":a_name["content"], "url":a_url['content']})        


        for result in find_result:
            if mode == "download":
                #判断此漫画是否已经下载过
                sql = "SELECT * FROM EntertainmentDB.tbl_fiction_name WHERE name=\"%s\";" %(result["name"])
                if self._EntertainmentSelect(sql):
                    print(result["name"])
                    continue

                #等待上一部小说下载完成   
                while True:
                    if not priority_queue.empty():
                        print("threads conunt :%d" %threading.active_count())
                        print("queue size : %d" %(priority_queue.qsize()))
                        if threading.active_count() < 10:
                            StartFictionThread(10)  
                        time.sleep(60)
                        continue
                    else:
                        break

                self.keyword         = result["name"]
                soup_keyword_content = BaseRequest.GetUrlSoup(result["url"], 'gbk')
                if soup_keyword_content == None:
                    return False

                a_name      = soup_keyword_content.find('meta',{'property':'og:novel:book_name'})
                a_introduce = soup_keyword_content.find('meta',{'property':'og:description'})
                a_image     = soup_keyword_content.find('meta',{'property':'og:image'})
                a_category  = soup_keyword_content.find('meta',{'property':'og:novel:category'})
                a_author    = soup_keyword_content.find('meta',{'property':'og:novel:author'})
                a_url       = soup_keyword_content.find('meta',{'property':'og:novel:read_url'})
                a_status    = soup_keyword_content.find('meta',{'property':'og:novel:status'})
                a_list      = soup_keyword_content.find('div', {'id':'list'})
                a_book      = a_list.dl.find_all('dd')

                #下载封面图片
                
                for i in range(5):
                    if download_path != None:
                        path = '%s/Fiction/%s/' %(download_path, self.keyword)
                        if not BaseRequest.DownloadData(a_image['content'], path, "封面.jpg"):
                            print("download %s failed %d time" % ("封面.jpg", i))
                        else:
                            print("download %s%s success" % (path,"封面.jpg"))
                            break

                src = "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Fiction/" + self.keyword + "/" + "封面.jpg"

                #将漫画信息存储到数据库
                sql_dict = collections.OrderedDict()
                sql_dict['name']      = "\"" + a_name['content'] + "\""             #名字
                sql_dict['watch_count']  = 0                                           #编号  
                sql_dict['website']   = "\"" + self._url + "\""                     #网址
                sql_dict['chapter_count']= len(a_book)                                 #总共有多少章节
                sql_dict['introduce'] = "\"" + a_introduce['content'] + "\""        #漫画介绍
                sql_dict['author']    = "\"" + a_author['content']  + "\""          #作者
                sql_dict['cover_img_src']       = "\"" +  src + "\""                          #封面图片
                sql_dict['type']      = "\"" + a_category['content'] + "\""         #漫画类型
                sql_dict['add_time']      = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                if "连载中" in a_status['content']:
                    sql_dict['is_finish'] = 0                                        #是否完结
                else:
                    sql_dict['is_finish'] = 1

                if not self._EntertainmentInsert('tbl_fiction_name', sql_dict):
                    print("inster tbl_fiction_name table failed!")
                    continue


                #获取漫画编号，唯一
                sql = "SELECT ID FROM EntertainmentDB.tbl_fiction_name WHERE name=\"%s\";" %(a_name['content'])
                max_id = self._EntertainmentSelect(sql)
                if max_id:
                    self.id = max_id[0][0]
                else:
                    print("get max_id failed!")
                    continue

            elif mode == "update":
                now_Time = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                sql = "update EntertainmentDB.tbl_fiction_name set add_time = %s  where pk_id = %d;" %(now_Time, self.id)
                if not self._EntertainmentUpdate(sql):
                    print("%s update failed!" %(sql))

            count = 1
            for book in a_book:

                href  = book.a['href']
                title = book.a.contents[0]
                
                #当前章节的内容插入到队列中
                url_a_book  = self._url + href
                data = {"ID": self.id, "url": url_a_book, "title":title, "href":href, "count": count}
                if mode == "download":
                    dic_queue = {"type": "download", "subtype": "download", "self":self, "data":data}
                elif mode == "update":
                    dic_queue = {"type": "download", "subtype": "update", "self":self, "data":data}

                priority_queue.put(base.Job(2,dic_queue,self._url))

                count += 1

        return True
        

    def _UpdataChapter(self, result):
        """更新最新章节，然后将返回的内容记录在kkmh_content结构中

        Parameters
        ----------
        keyword : str or unicode
            搜索文字
        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """

        keyword     = result[1]
        chapter_num = result[4]
        self.id     = result[0]

        #请求keyword网页
        self.keyword       = keyword

        url_keyword        = self._url + '/modules/article/soshu.php?searchkey=' +  parse.quote(keyword, encoding='gbk', errors='replace') 
        content_keyword    = BaseRequest.GetUrlSoup(url_keyword, 'gbk')
        if content_keyword == None:
            return None

        #将返回的内容解析
        find_result = []
        if content_keyword.find('caption'):
            a_result = content_keyword.find_all('tr',{'id':'nr'})
            if a_result == None:
                return None

            for result in a_result:
                find_result.append({"name":result.td.a.contents[0], "url": result.td.a['href']})        
        else:
            a_url = content_keyword.find('meta',{'property':'og:url'})
            if a_url == None:
                return None

            a_name = content_keyword.find('meta',{'property':'og:novel:book_name'})
            if a_name == None:
                return None
            find_result.append({"name":a_name["content"], "url":a_url['content']})    

        
        #取出id关键字，从而访问搜索到的内容
        for result in find_result:
            #获取漫画编号，唯一
            
            if result["name"] != keyword:
                continue

            soup_keyword_content = BaseRequest.GetUrlSoup(result["url"], 'gbk')
            if soup_keyword_content == None:
                return None

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            a_list      = soup_keyword_content.find('div', {'id':'list'})
            a_book      = a_list.dl.find_all('dd')

            now_chapter_num = len(a_book)
            for book in reversed(a_book):
                print(now_chapter_num, chapter_num)
                if now_chapter_num <= chapter_num:
                    return None

                href  = book.a['href']
                title = book.a.contents[0]
                url_a_book  = self._url + href

                lst_img_book = []
                dct_img_book = {}
                dct_book = {}

                soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'gbk')
                if soup_a_book == None:
                    return None

                #找到每一章节的图片地址并保存
                content_book = soup_a_book.find('div',{'id':'content'})
                content = ""
                for x in content_book.contents:
                    if "qidian" not in str(x) and "http" not in str(x):
                        content = content + ''.join(str(x))

                content = content.replace("\"", "“")
                content = content.replace("\'", "\‘") 
                content = content.replace("\\xC2\\xA0", "&nbsp;") 
                content = content.replace("\xa0", "&nbsp;")

                dct_book = {'href':href, 'title':title, 'chapter':now_chapter_num, 'content':content}

                now_chapter_num = now_chapter_num - 1
                
                yield dct_book
