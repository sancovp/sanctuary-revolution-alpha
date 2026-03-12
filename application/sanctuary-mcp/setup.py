"""
Sanctuary System MCP - Mythological wrapper and Sanctuary Degree scoring
"""
from setuptools import setup, find_packages

setup(
    name='sanctuary-system-mcp',
    version='0.3.0',
    description='Sanctuary System - Narrative wrapper and scoring for STARSYSTEM compound intelligence',
    author='Isaac',
    license='GNOSYS Personal Builder License (GPBL) v1.0',
    packages=find_packages(),
    install_requires=[
        'fastmcp>=2.0.0',
        'heaven-framework>=0.1.0',
    ],
    entry_points={
        'console_scripts': [
            'sanctuary-server=sanctuary_system.mcp_server:main',
        ],
    },
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='mcp ai sanctuary starsystem narrative mythology',
)
