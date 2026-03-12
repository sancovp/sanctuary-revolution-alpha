"""
CANOPY - Master Schedule Orchestration
MCP server for managing AI+Human collaboration scheduling
"""
from setuptools import setup, find_packages

setup(
    name='canopy-mcp',
    version='0.1.0',
    description='CANOPY - Master schedule orchestration for compound intelligence',
    author='Isaac',
    packages=find_packages(),
    install_requires=[
        'fastmcp>=2.0.0',
    ],
    entry_points={
        'console_scripts': [
            'canopy-server=canopy.canopy_mcp:main',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='mcp ai scheduling collaboration canopy starsystem',
)
