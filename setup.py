from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="AeroViz",
    version="0.1.7",
    author="alex",
    author_email="alex870521@gmail.com",
    description="Aerosol science",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",

    url="https://github.com/Alex870521/AeroViz",
    python_requires=">=3.12",

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    # Specify your project's dependencies
    install_requires=requirements,
    packages=find_packages(),
    include_package_data=True
)
