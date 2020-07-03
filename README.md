## python 多线程函数库 vthread ，简而强大

- ##### 安装
```
C:\Users\Administrator> pip3 install vthread
```
- ##### 线程池（核心功能）
不加装饰器就是普通的单线程，只用加一行就能在不破坏原来的结构直接实现线程池操作，能进行参数传递，支持分组，这已经到了不破坏代码的极限了。
```python
import time
import vthread

@vthread.pool(6) # 只用加这一行就能实现6条线程池的包装
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, test2 foolnumb: {num}")

for i in range(10):
    foolfunc(i) # 加入装饰器后，这个函数变成往伺服线程队列里塞原函数的函数了

# 不加装饰就是普通的单线程
# 只用加一行就能不破坏原来的代码结构直接实现线程池操作，能进行参数传递

执行效果如下：
[  Thread-1  ] foolstring, test2 foolnumb: 0
[  Thread-5  ] foolstring, test2 foolnumb: 4
[  Thread-2  ] foolstring, test2 foolnumb: 2
[  Thread-6  ] foolstring, test2 foolnumb: 5
[  Thread-4  ] foolstring, test2 foolnumb: 3
[  Thread-3  ] foolstring, test2 foolnumb: 1
[  Thread-1  ] foolstring, test2 foolnumb: 6
[  Thread-5  ] foolstring, test2 foolnumb: 7
[  Thread-2  ] foolstring, test2 foolnumb: 8
[  Thread-6  ] foolstring, test2 foolnumb: 9
```
- ##### 支持分组线程池
如果你想要让你的某几个函数有M个线程执行，而另外几个函数要N个线程去执行。
那么请看看下面的使用说明
```
import time
import vthread

pool_1 = vthread.pool(5,gqueue=1) # 开5个伺服线程，组名为1
pool_2 = vthread.pool(2,gqueue=2) # 开2个伺服线程，组名为2

@pool_1
def foolfunc1(num):
    time.sleep(1)
    print(f"foolstring1, test3 foolnumb1:{num}")

@pool_2 # foolfunc2 和 foolfunc3 用gqueue=2的线程池
def foolfunc2(num):
    time.sleep(1)
    print(f"foolstring2, test3 foolnumb2:{num}")
@pool_2 # foolfunc2 和 foolfunc3 用gqueue=2的线程池
def foolfunc3(num):
    time.sleep(1)
    print(f"foolstring3, test3 foolnumb3:{num}")

for i in range(10): foolfunc1(i)
for i in range(10): foolfunc2(i) 
for i in range(10): foolfunc3(i)
# 额外开启线程池组的话最好不要用gqueue=0
# 因为gqueue=0就是默认参数
```

- ##### 原子封装
如果需要考虑对函数内的某些步骤进行锁的操作，那么请看下面的使用说明。
```
# 有时候你需要把某些操作进行原子化
# 可以把你要原子化的操作写成函数，用vthread.atom装饰就行
import time
import vthread

@vthread.pool(5)
def foolfunc_():

    @vthread.atom # 将函数加锁封装
    def do_some_fool_thing1():
        pass # do_something
    @vthread.atom # 将函数加锁封装
    def do_some_fool_thing2():
        pass # do_something

    # 执行时就会实现原子操作
    do_some_fool_thing1()
    do_some_fool_thing2()
```
- ##### 等待执行完毕再继续任务
再某些情况下需要等待线程池任务完成之后再继续后面的操作，请看如下使用。
```
# 可以使用 vthread.pool.wait 函数来等待某一组线程池执行完毕再继续后面的操作
# 该函数仅有一个默认参数 gqueue=0，需要等待的分组。
# 该函数的本质就是一个定时循环内部使用 vthread.pool.check_stop 函数不停检测某个任务组是否结束。
# check_stop 函数返回结果为 0 则为线程池已执行结束。
# 如果有比 wait 更丰富的处理请使用 check_stop 。
import time
import vthread

@vthread.pool(5)
def foolfunc_():
    time.sleep(1)
    print(123)
for i in range(10): foolfunc_()

vthread.pool.wait() # 等待gqueue=0分组线程执行完毕再继续后面的代码
print('end.')
```

- ## 百度爬虫，线程池示例脚本
简单使用该库写一个简单的多线程 “请求”和 “写入文件”并行处理的百度爬虫作为使用范例。这里的代码仍然是注释装饰器则为正常单线程，添加装饰器则自动变成多线程池处理。
```python
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
```

- ##### 额外说明
```
# 另外：
# 为了便于调试函数在任意第一次装饰过后会对 print 打猴子补丁
# 自带的 print 函数变成带锁的函数了，还加了些打印线程名字的操作
# 可以通过 vthread.toggle 函数对这些或其他一些功能进行关闭
# 也可以用 vthread.unpatch_all() 直接将 print 还原成系统默认函数
# 更多详细内容可以 help(vthread)

# 额外细节：
# 如果想将自己的某些函数进行原子操作的封装可以考虑用 @vthread.atom 装饰那个函数
# 如果你想用原函数的话，你可以用 vthread.orig_func["foolfunc1"] 获得原函数地址
# vthread.orig_func 就是一个包装【原函数名字】对应【原函数地址】的字典。
# 虽然 vthread.atom 可以实现原子操作
# 这里仍然将 lock 暴露出去，用 vthread.lock 就可以拿到这个唯一的线程锁实体
# 可以用 vthread.pool.show 方法来查看线程池数量情况。

# 为了不用使用者收尾：
# 当使用者装饰任意数量的线程池的时候，都会默认只开一个不计入数量的线程MainMonitor
# 就是监视主线程执行情况，一旦主线程执行完，同时所有线程池函数处于伺服状态就向线程队列注入相应数量的停止标记
# 需要两个条件：
# 1. 主线程执行完毕
# 因为该线程池的原理就是让主线程变成派发函数的进程，执行到尾部自然就代表
# 分配的任务已经分配完了，这时就可以注入停止标记让线程执行完就赶紧结束掉
# 2. 每个函数都处于等待获取函数参数状态（即保证函数执行完毕）
# 当线程内嵌套其他分组的线程池函数的时，被嵌套的函数在之前是有可能不执行的
# 所以就设计了条件2，以确保所有需要分发的函数能够全部分发完成且执行完毕
# 因为是队列操作不会影响线程效率，MainMonitor线程只是为了防止在命令行下控制权不交还的情况。
# 当然在之前设计的时候是可以用人为等所有代码执行完毕最后执行一次 vthread.pool.close_all() 即可解决。
# 但是为了更易用，为了不让使用者在代码最后添加这一句话，就设计了这个监控线程
```
- ##### 另外强调的困惑
假如在使用过程中装饰了多个函数会怎么计算线程池的线程数量呢？
这里给出了说明，在 vthread.pool 函数库中，是以 gqueue 这个参数来确定线程池分组的。
而相同的分组，则会默认使用最后一个 "人为定义" 的伺服线程数量。
```
#==============================================#
#                                              #
#  注意！关于多个函数装饰器，线程池数量的定义  #
#                                              #
#==============================================#
# -------------------- eg.1 --------------------
@vthread.pool(10)
def foolfunc1():
    pass
@vthread.pool(18)
def foolfunc1():
    pass
# 这样就意味着gqueue=0的线程池数量为18
# -------------------- eg.2 --------------------
@vthread.pool(10)
def foolfunc1():
    pass
@vthread.pool()
def foolfunc1():
    pass
# 这样就意味着gqueue=0的线程池数量为10
# -------------------- eg.3 --------------------
@vthread.pool()
def foolfunc1():
    pass
@vthread.pool()
def foolfunc1():
    pass
这样就意味着gqueue=0的线程池数量为默认的cpu核心数
# -------------------- eg.4 --------------------
pool1 = vthread.pool(gqueue=1)
pool2 = vthread.pool(6,gqueue=2)
pool2 = vthread.pool(8,gqueue=2)
@pool1
def foolfunc1(): 
    pass
@pool2
def foolfunc1(): 
    pass
# 这样就意味着gqueue=1的线程池数量为默认的cpu核心数，gqueue=2的线程池数量为8
#==============================================#
# 为了避免这种定义时可能出现的问题。
# 建议在多个函数需要使用线程池的情况下，最好使用 eg.4 中的处理方式：
#     1 先生成装饰器对象 2 然后再装饰需要进入多线程的函数
#==============================================#
```

- ##### 普通的多线程
【不建议使用】 考虑到函数库的多用性，可能是觉得这种直接粗暴的开启多线程函数的测试需求比较常见，所以会保留有这样的一个功能。
```python
import time
import vthread

@vthread.thread(5) # 只要这一行就能让函数变成开5个线程执行同个函数
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, test1 foolnumb: {num}")

foolfunc(123) # 加入装饰器后，这个函数就变成了开5个线程执行的函数了

# 考虑到函数库的易用性，个人觉得这种直接粗暴的开启多线程函数的测试需求比较常见
# 所以才保留了这样的一个功能。

执行效果如下：
[  Thread-1  ] foolstring, test1 foolnumb: 123
[  Thread-2  ] foolstring, test1 foolnumb: 123
[  Thread-3  ] foolstring, test1 foolnumb: 123
[  Thread-4  ] foolstring, test1 foolnumb: 123
[  Thread-5  ] foolstring, test1 foolnumb: 123

# 为了使函数执行更独立（方便参数传递）可以用 vthread.thread(1) 来装饰
# 但是为了使用更为简便 这里的 vthread.thread 等同于 vthread.thread(1)
@vthread.thread 
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, test1 foolnumb: {num}")

for i in range(5):
    foolfunc(123) # 执行与数量分离，可以使得参数传递更为动态

# 执行效果同上
# 注意：
# vthread.thread 不带参数的方式只能装饰一个函数，装饰多个函数会出现问题，仅用于测试单个函数。
# vthread.thread(1) 带参数的可以装饰多个函数，但是已经有了分组线程池的强大功能，为什么还要这样浪费资源呢？
```
