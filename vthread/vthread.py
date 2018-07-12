'''
#==============================================================
# 更加方便的多线程调用，类装饰器封装，一行代码实现线程池
#
# 注意：
# 装饰器会默认对 print 函数进行 monkey patch
# 会对python自带的 print 函数加锁使 print 带有原子性
# 可以通过执行 vthread.unpatch_all() 解除这个补丁还原 print
# 默认打开 log 让 print 能够输出线程名字
# 可以通过设置 vthread._vlog 为 False 关掉显示线程名功能（不关锁）
#==============================================================
'''
from threading import Thread,Lock,RLock,\
                     current_thread
import builtins

_org_print = print
def _new_print(*arg,**kw):
    lock.acquire()
    if _vlog:
        name = current_thread().getName()
        name = f"[{name.center(12)}]"
        _org_print(name,*arg,**kw)
    else:
        _org_print(*arg,**kw)
    lock.release()


lock = RLock()
_vlog = True
_elog = True

# 所有被装饰的原始函数都会放在这个地方
orig_func = {}

class thread:
    '''
    #==============================================================
    # 普通的多线程装饰
    #
    # >>> import vthread
    # >>>
    # >>> # 对于 foolfunc 动态开启3个线程进行调用
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

        global _vlog
        _vlog = log
        
        # 默认将 print 函数进行monkey patch
        patch_print()

    def __call__(self,func):
        '''
        #==============================================================
        # 类装饰器入口
        #==============================================================
        '''
        orig_func[func.__name__] = func
        def _run_threads(*args,**kw):
            p = []
            for _ in range(self.num):
                # 这里包装一下异常捕捉，防止异常导致的不 join
                def _func():
                    try:
                        func(*args,**kw)
                    except Exception as e:
                        if _elog:
                            print(" - stop_by_error - ",e)
                p.append(Thread(target=_func))
            for i in p: i.start()
            if self.join:
                for i in p: i.join()
        return _run_threads


import queue

# 默认0号作为全局函数队列
_pool_queue = {}
_pool_func_num = {}

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
    # >>> @vthread.pool(5) # 对于 foolfunc 开启5个线程池（pool_num）
    # >>> def foolfunc(num):
    # ...     time.sleep(1)
    # ...     print(f"foolstring, foolnumb:{num}")
    # >>>
    # >>> # 默认参数:pool_num=None,join=False,log=True,gqueue=0
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
    join = False
    def __init__(self,pool_num=None,join=False,log=True,gqueue=0):
        '''
        #==============================================================
        # **kw
        #     :pool_num  伺服线程数量
        #     :join      多线程是否join
        #     :log       print函数的输出时是否加入线程名作前缀
        #     :gqueue    全局队列表的index，默认0，建议用数字标识
        #==============================================================
        '''
        pool.join = join

        global _vlog,_pool_queue,_pool_func_num
        _vlog = log

        # 默认用的是全局队列
        if gqueue not in _pool_queue:
            _pool_queue[gqueue] = queue.Queue()
        self._pool = _pool_queue[gqueue]
        
        # 默认将 print 函数进行monkey patch
        patch_print()

        # 智能选择线程数量
        num = pool._auto_pool_num(pool_num)

        # 这里考虑的是控制伺服线程数量，相同的gqueue以最后一个出现的线程池数为基准
        if gqueue not in _pool_func_num:
            _pool_func_num[gqueue] = num
            pool.run(num,gqueue)
        else:
            # 是以最后一个主动设置的线程池数为基准
            # 所以要排除不设置的情况
            if pool_num is not None:
                pool.change_thread_num(num,gqueue)

    def __call__(self,func):
        '''
        #==============================================================
        # 类装饰器入口
        #==============================================================
        '''
        orig_func[func.__name__] = func
        def _run_threads(*args,**kw):
            # 将函数以及参数包装进 queue
            self._pool.put((func,args,kw))
        return _run_threads


    @staticmethod
    def change_thread_num(num,gqueue=0):
        '''
        #==============================================================
        # 通过组名字，用来修改线程数量的函数，默认修改gqueue=0的组
        # 是静态函数，你可以直接用 vthread.pool.change_thread_num(3,1)修改
        # 就是简单的多退少补，用来动态修改伺服线程数量的。
        #==============================================================
        '''
        global _pool_queue,_pool_func_num
        x = _pool_func_num[gqueue] - num
        # 当前线程数少于最后一次定义的数量时候会增加伺服线程
        # 多了则会杀掉多余线程
        if x < 0:
            pool.run(abs(x),gqueue)
        if x > 0:
            for _ in range(abs(x)):
                _pool_queue[gqueue].put(KillThreadParams)
            _pool_func_num[gqueue] = num

    @staticmethod
    def run(num,gqueue):
        '''
        #==============================================================
        # 运行伺服线程，默认以 cpu 核心数作为伺服线程数量
        # 每个线程都等待任意函数放进队列，然后被线程抓出然后执行
        #==============================================================
        '''
        global _pool_queue,_vlog,_elog
        # 拖池函数
        def _pools_pull():
            while True:
                try:
                    v = _pool_queue[gqueue].get()
                    if v == KillThreadParams:
                        return
                    func,args,kw = v
                    func(*args,**kw)
                except:
                    if _elog:
                        print(" - stop_by_queue - ")
        # 线程的开启
        v = []
        for _ in range(num):
            def _func():
                try:
                    _pools_pull()
                except Exception as e:
                    if _elog:
                        print(" - stop_by_error - ",e)
            v.append(Thread(target=_func))
        for i in v: i.start()
        if pool.join:
            for i in v: i.join()

    @staticmethod
    def _auto_pool_num(num):
        if not num:
            try:
                from multiprocessing import cpu_count
                num = cpu_count()
            except:
                if _elog:
                    print("cpu_count error. use default num 4.")
                num = 4
        return num


def pool_close_by_gqueue(gqueue=0):
    '''
    #==============================================================
    # 通过组名关闭该组所有的伺服线程
    # 默认关闭gqueue=0组的所有伺服线程
    #==============================================================
    '''
    pool.change_thread_num(0,gqueue)

def pool_close_all():
    '''
    #==============================================================
    # 关闭所有伺服线程
    #==============================================================
    '''
    global _pool_func_num
    for i in _pool_func_num:
        pool.change_thread_num(0,i)

def pool_show():
    global _pool_func_num
    l = len(_pool_func_num)
    print(f"threads group number: {l}")
    for i,j in _pool_func_num.items():
        print(f"gqueue:{i}, alive threads number:{j}")


def atom(func):
    '''
    #==============================================================
    # 对任意函数进行原子包装
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

def unpatch_all():
    '''
    #==============================================================
    # 去补丁函数
    #==============================================================
    '''
    builtins.print = _org_print




# 函数
funcs = ["thread",
         "pool",
         "atom",
         "patch_print",
         "unpatch_all",
         "pool_close_by_gqueue",
         "pool_close_all",
         "pool_show"]

# 全局参
values = ["_elog",
          "_vlog",
          "orig_func"]


__all__ = funcs + values












