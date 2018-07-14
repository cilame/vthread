from __future__ import print_function  
from setuptools import setup, find_packages  
import sys  
  
setup(  
    name="vthread",
    version="0.0.8",
    author="vilame",
    author_email="opaquism@hotmail.com",
    description="the best threadpool pack.",
    long_description="""
#### You can implement thread pools by adding a single line of code without changing the order of any previous code.
- Example
```python
import vthread

@vthread.pool(3) # Create three thread pools
def crawl(i):
    import time;time.sleep(1) # Simulation time consuming
    print("crawl_url:",i)

urls = ["http://url1",
        "http://url2",
        "http://url3",
        "http://url4"]

for u in urls:
    crawl(u) # This function becomes a function that adds the original function to the thread pool.
```
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
