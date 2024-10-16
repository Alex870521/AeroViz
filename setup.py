from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="AeroViz",
    version="0.1.9.2",
    author="alex",
    author_email="alex870521@gmail.com",
    description="Aerosol science",
    long_description=long_description,
    long_description_content_type="text/markdown",

    url="https://github.com/Alex870521/AeroViz",
    python_requires=">=3.12",

    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,

    # 修正 extras_require 格式
    extras_require={
        'test': [
            'pytest>=7.0.0',
        ]
    },

    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)