import time
import vthread





# vthread.thread
#========#
# 多线程 #
#========#
@vthread.thread(5) # 只要这一行就能让函数变成开5个线程执行同个函数
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, test1 foolnumb: {num}")

foolfunc(123) # 加入装饰器后，这个函数就变成了开5个线程执行的函数了





# vthread.pool
#========#
# 线程池 #
#========#
@vthread.pool(6) # 只用加这一行就能实现6条线程池的包装
def foolfunc(num):
    time.sleep(1)
    print(f"foolstring, test2 foolnumb: {num}")

for i in range(10):
    foolfunc(i) # 加入装饰器后，这个函数变成往伺服线程队列里塞原函数的函数了

# 不加装饰就是普通的单线程
# 只用加一行就能不破坏原来的结构直接实现线程池操作，能进行参数传递





# vthread.pool
#==============#
# 多组的线程池 #
#==============#
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





# 有时候你需要把某些操作进行原子化
# 可以把你要原子化的操作写成函数，用vthread.atom装饰就行
#==========#
# 加锁封装 #
#==========#
@vthread.thread(5)
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





# 另外：
# 因为对 print 打了猴子补丁，自带的 print 函数变成带锁的函数了，还加了些打印线程名字的操作
# 可以修改 vthread._vlog 为 False 来阻止打印线程名
# 也可以用 vthread.unpatch_all() 直接将 print 还原成系统默认函数
# 更多详细内容可以 help(vthread)

# 额外细节：
# 如果想将自己的某些函数进行原子操作的封装可以考虑用 @vthread.atom 装饰那个函数
# 如果你想用原函数的话，你可以用 vthread.orig_func["foolfunc1"] 获得原函数地址
# vthread.orig_func 就是一个包装【原函数名字】对应【原函数地址】的字典。
# 虽然 vthread.atom 可以实现原子操作
# 这里仍然将 lock 暴露出去，用 vthread.lock 就可以拿到这个唯一的线程锁实体





'''
#==========================#
# 测试同组线程池数量的切换 #
#==========================#
@vthread.pool(10)
def foolfunc1():
    time.sleep(1)
    print("foolstring1")

@vthread.pool(18)
def foolfunc2():
    time.sleep(1)
    print("foolstring2")

time.sleep(1.5)
# 关闭线程池也需要时间，因为默认不是默认线程join，
# 所以这里不等等的话，主线程调用 threading.active_count() 可能会计算进将关未关的线程数
import threading
print(threading.active_count())
'''





'''
#==============================================#
#                                              #
#  注意！关于多个函数装饰器，线程池数量的定义  #
#                                              #
#==============================================#
# 相同的gqueue，默认使用最后一个 "人为定义" 的伺服线程数量
# eg.1
@vthread.pool(10)
def foolfunc1():
    pass
@vthread.pool(18)
def foolfunc1():
    pass
# 这样就意味着gqueue=0的线程池数量为18

# eg.2
@vthread.pool(10)
def foolfunc1():
    pass
@vthread.pool()
def foolfunc1():
    pass
# 这样就意味着gqueue=0的线程池数量为10

# eg.3
@vthread.pool()
def foolfunc1():
    pass
@vthread.pool()
def foolfunc1():
    pass
# 这样就意味着gqueue=0的线程池数量为默认的cpu核心数

# eg.4
pool1 = vthread.pool(gqueue=1)
pool2 = vthread.pool(6,gqueue=2)
pool2 = vthread.pool(8,gqueue=2)
这样就意味着gqueue=1的线程池数量为默认的cpu核心数
这样就意味着gqueue=2的线程池数量为8
'''
