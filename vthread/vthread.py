'''
#==============================================================
# 更加方便的多线程调用，类装饰器封装，一行代码实现线程池
#
# 注意：
# 装饰器会默认对 print 函数进行 monkey patch
# 会对python自带的 print 函数加锁使 print 带有原子性便于调试
# 默认打开 log 让 print 能够输出线程名字
# 可以通过 toggle 函数关掉显示线程名功能（不关锁）
# 可以通过执行 vthread.unpatch_all() 解除这个补丁还原 print
#==============================================================
'''
import time
import queue
import traceback
from threading import Thread,Lock,RLock,\
                     current_thread,main_thread
import builtins
import functools


lock = RLock()

class log_flag:
    _decorator_toggle = True
    _vlog = True # print是否显示线程名字
    _elog = True # 是否打印错误信息


# 所有被装饰的原始函数都会放在这个地方
orig_func = {}

_org_print = print
def _new_print(*arg,**kw):
    lock.acquire()
    if log_flag._vlog:
        name = current_thread().getName()
        name = "[{}]".format(name.center(13))
        _org_print(name,*arg,**kw)
    else:
        _org_print(*arg,**kw)
    lock.release()


def toggle(toggle=False,name="thread"):
    '''
    #==============================================================
    # 开关显示方式
    # 目前提供修改的参数有三个：
    # 1. "thread"  # 是否在print时在最左显示线程名字
    # 2. "error"   # 是否显示error信息
    #==============================================================
    '''
    # 因为装饰器是每次装饰都会默认打开 _vlog 一次，所以添加这个参数放置
    # 使得这个函数一旦在最开始执行之后，装饰器就不会再打开 _vlog 了
    global _monitor
    log_flag._decorator_toggle = False
    if name == "thread" : log_flag._vlog = toggle
    if name == "error"  : log_flag._elog = toggle


class thread:
    '''
    #==============================================================
    # 普通的多线程装饰
    #
    # >>> import vthread
    # >>>
    # >>> # 将 foolfunc 变成动态开启3个线程执行的函数
    # >>> @vthread.thread(3) # 默认参数:join=False,log=True
    # ... def foolfunc():
    # ...     print("foolstring")
    # >>> 
    # >>> foolfunc() # 一次执行开启三个线程执行相同函数
    # [  Thread-1  ]: foolstring
    # [  Thread-2  ]: foolstring
    # [  Thread-3  ]: foolstring
    # >>>
    #==============================================================
    # 为了和pool的使用方法共通（一次函数执行只是一次函数单独执行的效果）
    # 这里添加了一种更为简便的装饰手段
    #
    # >>> import vthread
    # >>>
    # >>> # 将 foolfunc 变成开启新线程执行的函数
    # >>> @vthread.vthread # 这时的 vthread.thread 等同于 vthread.thread(1)
    # ... def foolfunc():
    # ...     print("foolstring")
    # >>>
    # >>> for i in range(4):
    # ...     foolfunc() # 每次执行都会开启新线程，默认不join。
    # [  Thread-1  ]: foolstring
    # [  Thread-2  ]: foolstring
    # [  Thread-3  ]: foolstring
    # [  Thread-4  ]: foolstring
    # >>>
    #
    # 不过需要注意的是，不要将 vthread.thread 带参数和不带参数的装饰器混用
    # 可能会导致一些不可预知的异常。
    #==============================================================
    '''
    def __init__(self,num=1,join=False,log=True):
        '''
        #==============================================================
        # *args
        #     :num   线程数量
        # **kw
        #     :join  多线程是否join
        #     :log   print函数的输出时是否加入线程名作前缀
        #==============================================================
        '''
        # 为了兼容不带参数的装饰方式，这里做了如下修改。
        if type(num)==type(lambda:None): 
            def _no_params_func(self,*args,**kw):
                v = Thread(target=num,args=args,kwargs=kw)
                v.start()
            thread.__call__ = _no_params_func
        else:
            self.num  = num
            self.join = join

        # 让配置在 toggle 执行变成只能手动配置 log_flag
        if log_flag._decorator_toggle:
            log_flag._vlog = log
        
        # 默认将 print 函数进行monkey patch
        patch_print()        

    def __call__(self,func):
        '''
        #==============================================================
        # 类装饰器入口
        #==============================================================
        '''
        orig_func[func.__name__] = func
        @functools.wraps(func)
        def _run_threads(*args,**kw):
            p = []
            for _ in range(self.num):
                # 这里包装一下异常捕捉，防止异常导致的不 join
                def _func():
                    try:
                        func(*args,**kw)
                    except Exception as e:
                        if log_flag._elog:
                            print(traceback.format_exc())
                p.append(Thread(target=_func))
            for i in p: i.start()
            if self.join:
                for i in p: i.join()
        return _run_threads

class KillThreadParams(Exception):
    '''一个用来杀死进程的函数参数'''
    pass

class pool:
    '''
    #==============================================================
    # 线程池的多线程装饰
    # 对代码入侵较小，例如
    #
    # >>> import vthread
    # >>> import time
    # >>>
    # >>> # 只需要加下面这一行就可以将普通迭代执行函数变成线程池多线程执行
    # >>> @vthread.pool(5) # 对于 foolfunc 开启5个线程池
    # >>> def foolfunc(num):
    # ...     time.sleep(1)
    # ...     print(f"foolstring, foolnumb:{num}")
    # >>>
    # >>> # 默认参数:pool_num=None,log=True,gqueue='v'
    # >>> # pool_num不选时就自动选 cpu 核心数
    # >>> # 就是说，装饰方法还可以更简化为 @vthread.pool()
    # >>>
    # >>> for i in range(10):
    # ...     foolfunc(i)
    # [  Thread-3  ] foolstring, foolnumb:1
    # [  Thread-2  ] foolstring, foolnumb:2
    # [  Thread-1  ] foolstring, foolnumb:0
    # [  Thread-5  ] foolstring, foolnumb:3
    # [  Thread-4  ] foolstring, foolnumb:4
    # [  Thread-3  ] foolstring, foolnumb:5
    # [  Thread-2  ] foolstring, foolnumb:6
    # [  Thread-1  ] foolstring, foolnumb:7
    # [  Thread-5  ] foolstring, foolnumb:8
    # [  Thread-4  ] foolstring, foolnumb:9
    # >>> # 这里的函数执行都是放在伺服线程中执行。
    # >>> # 如果不指定 gqueue 参数，默认是共用0号队列
    # >>> # 不指定 gqueue 参数给多个函数装饰的情况下
    # >>> # 用的都是一组伺服线程
    # >>>
    #==============================================================
    # 可以尝试用gqueue的参数来实现不同函数不同作用域
    # 开启多组伺服线程
    #
    # >>>
    # >>> import vthread
    # >>> pool1 = vthread.pool(5,gqueue=1) # 开5个伺服线程，组名为1
    # >>> pool2 = vthread.pool(1,gqueue=2) # 开1个伺服线程，组名为2
    # >>> 
    # >>> @pool1
    # >>> def foolfunc1(num):
    # >>>     time.sleep(1)
    # >>>     print(f"foolstring1, foolnumb1:{num}")
    # >>> @pool2
    # >>> def foolfunc2(num):
    # >>>     time.sleep(1)
    # >>>     print(f"foolstring2, foolnumb2:{num}")
    # >>> 
    # >>> for i in range(5): foolfunc1(i)
    # >>> for i in range(5): foolfunc2(i)
    # [  Thread-1  ] foolstring1, foolnumb1:0
    # [  Thread-3  ] foolstring1, foolnumb1:2
    # [  Thread-4  ] foolstring1, foolnumb1:3
    # [  Thread-2  ] foolstring1, foolnumb1:1
    # [  Thread-6  ] foolstring2, foolnumb2:0
    # [  Thread-5  ] foolstring1, foolnumb1:4
    # [  Thread-6  ] foolstring2, foolnumb2:1
    # [  Thread-6  ] foolstring2, foolnumb2:2
    # [  Thread-6  ] foolstring2, foolnumb2:3
    # [  Thread-6  ] foolstring2, foolnumb2:4
    # >>>
    # >>> # 通过上面的代码执行就很容易发现
    # >>> # pool2 装饰后的函数频率、线程数和 pool1 的不一样
    # >>> # 你可能某几个函数要用一个组，某几个函数用另一组
    # >>> # 分组功能可以更加灵活地使用线程池
    # >>>
    #==============================================================
    '''

    _monitor = None       # 监视主线程是否在运行的线程
    _monitor_run_num = {} # 用判断队列是否为空监视线程是否执行完毕
    
    # 默认0号作为全局函数队列
    _pool_queue = {}
    _pool_func_num = {}

    def __init__(self,pool_num=None,gqueue='v',log=True,monitor=True):
        '''
        #==============================================================
        # **kw
        #     :pool_num  伺服线程数量
        #     :gqueue    全局队列表的index，默认0，建议用数字标识
        #     :log       print函数的输出时是否加入线程名作前缀
        #==============================================================
        '''

        # 让配置在 toggle 函数执行后的装饰行为都变成只能手动配置 log_flag
        if log_flag._decorator_toggle:
            log_flag._vlog = log

        # 默认用的是全局队列
        if gqueue not in self._pool_queue:
            self._pool_queue[gqueue] = queue.Queue()
        self._pool = self._pool_queue[gqueue]
        
        # 默认将 print 函数进行monkey patch
        patch_print()

        # 新线程，监视主线程执行情况，一旦停止就向线程队列注入相应数量的停止标记
        # 因为该线程池的原理就是让主线程变成派发函数的进程，执行到尾部自然就代表
        # 分配的任务已经分配完了，这时就可以注入停止标记让线程执行完就赶紧结束掉
        # 防止在命令行下控制权不交还的情况。
        if monitor and not self._monitor:
            self.main_monitor()
        else:
            self._monitor = "close"

        # 在函数执行前put进该组队列，在函数执行完毕后get该组队列
        # 对每组函数分配进行管理，实现函数执行完毕的挂钩
        if gqueue not in self._monitor_run_num:
            self._monitor_run_num[gqueue] = queue.Queue()

        # 智能选择线程数量
        num = self._auto_pool_num(pool_num)

        # 这里考虑的是控制伺服线程数量，相同的gqueue以最后一个人为定义的线程池数为基准
        if gqueue not in self._pool_func_num:
            self._pool_func_num[gqueue] = num
            self._run(num,gqueue)
        else:
            # 是以最后一个主动设置的线程池数为基准
            # 所以要排除不设置的情况
            if pool_num is not None:
                self.change_thread_num(num,gqueue)

    def __call__(self,func):
        '''
        #==============================================================
        # 类装饰器入口
        #==============================================================
        '''
        orig_func[func.__name__] = func
        @functools.wraps(func)
        def _run_threads(*args,**kw):
            # 将函数以及参数包装进 queue
            self._pool.put((func,args,kw))
        return _run_threads

    @classmethod
    def change_thread_num(self,num,gqueue='v'):
        '''
        #==============================================================
        # 通过组名字，用来修改线程数量的函数，默认修改gqueue='v'的组
        # 是静态函数，你可以直接用 vthread.self.change_thread_num(3)修改
        # 就是简单的多退少补，用来动态修改伺服线程数量的。
        #
        # 因为原理是向线程队列注入停止标记，线程执行和线程接收停止信号是互斥安全的
        # 也是在设计初对任务执行完整性的一种考虑
        #==============================================================
        '''
        if gqueue in self._pool_func_num:
            x = self._pool_func_num[gqueue] - num
            # 当前线程数少于最后一次定义的数量时候会增加伺服线程
            # 多了则会杀掉多余线程
            if x < 0:
                self._run(abs(x),gqueue)
            if x > 0:
                for _ in range(abs(x)):
                    self._pool_queue[gqueue].put(KillThreadParams)
            self._pool_func_num[gqueue] = num

    @classmethod
    def _run(self,num,gqueue):
        '''
        #==============================================================
        # 运行伺服线程，不指定数量则默认以 cpu 核心数作为伺服线程数量
        # 每个线程都等待任意函数放进队列，然后被线程抓出然后执行
        #==============================================================
        '''
        # 伺服函数
        def _pools_pull():
            ct = current_thread()
            name = ct.getName()
            ct.setName("{}_{}".format(name, gqueue))
            while True:
                v = self._pool_queue[gqueue].get()
                if v == KillThreadParams: return
                try:
                    func,args,kw = v
                    self._monitor_run_num[gqueue].put('V') # 标记线程是否执行完毕
                    func(*args,**kw)
                except BaseException as e:
                    if log_flag._elog:
                        print(traceback.format_exc())
                finally:
                    self._monitor_run_num[gqueue].get('V') # 标记线程是否执行完毕
        # 线程的开启
        for _ in range(num): Thread(target=_pools_pull).start()

    @classmethod
    def main_monitor(self):
        '''
        #==============================================================
        # 对主线程进行监视的函数
        # 一旦主线程执行完毕就会向所有线程池函数队列尾注入停止标记
        # 使所有的线程在执行完任务后都停止下来
        # 对于命令行使用的 python 脚本尤为重要
        # 因为如果所有线程不停止的话，控制权就不会交还给命令窗口
        #
        # 在任意被含有该函数的装饰类装饰的情况下，这个是默认被打开的
        # 可以在装饰时通过设置 monitor 参数是否打开，默认以第一个装饰器设置为准
        #==============================================================
        '''
        def _func():
            while True:
                time.sleep(.25)
                if not main_thread().isAlive() and all(map(lambda i:i.empty(),self._monitor_run_num.values())):
                    self.close_all()
                    break
        if not self._monitor:
            self._monitor = Thread(target=_func,name="MainMonitor")
            self._monitor.start()

    @staticmethod
    def _auto_pool_num(num):
        if not num:
            try:
                from multiprocessing import cpu_count
                num = cpu_count()
            except:
                if log_flag._elog:
                    print("cpu_count error. use default num 4.")
                num = 4
        return num

    @classmethod
    def close_by_gqueue(self,gqueue='v'):
        '''
        #==============================================================
        # 通过组名关闭该组所有的伺服线程
        # 默认关闭gqueue='v'组的所有伺服线程
        #==============================================================
        '''
        self.change_thread_num(0,gqueue)

    @classmethod
    def close_all(self):
        '''
        #==============================================================
        # 关闭所有伺服线程
        #==============================================================
        '''
        for i in self._pool_func_num:
            self.change_thread_num(0,i)

    @classmethod
    def show(self):
        '''
        #==============================================================
        # 简单的打印一下当前的线程池的组数
        # 以及打印每一组线程池的线程数量
        #
        # >>> vthread.show()
        # [ MainThread ] threads group number: 3
        # [ MainThread ] gqueue:0, alive threads number:6
        # [ MainThread ] gqueue:1, alive threads number:5
        # [ MainThread ] gqueue:2, alive threads number:2
        # >>>
        #==============================================================
        '''
        l = len(self._pool_func_num)
        print("threads group number: {}".format(l))
        for i,j in self._pool_func_num.items():
            print("gqueue:{}, alive threads number:{}".format(i, j))

    @classmethod
    def waitall(self):
        while any([not self.check_stop(gqueue) for gqueue in self._monitor_run_num]):
            time.sleep(.25)

    @classmethod
    def wait(self, gqueue='v'):
        '''
        #==============================================================
        # 等待任务结束，以下是实例代码
        #
        # import vthread, time
        # @vthread.pool(6) # 生成默认的 gqueue='v' 组线程池，6个线程
        # def foolfunc1(num):
        #     time.sleep(1)
        #     print("foolstring, test foolnumb {}".format(num))
        # ls = []
        # @vthread.pool(2, gqueue='h') # 生成 gqueue='h' 组线程池，2个线程
        # def foolfunc2(num):
        #     time.sleep(1)
        #     print('123123')
        #     ls.append(num*3/2)
        # for i in range(30): foolfunc1(i)
        # for i in range(30): foolfunc2(i)
        # vthread.pool.wait() # 等待默认的 gqueue='v' 组线程池全部停止再执行后面内容
        # vthread.pool.wait(gqueue='h') # 等待默认的 gqueue='v' 组线程池全部停止再执行后面内容
        # print('ls:{}'.format(ls))
        # print('end')
        #==============================================================
        '''
        while not self.check_stop(gqueue):
            time.sleep(.25)

    @classmethod
    def check_stop(self, gqueue='v'):
        '''
        #==============================================================
        # 该函数数用于一边生产一边消费的代码中会很方便，扩展成多消费者也很容易
        # 下面是示例代码
        #
        # import time, random, queue
        # from vthread import pool, lock
        # ls = queue.Queue()
        # producer = 'pr'
        # consumer = 'co'
        # @pool(6, gqueue=producer)
        # def creater(num):
        #     time.sleep(random.random()) # 随机睡眠 0.0 ~ 1.0 秒
        #     with lock:
        #         print("数据进入队列: {}".format(num))
        #         ls.put(num)
        # @pool(1, gqueue=consumer)
        # def coster():
        #     # 这里之所以使用 check_stop 是因为，这里需要边生产边消费
        #     while not pool.check_stop(gqueue=producer):
        #         time.sleep(random.random()) # 随机睡眠 2.0 ~ 3.0 秒
        #         pp = [ls.get() for _ in range(ls.qsize())]
        #         print('当前消费的列表 list: {}'.format(pp))
        # for i in range(30): creater(i)
        # coster()
        # pool.wait(gqueue=producer) # 等待默认的 gqueue=producer 组线程池全部停止再执行后面内容
        # pool.wait(gqueue=consumer) # 等待默认的 gqueue=consumer 组线程池全部停止再执行后面内容
        # print('当生产和消费的任务池数据都结束后，这里才会打印')
        # print('ls:{}'.format(ls.qsize()))
        # print('end')
        #==============================================================
        '''
        return not (self._monitor_run_num[gqueue].qsize() or self._pool_queue[gqueue].qsize())



def atom(func):
    '''
    #==============================================================
    # 对任意函数进行原子包装（加锁）
    #==============================================================
    '''
    def _atom(*arg,**kw):
        lock.acquire()
        v = func(*arg,**kw)
        lock.release()
        return v
    return _atom

def patch_print():
    '''
    #==============================================================
    # print 补丁函数
    #
    # monkey patch 式的修改
    # 对python内建 print 函数进行加锁
    # 使其在调试阶段能更方便使用
    #==============================================================
    '''
    builtins.print = _new_print

def unpatch_all(can_be_repatch=False):
    '''
    #==============================================================
    # 去补丁函数
    # :can_be_repatch=False
    #   因为设计是在每次装饰时就会默认patch一次
    #   卸载后不可被重新patch的参数添加就是为了
    #   可以使得在头部执行这个函数后后面的装饰都不会再patch
    #==============================================================
    '''
    global _new_print,_org_print
    builtins.print = _org_print
    if not can_be_repatch:
        _new_print = builtins.print


# 函数
funcs = ["thread",
         "pool",
         "atom",
         "patch_print",
         "toggle",
         "unpatch_all"]

# 全局参
values = ["orig_func",
          "lock"]


__all__ = funcs + values