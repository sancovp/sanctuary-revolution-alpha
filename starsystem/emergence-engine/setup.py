from setuptools import setup, find_packages

setup(
    name="emergence-engine",
    version="0.1.0",
    description="3-pass systematic thinking methodology for compound intelligence systems",
    packages=find_packages(),
    package_data={
        "": ["*.md"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "emergence-engine-mcp=emergence_engine.mcp_server:main",
        ],
    },
)