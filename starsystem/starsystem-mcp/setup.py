"""
STARSYSTEM - Complete Compound Intelligence Ecosystem
Master metapackage and help system for STARSYSTEM
"""
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='starsystem',
    version='1.0.0',
    description='STARSYSTEM - Complete compound intelligence ecosystem with master help system',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Isaac',
    license='GNOSYS Personal Builder License (GPBL) v1.0',
    url='https://github.com/sancovp/starsystem',
    packages=find_packages(),
    install_requires=[
        # MCP dependency for the server
        'fastmcp>=2.0.0',

        # Optional: Registry support (for help system)
        # 'heaven-framework>=0.1.14',
    ],
    entry_points={
        'console_scripts': [
            'starsystem-server=starsystem.starsystem_mcp:main',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='ai llm mcp compound-intelligence starsystem heaven starlog giint carton',
)