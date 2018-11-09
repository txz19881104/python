# -*- coding: utf-8 -*-
# ------------------------------------------
#   版本：1.0
#   日期：2018-04-01
#   作者：Txz
# ------------------------------------------


import base
from base import Comics
from request import BaseRequest
from urllib import parse
from base import Job
from base import priority_queue
from base import threads
import json
import collections 
import time
import threading
import gevent
from gevent import monkey
#monkey.patch_all()
from gevent.pool import Pool

def ComicProcesses(tasks):
    p = Pool(5)#设置并发数为20
    for task in tasks:
        p.spawn(run, task)              
    p.join()

now = lambda : time.time()


#线程处理
def run(chunk): 

    chunkData = chunk.description

    #下载漫画
    if chunkData["type"] == "download":
        
        data       = chunkData["data"]
        subtype    = chunkData["subtype"]
        selfComic  = chunkData["self"]
        title      = data["title"]
        url_a_book = data["url"]
        count      = data["count"]
        href       = data["href"]

        lst_img_book = []
        dct_img_book = {}

        if "http://www.kuaikanmanhua.com" in url_a_book:
            
            while True:
                soup_a_book = BaseRequest.GetUrlSoup(url_a_book)
                
                if soup_a_book != None:
                    print(count, title)
                    #找到每一章节的图片地址并保存
                
                    content_img_book = soup_a_book.find_all('img',{'class':'kklazy', 'title':title})

                    for img_book in content_img_book:
                        lst_img_book.append(img_book['data-kksrc'].replace('amp;', ''))

                    break
                else:
                    continue

        elif "http://www.cartoonmad.com" in url_a_book:
            title = title.replace(' ','')
            soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'big5')
            if soup_a_book != None:
                print(count, title)
                content_img_book = soup_a_book.find_all('img',{'oncontextmenu':'return false'})
                img_num = soup_a_book.find_all('option', value=True)
                for num in range(len(img_num)):
                    img = content_img_book[0]['src']
                    img = img[0:(len(img)-7)]

                    if (num+1) < 10:
                        img = img + '00' + str(num+1) + ".jpg"
                    elif (num+1) >= 10 and (num+1) < 100:
                        img = img + '0' + str(num+1)  + ".jpg"
                    else:
                        img = img + str(num+1)  + ".jpg"

                    lst_img_book.append(img)

        elif "http://www.mh160.com" in url_a_book:
            title = title.replace(' ','')
            soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'gbk')
            if soup_a_book != None:
                print(count, title)

                url_list = url_a_book.split("/")
                comic_id = url_list[-2]
                chapter_id = url_list[-1][0:-5]
                
                for i in range(20):
                    download_url   = "http://mhpic5.lineinfo.cn/mh160tuku/s/"
                    keyword_encode = parse.urlencode({"": selfComic.keyword})
                    title_encode   = parse.urlencode({"": title})

                    name = ''
                    if (i+1) < 10:
                        name = '/000' + str(i+1) + ".jpg"
                    elif (i+1) >= 10 and (i+1) < 100:
                        name = '/00' + str(i+1)  + ".jpg"
                    else:
                        name = '/0' + str(i+1)  + ".jpg"
                        
                    download_url = download_url + keyword_encode[1:len(keyword_encode)] + "_" + comic_id + "/" + title_encode[1:len(title_encode)] + "_" + chapter_id + name
                    lst_img_book.append(download_url)

        else:
            print("%s download faild"%(title))
            return False

        #将数据存储到结构体中,用于后续保存
        dct_img_book = {'href':href, 'title':title, 'chapter':count, 'download_url':lst_img_book}
        dic_queue = {}
        if subtype == "download":
            dic_queue = {"type": "insert", "data": dct_img_book, "self": selfComic}
        elif subtype == "update":
            dic_queue = {"type": "update", "data": dct_img_book, "self": selfComic}

        if not selfComic._InsertImg(dct_img_book['chapter'], dct_img_book, selfComic.download_path):
            print("insert %s failed" %(dct_img_book["title"]))
            return False

    #插入到数据库
    elif chunkData["type"] == "insert":
        dct_img_book  = chunkData["data"]
        selfComic     = chunkData["self"]

        if not selfComic._InsertImg(dct_img_book['chapter'], dct_img_book, selfComic.download_path):
            print("insert %s failed" %(dct_img_book["title"]))

        del dct_img_book["download_url"][:]

    #更新数据到数据库
    elif chunkData["type"] == "update":
        dct_img_book = chunkData["data"]


        cComics = Comics()
        if not cComics._UpdateImg(dct_img_book):
            print("update %s failed" %(dct_img_book["title"]))
    
        print("update")
        print(dct_img_book["chapter"], dct_img_book["title"])

    #thread = threading.current_thread()
    #print(thread.getName()) 
    #self.queue.task_done()  

class ComicsKKMH(Comics):
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
        url_keyword        = self._url + '/web/topic/search?keyword' +  parse.urlencode({"": keyword})
        content_keyword    = BaseRequest.GetUrlContent(url_keyword)
        if content_keyword == None:
            return False

        #将返回的内容解析
        content_keyword_json = json.loads(content_keyword.decode("utf8"))
        if content_keyword_json == False:
            return False

        #取出id关键字，从而访问搜索到的内容
        for data in content_keyword_json['data']['topic']:

            if mode == "download":
                #判断此漫画是否已经下载过
                sql = "SELECT * FROM EntertainmentDB.ComicName WHERE Name=\"%s\";" %(data['title'])
                if self._EntertainmentSelect(sql):
                    print(data['title'])
                    continue

            #等待上一部漫画下载完成   
            while True:
                if not priority_queue.empty():
                    print("threads conunt :%d" %threading.active_count())
                    print("queue size : %d" %(queue.qsize()))
                    if threading.active_count() < 10:
                        StartComicThread(10)  
                    time.sleep(60)
                    continue
                else:
                    break

            self.keyword         = data['title']
            url_keyword_content  = self._url + '/web/topic/' + str(data['id'])
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content)
            if soup_keyword_content == None:
                return False

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            a_book = soup_keyword_content.find_all('a',{'class':'article-img'})

            if mode == "download":

                a_author    = soup_keyword_content.find('div', {'class':'author-nickname'})
                a_introduce = soup_keyword_content.find('div', {'class':'switch-content'})
                a_img       = soup_keyword_content.find('img', {'class':'kk-img'})

                #下载漫画封面
                for i in range(5):
                    if download_path != None:
                        path = '%s/Comics/%s/' %(download_path, self.keyword)
                        if not BaseRequest.DownloadData(a_img['src'], path, "封面.jpg"):
                            print("download %s failed %d time" % ("封面.jpg", i))
                        else:
                            print("download %s%s success" % (path,"封面.jpg"))
                            break

                src = "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Comics/" + self.keyword + "/" + "封面.jpg"

                #将漫画信息存储到数据库
                sql_dict = collections.OrderedDict()
                sql_dict['name']      = "\"" + data['title'] + "\""         #名字
                sql_dict['watch_count']  = 0                                   #编号  
                sql_dict['website']   = "\"" + self._url + "\""             #网址
                sql_dict['chapter_count']= len(a_book)                         #总共有多少章节
                sql_dict['is_finish']  = 0                                   #是否完结
                sql_dict['introduce'] = "\"" + a_introduce.p.contents[0].replace('\"', '') + "\""   #漫画介绍
                sql_dict['author']    = "\"" + a_author.contents[0] + "\""  #作者
                sql_dict['cover_img_src']       = "\"" + src + "\""                   #封面图片
                sql_dict['type']      = "\"" + self.type + "\""             #漫画类型
                sql_dict['time']      = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间

                if not self._EntertainmentInsert('tbl_comic_name', sql_dict):
                    print("inster tbl_comic_name table failed!")
                    continue

                #获取漫画编号，唯一
                sql = "SELECT pk_id FROM EntertainmentDB.tbl_comic_name WHERE Name=\"%s\";" %(data['title'])
                max_id = self._EntertainmentSelect(sql)
                if max_id:
                    self.id = max_id[0][0]
                else:
                    print("get max_id failed!")
                    continue

            elif mode == "update":
                now_Time = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                sql = "update EntertainmentDB.tbl_comic_name set add_time = %s  where pk_id = %d;" %(now_Time, self.id)
                if not self._EntertainmentUpdate(sql):
                    print("%s update failed!" %(sql))

            #processpool = multiprocessing.Pool(processes = 8)
            count = 1
            for book in reversed(a_book):
                href  = book['href']
                title = book['title']
                src   = book.img['src']

                #当前章节的内容插入到队列中
                url_a_book  = self._url + href
                data = {"url": url_a_book, "title":title, "src": src, "href":href, "count": count}
                if mode == "download":
                    dic_queue = {"type": "download", "subtype": "download", "self":self, "data":data}
                elif mode == "update":
                    dic_queue = {"type": "download", "subtype": "update", "self":self, "data":data}

                priority_queue.put(base.Job(2,dic_queue,self._url))

                count += 1

                    #pp = processpool.apply_async(test)
                    
                #p.spawn(run)              
            #p.join()


        return True
        

    def _UpdataChapter(self, result, download_path=None):
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
        self.download_path = download_path

        url_keyword        = self._url + '/web/topic/search?keyword' +  parse.urlencode({"": keyword})
        content_keyword    = BaseRequest.GetUrlContent(url_keyword)
        if content_keyword == False:
            return None

        #将返回的内容解析
        content_keyword_json = json.loads(content_keyword.decode("utf8"))
        if content_keyword_json == False:
            return None

        
        #取出id关键字，从而访问搜索到的内容
        for data in content_keyword_json['data']['topic']:
            #获取漫画编号，唯一
            
            if data['title'] != keyword:
                continue

            url_keyword_content = self._url + '/web/topic/' + str(data['id'])
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content)
            if soup_keyword_content == False:
                return None

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            a_book = soup_keyword_content.find_all('a',{'class':'article-img'})

            now_chapter_num = len(a_book)
            for book in a_book:
                print(now_chapter_num, chapter_num)
                if now_chapter_num <= chapter_num:
                    return None

                
                href  = book['href']
                title = book['title']
                lst_img_book = []
                dct_img_book = {}

                #下载当前章节的内容
                url_a_book  = self._url + href
                soup_a_book = BaseRequest.GetUrlSoup(url_a_book)
                if soup_a_book == None:
                    return None

                #找到每一章节的图片地址并保存
                content_img_book = soup_a_book.find_all('img',{'class':'kklazy', 'title':title})
                for img_book in content_img_book:
                    lst_img_book.append(img_book['data-kksrc'].replace('amp;', ''))

                #将数据存储到结构体中,用于后续保存
                dct_img_book = {'href':href, 'title':title, 'chapter':now_chapter_num, 'download_url':lst_img_book}
                self.lst_kkmh_content.append(dct_img_book)

                now_chapter_num = now_chapter_num - 1
                
                yield dct_img_book



class ComicsCartoonMad(Comics):
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
        url_keyword        = self._url + '/search.html'

        keyword_encode = keyword.encode('big5','strict');
        params = {  
            'keyword':keyword_encode,  
            'searchtype':'all',  
        }
        params = parse.urlencode(params).encode("big5")

        content_keyword = BaseRequest.PostUrlSoup(url_keyword, params, 'big5')
        if content_keyword == None:
            return False

        a_result = content_keyword.find_all('span',{'class':'covertxt'})

        #取出id关键字，从而访问搜索到的内容
        for data in a_result:
            data_next_siblings = data.find_next_siblings()
            
            if mode == "download":
                #判断此漫画是否已经下载过
                sql = "SELECT * FROM EntertainmentDB.tbl_comic_name WHERE name=\"%s\";" %(data_next_siblings[0]['title'])
                if self._EntertainmentSelect(sql):
                    print(data_next_siblings[0]['title'])
                    continue
            
            #等待上一部漫画下载完成   
            while True:
                if not priority_queue.empty():
                    print("threads conunt :%d" %threading.active_count())
                    print("queue size : %d" %(priority_queue.qsize()))
                    if threading.active_count() < 10:
                        StartComicThread(10)  
                    time.sleep(60)
                    continue
                else:
                    break
            

            self.keyword         = data_next_siblings[0]['title']
            print(self.keyword)
            url_keyword_content  = self._url + "/" + data_next_siblings[0]['href']
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content, 'big5')
            if soup_keyword_content == None:
                return False

            #将漫画信息存储到数据库
            sql_dict = collections.OrderedDict()
            sql_dict['name']      = "\"" + self.keyword + "\""          #名字
            sql_dict['watch_count']  = 0                                   #编号  
            sql_dict['website']   = "\"" + self._url + "\""             #网址

            save_content = soup_keyword_content.find_all('td',{'width':276})
            if save_content == None:
                return False

            sql_dict['type']     = "\"" + save_content[1].a.contents[0].strip() + "\""
            sql_dict['author']   = "\"" + save_content[3].contents[1].strip() + "\""
            a_IsFinish = 0
            if save_content[5].contents[4]['src'].strip() == "/image/chap1.gif":
                sql_dict['is_finish'] = 0
            elif save_content[5].contents[4]['src'].strip() == "/image/chap9.gif":
                sql_dict['is_finish'] = 1
            else:
                sql_dict['is_finish'] = 0

            save_content = soup_keyword_content.find_all('table',{'width':688,'cellspacing':"8"})
            if save_content != None:
                sql_dict['introduce'] = "\"" + save_content[0].tr.td.contents[0].strip() + "\""
            else:
                sql_dict['introduce'] = ''

            save_content = soup_keyword_content.find_all('img',{'width':'240','height':'320'})
            a_img = ''
            if save_content != None:
                a_img = self._url + save_content[0]['src']
                

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            save_content = soup_keyword_content.find_all('table',{'width':'688', 'align':'center'})
            if save_content == None:
                return False

            a_book = []
            for data_content in save_content[0].tbody:
                for data_td in data_content:
                    a = data_td.find('a')
                    if a != None and a != -1:
                        a_book.append(a)

            if mode == "download":

                #下载漫画封面
                for i in range(5):
                    if download_path != None:
                        path = '%s/Comics/%s/' %(download_path, self.keyword)
                        if not BaseRequest.DownloadData(a_img, path, "封面.jpg"):
                            print("download %s failed %d time" % ("封面.jpg", i))
                        else:
                            print("download %s%s success" % (path,"封面.jpg"))
                            break

                src = "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Comics/" + self.keyword + "/" + "封面.jpg"

                #将漫画信息存储到数据库
                sql_dict['cover_img_src']       = "\"" + src + "\""
                sql_dict['chapter_count']= len(a_book)                         #总共有多少章节
                sql_dict['add_time']      = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间

                
                if not self._EntertainmentInsert('tbl_comic_name', sql_dict):
                    print("inster tbl_comic_name table failed!")
                    continue

                #获取漫画编号，唯一
                sql = "SELECT pk_id FROM EntertainmentDB.tbl_comic_name WHERE name=\"%s\";" %(self.keyword)
                max_id = self._EntertainmentSelect(sql)
                if max_id:
                    self.id = max_id[0][0]
                else:
                    print("get max_id failed!")
                    continue
                
            elif mode == "update":
                now_Time = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                sql = "update EntertainmentDB.tbl_comic_name set add_time = %s  where pk_id = %d;" %(now_Time, self.id)
                if not self._EntertainmentUpdate(sql):
                    print("%s update failed!" %(sql))

            count = 1
            for book in (a_book):
                href  = book['href']
                title = book.contents[0]

                #当前章节的内容插入到队列中
                url_a_book  = self._url + href

                data = {"url": url_a_book, "title":title, "href":href, "count": count}
                if mode == "download":
                    dic_queue = {"type": "download", "subtype": "download", "self":self, "data":data}
                elif mode == "update":
                    dic_queue = {"type": "download", "subtype": "update", "self":self, "data":data}


                count += 1

        return True
        

    def _UpdataChapter(self, result, download_path=None):
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
        self.download_path = download_path

        url_keyword        = self._url + '/search.html'
        keyword_encode = keyword.encode('big5','strict');
        params = {  
            'keyword':keyword_encode,  
            'searchtype':'all',  
        }
        params = parse.urlencode(params).encode("big5")

        content_keyword = BaseRequest.PostUrlSoup(url_keyword, params, 'big5')
        if content_keyword == None:
            return None

        a_result = content_keyword.find_all('span',{'class':'covertxt'})

        #取出id关键字，从而访问搜索到的内容
        for data in a_result:
            data_next_siblings = data.find_next_siblings()

            print(data_next_siblings[0]['title'], keyword)
            if data_next_siblings[0]['title'] != keyword:
                continue

            url_keyword_content  = self._url + "/" + data_next_siblings[0]['href']
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content, 'big5')
            if soup_keyword_content == None:
                return None

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            save_content = soup_keyword_content.find_all('table',{'width':'688', 'align':'center'})
            if save_content == None:
                return None

            a_book = []
            for data_content in save_content[0].tbody:
                for data_td in data_content:
                    a = data_td.find('a')
                    if a != None and a != -1:
                        a_book.append(a)

            now_chapter_num = len(a_book)
            for book in reversed(a_book):
                print(now_chapter_num, chapter_num)
                if now_chapter_num <= chapter_num:
                    return None

                href  = book['href']
                title = book.contents[0]
                lst_img_book = []
                dct_img_book = {}

                #下载当前章节的内容
                url_a_book  = self._url + href
                soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'big5')
                if soup_a_book == None:
                    return None

                content_img_book = soup_a_book.find_all('img',{'oncontextmenu':'return false'})
                img_num = soup_a_book.find_all('option', value=True)
                for num in range(len(img_num)):
                    img = content_img_book[0]['src']
                    img = img[0:(len(img)-7)]

                    if (num+1) < 10:
                        img = img + '00' + str(num+1) + ".jpg"
                    elif (num+1) >= 10 and (num+1) < 100:
                        img = img + '0' + str(num+1)  + ".jpg"
                    else:
                        img = img + str(num+1)  + ".jpg"

                    lst_img_book.append(img)



                #将数据存储到结构体中,用于后续保存
                dct_img_book = {'href':href, 'title':title, 'chapter':now_chapter_num, 'download_url':lst_img_book}
                self.lst_kkmh_content.append(dct_img_book)

                now_chapter_num = now_chapter_num - 1
                
                yield dct_img_book



class ComicsMH160(Comics):
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
        url_keyword        = self._url + '/e/search/'

        keyword_encode = keyword.encode('gbk','strict');
        button_encode  = "搜索漫画".encode('gbk','strict');
        params = {  
            'key':keyword_encode,  
            'button':button_encode,  
        }
        params = parse.urlencode(params).encode("gbk")
        content_keyword = BaseRequest.PostUrlSoup(url_keyword, params, 'gbk')
        if content_keyword == None:
            return False

        a_result = content_keyword.find_all('p',{'class':'fl cover'})
        #取出id关键字，从而访问搜索到的内容
        for data in a_result:
            
            if mode == "download":
                #判断此漫画是否已经下载过
                sql = "SELECT * FROM EntertainmentDB.tbl_comic_name WHERE name=\"%s\";" %(data.a.img['alt'])
                if self._EntertainmentSelect(sql):
                    print("%s 已经下载过，请查看数据库" % data.a.img['alt'] )
                    continue
            
            #等待上一部漫画下载完成   
            while True:
                if not priority_queue.empty():
                    print("threads conunt :%d" %threading.active_count())
                    print("queue size : %d" %(priority_queue.qsize()))
                    if threading.active_count() < 10:
                        StartComicThread(10)  
                    time.sleep(60)
                    continue
                else:
                    break
            

            self.keyword         = data.a.img['alt']
            print(self.keyword)
            url_keyword_content  = self._url + "/" + data.a['href']
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content, 'gbk')
            if soup_keyword_content == None:
                return False

            #将漫画信息存储到数据库
            sql_dict = collections.OrderedDict()
            sql_dict['name']      = "\"" + self.keyword + "\""          #名字
            sql_dict['watch_count']  = 0                                   #编号  
            sql_dict['website']   = "\"" + self._url + "\""             #网址

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            book = soup_keyword_content.find('div',{'class':'plist pnormal','id':'play_0'})
            a_book = []
            for data_content in book.ul:
                a = data_content.find('a')
                if a != None and a != -1:
                    a_book.append(a)

            if mode == "download":

                a_author    = soup_keyword_content.find('meta', {'property':'og:novel:author'})
                a_category  = soup_keyword_content.find('meta', {'property':'og:novel:category'})
                a_img       = soup_keyword_content.find('meta', {'property':'og:image'})
                a_introduce = soup_keyword_content.find('p', {'id':'intro'})
                IsFinish    = soup_keyword_content.find('meta', {'property':'og:novel:status'})
                if (IsFinish['content'] == '连载中'):
                    a_isfinish = 0
                else:
                    a_isfinish = 1
                
                #下载漫画封面
                for i in range(5):
                    if download_path != None:
                        path = '%s/Comics/%s/' %(download_path, self.keyword)
                        if not BaseRequest.DownloadData(a_img['content'], path, "封面.jpg"):
                            print("download %s failed %d time" % ("封面.jpg", i))
                        else:
                            print("download %s%s success" % (path,"封面.jpg"))
                            break
                src = "https://txz-1256783950.cos.ap-beijing.myqcloud.com/Comics/" + self.keyword + "/" + "封面.jpg"

                #将漫画信息存储到数据库
                sql_dict = collections.OrderedDict()
                sql_dict['name']      = "\"" + self.keyword + "\""          #名字
                sql_dict['watch_count']  = 0                                   #编号  
                sql_dict['website']   = "\"" + self._url + "\""             #网址
                sql_dict['chapter_count']= len(a_book)                         #总共有多少章节
                sql_dict['is_finish']  = a_isfinish                          #是否完结
                sql_dict['introduce'] = "\"" + a_introduce.a.contents[0] + "\""   #漫画介绍
                sql_dict['author']    = "\"" + a_author['content'] + "\""   #作者
                sql_dict['cover_img_src']       = "\"" + src + "\""                   #封面图片
                sql_dict['type']      = "\"" + a_category['content'] + "\""             #漫画类型
                sql_dict['add_time']      = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                
                if not self._EntertainmentInsert('tbl_comic_name', sql_dict):
                    print("inster tbl_comic_name table failed!")
                    continue

                #获取漫画编号，唯一
                sql = "SELECT pk_id FROM EntertainmentDB.tbl_comic_name WHERE name=\"%s\";" %(data.a.img['alt'])
                max_id = self._EntertainmentSelect(sql)
                if max_id:
                    self.id = max_id[0][0]
                else:
                    print("get max_id failed!")
                    continue
                
            elif mode == "update":
                now_Time = "\"" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\"" #下载时间
                sql = "update EntertainmentDB.tbl_comic_name set add_time = %s  where pk_id = %d;" %(now_Time, self.id)
                if not self._EntertainmentUpdate(sql):
                    print("%s update failed!" %(sql))

            count = 1
            for book in reversed(a_book):
                href  = book['href']
                title = book['title']

                #当前章节的内容插入到队列中
                url_a_book  = self._url + href

                data = {"url": url_a_book, "title":title, "href":href, "count": count}
                if mode == "download":
                    dic_queue = {"type": "download", "subtype": "download", "self":self, "data":data}
                elif mode == "update":
                    dic_queue = {"type": "download", "subtype": "update", "self":self, "data":data}


                count += 1

        return True
        

    def _UpdataChapter(self, result, download_path=None):
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
        self.download_path = download_path

        url_keyword        = self._url + '/e/search/'

        keyword_encode = keyword.encode('gbk','strict');
        button_encode  = "搜索漫画".encode('gbk','strict');
        params = {  
            'key':keyword_encode,  
            'button':button_encode,  
        }
        params = parse.urlencode(params).encode("gbk")
        content_keyword = BaseRequest.PostUrlSoup(url_keyword, params, 'gbk')
        if content_keyword == None:
            return None

        a_result = content_keyword.find_all('p',{'class':'fl cover'})

        #取出id关键字，从而访问搜索到的内容
        for data in a_result:
            #获取漫画编号，唯一
            
            if data.a.img['alt'] != keyword:
                continue

            url_keyword_content  = self._url + "/" + data.a['href']
            soup_keyword_content = BaseRequest.GetUrlSoup(url_keyword_content, 'gbk')
            if soup_keyword_content == None:
                return None

            #找到漫画所有章节的地址,由于网页的顺序是从最后一章至第一章，所以要反向循环
            book = soup_keyword_content.find('div',{'class':'plist pnormal','id':'play_0'})
            a_book = []
            for data_content in book.ul:
                a = data_content.find('a')
                if a != None and a != -1:
                    a_book.append(a)

            now_chapter_num = len(a_book)
            for book in a_book:
                print(now_chapter_num, chapter_num)
                if now_chapter_num <= chapter_num:
                    return None
                
                href  = book['href']
                title = book['title']
                lst_img_book = []
                dct_img_book = {}

                title = title.replace(' ','')
                #下载当前章节的内容
                url_a_book  = self._url + href

                soup_a_book = BaseRequest.GetUrlSoup(url_a_book, 'gbk')
                if soup_a_book == None:
                    return None

                url_list = url_a_book.split("/")
                comic_id = url_list[-2]
                chapter_id = url_list[-1][0:-5]
                
                for i in range(20):
                    download_url   = "http://mhpic5.lineinfo.cn/mh160tuku/s/"
                    keyword_encode = parse.urlencode({"": self.keyword})
                    title_encode   = parse.urlencode({"": title})

                    name = ''
                    if (i+1) < 10:
                        name = '/000' + str(i+1) + ".jpg"
                    elif (i+1) >= 10 and (i+1) < 100:
                        name = '/00' + str(i+1)  + ".jpg"
                    else:
                        name = '/0' + str(i+1)  + ".jpg"

                    download_url = download_url + keyword_encode[1:len(keyword_encode)] + "_" + comic_id + "/" + title_encode[1:len(title_encode)] + "_" + chapter_id + name
                    lst_img_book.append(download_url)


                #将数据存储到结构体中,用于后续保存
                dct_img_book = {'href':href, 'title':title, 'chapter':now_chapter_num, 'download_url':lst_img_book}
                self.lst_kkmh_content.append(dct_img_book)

                now_chapter_num = now_chapter_num - 1
                
                yield dct_img_book






