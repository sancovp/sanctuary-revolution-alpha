"""Setup script for FlightSim MCP."""

from setuptools import setup, find_packages

setup(
    name="flightsim-mcp",
    version="0.1.0",
    description="FlightSim MCP - Systematic subagent delegation via mission brief generation",
    packages=find_packages(),
    install_requires=[
        "fastmcp",
        "pydantic>=2.0.0",
        # heaven-base must be available in environment
    ],
    entry_points={
        "console_scripts": [
            "flightsim-server=flightsim_mcp.flightsim_mcp:main",
        ],
    },
    python_requires=">=3.8",
    author="Isaac and Claude",
    author_email="noreply@anthropic.com",
    url="https://github.com/anthropics/claude-code",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)