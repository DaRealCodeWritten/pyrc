from setuptools import setup

setup(
    name="pyrc",
    version="1.0.0",
    description="An asynchronous, event-driven IRC client library for Python",
    author="Emma Lysne",
    author_email="ytcodew@gmail.com",
    packages=["pyrc"],
    install_requires=["wheel", "pysasl"],
)
