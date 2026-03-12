from setuptools import setup, find_packages

setup(
    name="hyperon-mcp",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "hyperon_mcp.core": ["*.metta"],
    },
    install_requires=[
        "hyperon>=0.2.8",
        "fastmcp>=0.3.0",
        "pydantic>=2.0.0",
        "metta-motto>=0.0.12",
        "snet.sdk>=5.0.0"
    ],
    extras_require={
        "heaven": ["heaven-framework"],
    },
)
