from setuptools import setup, find_packages

setup(
    name="sophra-client",
    version="0.1.0",
    description="Open-Source Edge Client for Sophra Enterprise Agent Orchestration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Sophra OSS",
    url="https://github.com/sophra/sophra-client-oss",
    packages=find_packages(),
    install_requires=[
        # Add minimal required packages here
    ],
    entry_points={
        "console_scripts": [
            "sophra=sophra_client.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
