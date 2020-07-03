import time
import vthread

@vthread.pool(5)
def foolfunc_():
    time.sleep(1)
    print(123)
for i in range(10): foolfunc_()
vthread.pool.wait() # 等待默认的gqueue=0分组线程执行完毕再继续后面的代码
print('end.')