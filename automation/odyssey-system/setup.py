from setuptools import setup, find_packages

setup(
    name="odyssey",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sdna",
        "neo4j",
    ],
)
