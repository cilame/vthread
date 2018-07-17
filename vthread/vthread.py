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
        name = f"[{name.center(13)}]"
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
    # >>> @vthread.vthread(3) # 默认参数:join=False,log=True
    # ... def foolfunc():
    # ...     print("foolstring")
    # >>> 
    # >>> foolfunc() # 一次执行开启三个线程执行相同函数
    # [  Thread-1  ]: foolstring
    # [  Thread-2  ]: foolstring
    # [  Thread-3  ]: foolstring
    # >>>
    #==============================================================
    '''
    def __init__(self,num,join=False,log=True):
        '''
        #==============================================================
        # *args
        #     :num   线程数量
        # **kw
        #     :join  多线程是否join
        #     :log   print函数的输出时是否加入线程名作前缀
        #==============================================================
        '''
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
                            print(" - stop_by_error - ",e)
                p.append(Thread(target=_func))
            for i in p: i.start()
            if self.join:
                for i in p: i.join()
        return _run_threads


import queue

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
    # >>> # 默认参数:pool_num=None,join=False,log=True,gqueue=0
    # >>> # pool_num不选时就自动选 cpu 核心数
    # >>> # 就是说，装饰方法还可以更简化为 @vthread.pool()
    # >>> # join参数不建议在主线程内打开。
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
    join = False

    def __init__(self,pool_num=None,gqueue=0,join=False,log=True,monitor=True):
        '''
        #==============================================================
        # **kw
        #     :pool_num  伺服线程数量
        #     :gqueue    全局队列表的index，默认0，建议用数字标识
        #     :join      多线程是否join
        #     :log       print函数的输出时是否加入线程名作前缀
        #==============================================================
        '''
        self.join = join

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
    def change_thread_num(self,num,gqueue=0):
        '''
        #==============================================================
        # 通过组名字，用来修改线程数量的函数，默认修改gqueue=0的组
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
            ct.setName(name+"_%d"%gqueue)
            while True:
                v = self._pool_queue[gqueue].get()
                if v == KillThreadParams: return
                try:
                    func,args,kw = v
                    self._monitor_run_num[gqueue].put('V') # 标记线程是否执行完毕
                    func(*args,**kw)
                except BaseException as e:
                    if log_flag._elog:
                        print(" - thread stop_by_error - ",e)
                    break
                finally:
                    self._monitor_run_num[gqueue].get('V') # 标记线程是否执行完毕
        # 线程的开启
        v = []
        for _ in range(num):
            v.append(Thread(target=_pools_pull))
        for i in v: i.start()
        if self.join:
            for i in v: i.join()

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
                import time
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
    def close_by_gqueue(self,gqueue=0):
        '''
        #==============================================================
        # 通过组名关闭该组所有的伺服线程
        # 默认关闭gqueue=0组的所有伺服线程
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
        print(f"threads group number: {l}")
        for i,j in self._pool_func_num.items():
            print(f"gqueue:{i}, alive threads number:{j}")




def atom(func):
    '''
    #==============================================================
    # 对任意函数进行原子包装（加锁）
    #==============================================================
    '''
    def _atom(*arg,**kw):
        lock.acquire()
        func(*arg,**kw)
        lock.release()
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












