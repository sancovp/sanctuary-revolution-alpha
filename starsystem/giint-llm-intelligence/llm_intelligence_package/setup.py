from setuptools import setup, find_packages

setup(
    name="giint-llm-intelligence",
    version="0.1.7",
    description="GIINT - General Intuitive Intelligence for Neural Transformers: Multi-fire cognitive architecture",
    author="Isaac",
    packages=find_packages(),
    install_requires=[
        "fastmcp>=2.12.2",
        "pathlib",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "llm-intelligence-server=llm_intelligence.mcp_server:main",
        ],
    },
)