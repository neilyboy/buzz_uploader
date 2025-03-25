#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="buzz-uploader",
    version="0.2.0",
    author="Neil",
    author_email="user@example.com",
    description="A terminal-based file uploader for BuzzHeavier with a slick TUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/buzz-uploader",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "buzz_uploader": ["app.css"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Utilities",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
        "Intended Audience :: End Users/Desktop",
    ],
    python_requires=">=3.7",
    install_requires=[
        "textual>=0.27.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "clipboard": ["pyperclip>=1.8.2"],
        "dev": [
            "black>=23.0.0",
            "isort>=5.12.0",
            "pylint>=2.17.0",
            "pyperclip>=1.8.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "buzz-uploader=buzz_uploader.__main__:main",
        ],
    },
)
