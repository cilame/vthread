import time
import vthread


#========#
# 多线程 #
#========#
@vthread.thread(5) # 只要这一行就能开N个线程执行同个函数
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, foolnumb: {num}")

foolfunc(123) # 加入装饰器后，这个函数就变成了开N个线程执行的函数了


#========#
# 线程池 #
#========#
@vthread.pool(1,6) # 只用加这一行就能实现N线程池的包装
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, foolnumb: {num}")

for i in range(10):
    foolfunc(i) # 加入装饰器后，这个函数变成往伺服线程队列里塞原函数的函数了


#================#
# 不同组的线程池 #
#================#
pool_1 = vthread.pool(1,5,gqueue=1)
pool_2 = vthread.pool(1,2,gqueue=2)

@pool_1
def foolfunc1(num):
    time.sleep(1)
    print(f"foolstring1, foolnumb1:{num}")

@pool_2
def foolfunc2(num):
    time.sleep(1)
    print(f"foolstring2, foolnumb2:{num}")

for i in range(10): foolfunc1(i)
for i in range(10): foolfunc2(i)

# 另外：
# 因为对 print 打了猴子补丁，自带的 print 函数变成带锁的函数了
# 可以用 vthread.unpatch_all() 还原
# 更多详细内容可以 help(vthread)
