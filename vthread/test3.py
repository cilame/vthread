import time, random, queue
from vthread import pool, lock

ls1 = queue.Queue()
ls2 = queue.Queue()
producer = 'pr'
consumer1 = 'co1'
consumer2 = 'co2'

@pool(6, gqueue=producer)
def creater(num):
    time.sleep(random.random()) # 随机睡眠 0.0 ~ 1.0 秒
    num1, num2 = num, num*num+1000
    print("数据进入队列: num:{}".format(num))
    ls1.put(num1)
    ls2.put(num2)

# 两个消费者
@pool(1, gqueue=consumer1)
def coster1():
    while not pool.check_stop(gqueue=producer):
        time.sleep(random.random()) # 随机睡眠 0.0 ~ 1.0 秒
        pp = [ls1.get() for _ in range(ls1.qsize())]
        print('当前消费的列表 list: {}'.format(pp))
@pool(1, gqueue=consumer2)
def coster2():
    while not pool.check_stop(gqueue=producer):
        time.sleep(random.random()) # 随机睡眠 0.0 ~ 1.0 秒
        pp = [ls2.get() for _ in range(ls2.qsize())]
        print('当前消费的列表 list: {}'.format(pp))
for i in range(30): creater(i)
coster1()
coster2()

pool.wait(gqueue=producer) # 等待默认的 gqueue=producer 组线程池全部停止再执行后面内容
pool.wait(gqueue=consumer1) # 等待默认的 gqueue=consumer1 组线程池全部停止再执行后面内容
pool.wait(gqueue=consumer2) # 等待默认的 gqueue=consumer2 组线程池全部停止再执行后面内容
print('当生产和消费的任务池数据都结束后，这里才会打印')
print('current queue 1 size:{}'.format(ls1.qsize()))
print('current queue 2 size:{}'.format(ls2.qsize()))
print('end')