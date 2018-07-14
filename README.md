### python 多线程函数库 vthread ，简而强大

- ##### 安装
```
C:\Users\Administrator> pip3 install vthread
```
- ##### 普通的多线程
考虑到函数库的多用性，可能是觉得这种直接粗暴的开启多线程函数的测试需求比较常见，所以会保留有这样的一个功能。
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
# 可以用 vthread.pool_show 方法来查看线程数量情况。

# 主线程监视器
# 额外线程，监视主线程执行，一旦停止就向线程队列注入相应数量的停止标记
# 因为该线程池的原理就是让主线程里变成派发函数的线程，主线程执行到尾部自然就代表
# 分配的任务已经分配完了，这时就可以注入停止标记让线程执行完就赶紧结束掉
# 防止在命令行下控制权不交还的情况。
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
这样就意味着gqueue=0的线程池数量为默认的cpu核心数


# eg.4
pool1 = vthread.pool(gqueue=1)
pool2 = vthread.pool(6,gqueue=2)
pool2 = vthread.pool(8,gqueue=2)
# 这样就意味着gqueue=1的线程池数量为默认的cpu核心数，gqueue=2的线程池数量为8
```
