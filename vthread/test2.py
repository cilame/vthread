import vthread
# 生成两个线程池装饰器来并行处理多线程的 “请求” 和 “写入” 两种功能
pool_gets = vthread.pool(8,gqueue=1)# 线程池1 多线程请求任务
pool_save = vthread.pool(1,gqueue=2)# 线程池2 数据写入文件，只开一个线程的性能足够处理写入任务


import os, re, json, time, queue, traceback
import requests
from lxml import etree
datapipe = queue.Queue() # 不同线程之间用管道传递数据
@pool_gets
def crawl(page):
    url = 'https://www.baidu.com/s?wd=123&pn={}'.format(page*10)
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36"
    }
    s = requests.get(url, headers=headers)
    if s.history and s.history[0].status_code == 302:
        print('retrying {}.'.format(s.history[0].request.url))
        crawl(page) # 百度现在有验证码问题，直接重新提交任务即可。
        return
    tree = etree.HTML(s.content.decode('utf-8'))
    for x in tree.xpath('//div/h3[@class="t"]/parent::*'):
        d = {}
        d["href"]  = x.xpath('./h3/a[1][@target]/@href')[0]
        d["title"] = x.xpath('string(./h3[@class="t"])').strip()
        datapipe.put(d)
@pool_save
def save_jsonline():
    def check_stop():
        try:    ret = vthread.pool.check_stop(gqueue=1) # 检查1号线程池的任务是否全部请求结束
        except: ret = False; print(traceback.format_exc()) # 当你不用 vthread 时也能运行的保底处理
        return ret
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime()) # 年月日_时分秒
    filename = 'v{}.json'.format(timestamp) # 输出文件名(这里使用jsonlines格式存储)
    with open(filename, "a", encoding="utf-8") as f:
        while True:
            for _ in range(datapipe.qsize()):
                data = datapipe.get()
                print('write: {}'.format(data))
                f.write(json.dumps(data, ensure_ascii=False)+"\n")
            time.sleep(.25)
            if (not check_stop()) and (not datapipe.qsize()):
                break

# 提交 n 个网页请求的任务，然后开启写入任务
for page in range(20): crawl(page)
save_jsonline()
# 虽然这里的处理按照该脚本代码的逻辑可以不必让 save_jsonline 变成线程执行，不过数据保存也写成线程池的好处就是
# 如果存在多个不同的表格存储，你就可以按照类似的方式， 新加一个数据管道，新加一个保存函数进行多文件并行存储


# 由于被 vthread.pool 装饰的函数变成了任务提交函数，
# 所以在提交完任务时候很快就执行到下一行而不会等待任务执行完
# 所以如果需要等待任务执行完再执行下一行内容的话，需要使用 vthread.pool.wait(gqueue) 来处理
# 不过 vthread 已经自动挂钩的主线程，都会等待任务结束，脚本才会完全停止，下面的两行代码视不同情使用即可
# vthread.pool.wait(gqueue=1) # 等待1号线程池任务执行完
# vthread.pool.wait(gqueue=2) # 等待2号线程池任务执行完
# print('end')