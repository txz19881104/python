# -*- coding: utf-8 -*-


import sys
import time
import database 
import base
import threading
from base import priority_queue
from base import threads
from base import EntertainmentSpider
from Comics import ComicsKKMH
from Comics import ComicsCartoonMad
from Comics import ComicsMH160
from Comics import StartComicThread
from Fiction import FictionBQG
from Fiction import StartFictionThread
import ssl
from gevent import monkey
monkey.patch_all()
ssl._create_default_https_context = ssl._create_unverified_context



class EntertainmentAPI(object):
    """外部接口"""
    def __init__(self):
        self.ComicHandle = None
        self.FictionHandle = None


    
    def GetComicHandle(self, url):
        #根据不同网址，获取不同句柄
        if url in "http://www.kuaikanmanhua.com":
            self.ComicHandle = ComicsKKMH()
        elif url in "http://www.cartoonmad.com":
            self.ComicHandle = ComicsCartoonMad()
        elif url in "http://www.mh160.com":
            self.ComicHandle = ComicsMH160()




    def LogIn(self, user, passward):
        #登录
        return self.ComicHandle._LogIn()


    
    def SetComicLoginInfo(self, url, username=None, password=None): 
        #设置基础信息 
        return self.ComicHandle._set_info(url, username, password)



    def GetComicByKeyword(self):
        """通过关键字查找到需要的内容，然后将返回的内容记录在kkmh_content结构中

        Parameters
        ----------
        keyword : str or unicode
            搜索文字

        url     ： str or unicode
            要从那个网址下载

        download_path ： str or unicode
            文件要保存的何处，默认为None

        mode    : str or unicode 
            download : 下载
            updata   ：更新图片
        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """
        download_lst = [
            {"name":'航海王（海贼王）', "url": "http://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
        ]
        print(download_lst)
        for data in download_lst:   
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

            print("%s start download" %(data['name']))
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

            #生成漫画类句柄
            self.GetComicHandle(data['url'])

            #设置网址等信息
            self.ComicHandle._set_info(data['url'], None, None)

            #通过关键字下载
            if not self.ComicHandle._GetContentByKeyword(data['name'], "download", data['download']):
                print("Download %s failed!" %(data['name']))




    def UpdateComicChapter(self, download_path=None):
        """更新章节

        Parameters
        ----------
        download_path ： str or unicode
            文件要保存的何处，默认为None

        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """

        #查找所有未完结的漫画
        ComicHandle = EntertainmentSpider()
        sql = "SELECT * FROM EntertainmentDB.ComicName WHERE IsFinish = 0;"
        results_tup = ComicHandle._EntertainmentSelect(sql)

        for result in results_tup:
            comic_id    = result[0]
            url         = result[6]

            #生成漫画类句柄
            self.GetComicHandle(url)

            #设置网址等信息
            self.ComicHandle._set_info(url, None, None)

            #获取数据库里的最大章节
            chapter_num_max = result[4]

            if url != "http://www.mh160.com":
                continue

            #下载网页，得到当前的最大章节数，然后下载
            for dct_img_book in self.ComicHandle._UpdataChapter(result, download_path):
                chapter_num = dct_img_book['chapter']

                if chapter_num > chapter_num_max:
                    chapter_num_max = chapter_num

                #插入图片到数据库
                if not self.ComicHandle._InsertImg(chapter_num, dct_img_book, download_path):
                    print("download %s failed" %dct_img_book)
                    results = False

            #更新当前数据库里的最大章节数
            if chapter_num_max > result[4]:
                sql = "update EntertainmentDB.ComicName set ChapterNum = %d  where ID = %d;" %(chapter_num, comic_id)
                if not self.ComicHandle._EntertainmentUpdate(sql):
                    print("%s insert failed!" %(sql))



    def UpdateComicPicture(self, download_path=None):
        """图片地址有时会失效，故需要更新图片

        Parameters
        ----------
        download_path ： str or unicode
            文件要保存的何处，默认为None

        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """

        #查找所有未完结的漫画
        results = True

        #获取当前数据库里的所有漫画
        ComicHandle = EntertainmentSpider()
        sql = "SELECT * FROM EntertainmentDB.ComicName;"
        results_tup = ComicHandle._ComicSelect(sql)

        for result in results_tup:
            keyword        = result[1]
            url            = result[5]

            #生成漫画类句柄
            self.GetComicHandle(url)

            #漫画ID
            self.ComicHandle.id = result[0]

            #设置网址等信息
            self.ComicHandle._set_info(url, None, None)

            #如果队列不为空，则说明当前漫画还没有处理完成，等待完成后在下载下一部漫画
            while True:
                if not priority_queue.empty():
                    print("queue size : %d" %(priority_queue.qsize()))
                    time.sleep(5)
                    continue
                else:
                    break

            #更新数据库
            if not self.ComicHandle._GetContentByKeyword(keyword, "update"):
                print("Download %s failed!" %(keyword))
                result = False


        return results


    def GetFictionHandle(self, url):
        #根据不同网址，获取不同句柄
        if url in "http://www.biquge.com.tw":
            self.FictionHandle = FictionBQG()


    def GetFictionByKeyword(self):
        """通过关键字查找到需要的内容，然后将返回的内容记录在kkmh_content结构中

        Parameters
        ----------
        keyword : str or unicode
            搜索文字

        url     ： str or unicode
            要从那个网址下载

        download_path ： str or unicode
            文件要保存的何处，默认为None

        mode    : str or unicode 
            download : 下载
            updata   ：更新图片
        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """
        download_lst = [
            {"name":'鬼吹灯', "url": "http://www.biquge.com.tw", "download": "/mnt/TecentCloud"},
        ]
        print(download_lst)
        for data in download_lst:   
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

            print("%s start download" %(data['name']))
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

            #生成漫画类句柄
            self.GetFictionHandle(data['url'])

            #设置网址等信息
            self.FictionHandle._set_info(data['url'], None, None)

            #通过关键字下载
            if not self.FictionHandle._GetContentByKeyword(data['name'], "download", data['download']):
                print("Download %s failed!" %(data['name']))




    def UpdateFictionChapter(self, download_path=None):
        """更新章节

        Parameters
        ----------
        download_path ： str or unicode
            文件要保存的何处，默认为None

        Returns
        -------
        success: dict[list]--self.kkmh_content
        failed : None
        """

        #查找所有未完结的漫画
        ComicHandle = EntertainmentSpider()
        sql = "SELECT * FROM EntertainmentDB.FictionName WHERE IsFinish = 0;"
        results_tup = ComicHandle._EntertainmentSelect(sql)

        for result in results_tup:
            fiction_id  = result[0]
            url         = result[6]

            print(result[1])
            #生成漫画类句柄
            self.GetFictionHandle(url)

            #设置网址等信息
            self.FictionHandle._set_info(url, None, None)

            #获取数据库里的最大章节
            chapter_num_max = result[4]

            #下载网页，得到当前的最大章节数，然后下载
            for dct_book in self.FictionHandle._UpdataChapter(result):
                chapter_num = dct_book['chapter']

                if chapter_num > chapter_num_max:
                    chapter_num_max = chapter_num
                                #插入小说到数据库
                if not self.FictionHandle._InsertFiction(dct_book['chapter'], dct_book, download_path):
                    print("insert %s failed" %(dct_book["title"]))

            #更新当前数据库里的最大章节数
            if chapter_num_max > result[4]:
                sql = "update EntertainmentDB.FictionName set ChapterNum = %d  where ID = %d;" %(chapter_num_max, fiction_id)
                print(sql)
                if not self.FictionHandle._EntertainmentUpdate(sql):
                    print("%s insert failed!" %(sql))
            

now = lambda : time.time()
if __name__ == '__main__':

    start = now()
    print("begin CreateDBPool")
    #配置数据库链接池
    database.gHandleDatabase = database.SaveToDatabase("198.13.54.7", "txz", "passwd", "EntertainmentDB", 3306, "utf8")
    database.gHandleDatabase.CreateDBPool()

    #获取娱乐类句柄
    EntertainmentAPi = EntertainmentAPI()

    print('database: ', now() - start)
    if sys.argv[1] == "Comic":
        #启动线程
        print("begin StartThread")
        StartComicThread(50)
        print('thread: ', now() - start)
        #下载模式
        if sys.argv[2] == "DownloadAll":
            EntertainmentAPi.GetComicByKeyword()

        #更新模式，增加新的章节
        elif sys.argv[2] == "UpdateChapter":
            EntertainmentAPi.UpdateComicChapter("/mnt/TecentCloud")
        """
        #更新模式，更新漫画图片
        elif sys.argv[2] == "UpdatePicture":
            EntertainmentAPi.UpdateComicPicture("/mnt/TecentCloud")
        """

    elif sys.argv[1] == "Fiction":
        #启动线程
        print("begin StartThread")
        StartFictionThread(20)

        #下载模式
        if sys.argv[2] == "DownloadAll":
            EntertainmentAPi.GetFictionByKeyword()

        #更新模式，增加新的章节
        elif sys.argv[2] == "UpdateChapter":
            EntertainmentAPi.UpdateFictionChapter("/mnt/TecentCloud")

    while True:
        if not priority_queue.empty():
            print("threads conunt :%d" %threading.active_count())
            print("queue size : %d" %(priority_queue.qsize()))
            time.sleep(5)
            continue
        else:
            break

    
    #关闭所有线程
    #for t in threads:
    #    t.join()

    print('finish: ', now() - start)
    print("download finish")
    #if not EntertainmentAPi.SaveToDatabase('/home/txz/download',dct_img_book):
    #    print("download failed!")
    #EntertainmentAPi.ParseContent(content)


"""
            {"name":'火影忍者', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'航海王（海贼王）', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'死神/境·界', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'银魂', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'网球王子', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'阿拉蕾', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'游戏王', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'就喜欢你看不惯我又干不掉我的样子', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'青空下', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'当神不让', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'就喜欢你看不惯我又干不掉我的样子', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'就喜欢你看不惯我又干不掉我的样子', "url": "https://www.kuaikanmanhua.com", "download": "/mnt/TecentCloud"},
            {"name":'美食的俘虜', "url": "http://www.cartoonmad.com", "download": "/mnt/TecentCloud"},



            
            {"name":'全职法师', "url": "http://www.biquge.com.tw", "download": "/mnt/TecentCloud"},
            {"name":'斗罗大陆', "url": "http://www.biquge.com.tw", "download": "/mnt/TecentCloud"},
"""