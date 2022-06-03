import textwrap

import setuptools

long_description = """
[Libcloud](https://libcloud.apache.org/) driver for provdier clodo.ru.

For all available methods, see [README at github](https://github.com/thebits/libcloud-clodoru).
"""


setuptools.setup(
    name="libcloudclodoru",
    version="0.0.2",
    author="Sergey Mezentsev",
    author_email="thebits@yandex.ru",
    description="Libcloud driver for provdier clodo.ru",
    license="UNLICENSE",
    long_description=textwrap.dedent(long_description),
    long_description_content_type="text/markdown",
    url="https://github.com/thebits/libcloud-clodoru",
    install_requires=["apache-libcloud>=3.0.0"],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    classifiers=[
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Systems Administration",
    ],
)
