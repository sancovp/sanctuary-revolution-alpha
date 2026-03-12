#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="starsystem_reward_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "heaven-framework>=0.1.15",  # For RegistryService
    ],
    python_requires=">=3.8",
    author="Isaac (TWI)",
    description="STARSYSTEM reward and fitness scoring system",
    long_description=open("README.md").read() if __name__ == "__main__" else "",
    long_description_content_type="text/markdown",
)
