from urllib import request
import gevent,time
from gevent import monkey
monkey.patch_all()
from gevent.pool import Pool
p = Pool(1)#设置并发数为2

def run(url):
    print("GET:{0}".format(url))
    time_start = time.time()
    resp = request.urlopen(url)    # request.urlopen()函数 用来打开网页
    data = resp.read()    # 读取爬到的数据
    print("down", time.time() - time_start)
    print('{0} bytes received from {1}'.format(len(data), url))
 
urls = [
    'http://www.163.com/',
    'https://www.yahoo.com/',
    'https://github.com/'
]
 
time_start = time.time()    # 开始时间
for url in urls:
    p.spawn(run, url)


p.join()
print("同步cost", time.time() - time_start)  # 程序执行消耗的时间