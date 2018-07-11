'''
#==============================================================
# 更加方便的多线程调用，类装饰器封装，使用方法见下方说明
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

class thread:
    '''
    #==============================================================
    # 普通的多线程装饰
    #
    # >>> import vthread
    # >>>
    # >>> # 对于 foolfunc 动态开启N个线程进行调用
    # >>> # 默认对 print 函数进行 monkey patch
    # >>> # 对 print 加锁使 print 函数都带有原子性
    # >>> # 默认打开 log 让 print 能够输出线程名字
    # >>>
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
    #
    # >>> import vthread
    # >>>
    # >>> # 下面的函数意义为，对于 foolfunc 开启4个线程（pool_num）
    # >>> # 每次使用 foolfunc 函数时将该函数的执行传入队列3次
    # >>> # 交给伺服线程执行3次
    # >>>
    # >>> @vthread.pool(3,4) 
    # ... def foolfunc():
    # ...     print("foolstring")
    # >>> 
    # >>> # 默认参数:pool_num=None,join=False,log=True,gqueue=0
    # >>> # pool_num不选时就自动选 cpu 核心数
    # >>> # 就是说，装饰方法还可以更简化为 @vthread.pool(3)
    # >>> 
    # >>> foolfunc() # 此方法被装饰执行传入伺服队列，待伺服函数执行
    # [  Thread-1  ]: foolstring
    # [  Thread-2  ]: foolstring
    # [  Thread-3  ]: foolstring
    # >>>
    #==============================================================
    # 好处就是对代码入侵较小，例如
    #
    # >>> import vthread
    # >>> import time
    # >>>
    # >>> # 只需要加下面这一行就可以将普通迭代执行变成线程池多线程
    # >>> @vthread.pool(1,5)
    # >>> def foolfunc(num):
    # ...     time.sleep(1)
    # ...     print(f"foolstring, foolnumb:{num}")
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
    # >>> pool1 = vthread.pool(1,5,gqueue=1)
    # >>> pool2 = vthread.pool(1,1,gqueue=2)
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
    # >>> # 分组功能可以更加灵活地使用线程
    # >>>
    #==============================================================
    '''
    join = False
    def __init__(self,num,pool_num=None,join=False,log=True,gqueue=0):
        '''
        #==============================================================
        # *args
        #     :num       线程数量
        # **kw
        #     :pool_num  伺服线程数量
        #     :join      多线程是否join
        #     :log       print函数的输出时是否加入线程名作前缀
        #     :gqueue    全局队列表的index，默认0，建议用数字标识
        #==============================================================
        '''
        self.num  = num
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
                x = _pool_func_num[gqueue] - num
                # 当前线程数少于最后一次定义的数量时候会增加伺服线程
                # 多了则会杀掉多余线程
                if x < 0:
                    pool.run(abs(x),gqueue)
                if x > 0:
                    for _ in range(abs(x)):
                        self._pool.put(KillThreadParams)



    def __call__(self,func):
        '''
        #==============================================================
        # 类装饰器入口
        #==============================================================
        '''
        def _run_threads(*args,**kw):
            for _ in range(self.num):
                # 将函数以及参数包装进 queue
                self._pool.put((func,args,kw))
        return _run_threads

    @staticmethod
    def run(num=None,gqueue=0):
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
                except queue.Empty:
                    if _elog:
                        print(" - stop_by_queue - ")
        # 执行线程的开启
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
    # print 去补丁函数
    #==============================================================
    '''
    builtins.print = _org_print




# 函数
funcs = ["thread",
         "pool",
         "atom",
         "patch_print",
         "unpatch_all"]

# 全局参
values = ["_elog",
          "_vlog"]


__all__ = funcs + values












