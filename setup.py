from __future__ import print_function  
from setuptools import setup, find_packages  
import sys  
  
setup(  
    name="vthread",
    version="0.1.2",
    author="vilame",
    author_email="opaquism@hotmail.com",
    description="the best threadpool pack.",
    long_description="""
You can implement thread pools by adding a single line of code without changing the order of any previous code.
===============================================================================================================

.. code-block:: python

    import vthread
    
    @vthread.pool(3) # just use this line to make pool, Create a threadpool with three threads
    def crawl(i):
        import time;time.sleep(1) # Simulation time consuming
        print("crawl_url:",i)
    
    urls = ["http://url1",
            "http://url2",
            "http://url3",
            "http://url4"]
    
    for u in urls:
        crawl(u) # This function becomes a function that adds the original function to the thread pool.


It provides a method for grouping the thread pool
=================================================

.. code-block:: python

    import vthread
    pool_1 = vthread.pool(5,gqueue=1) # open a threadpool with 5 threads named 1
    pool_2 = vthread.pool(2,gqueue=2) # open a threadpool with 2 threads named 2
    
    @pool_1
    def foolfunc1(num):
        time.sleep(1)
        print(f"foolstring1, test3 foolnumb1:{num}")
    
    @pool_2 
    def foolfunc2(num):
        time.sleep(1)
        print(f"foolstring2, test3 foolnumb2:{num}")

    @pool_2 
    def foolfunc3(num):
        time.sleep(1)
        print(f"foolstring3, test3 foolnumb3:{num}")
    
    for i in range(10): foolfunc1(i)
    for i in range(4): foolfunc2(i) 
    for i in range(2): foolfunc3(i)
    # default gqueue is 0
""",
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/cilame/vthread",
    packages=['vthread'],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ]
)  
