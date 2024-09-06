from setuptools import setup, find_packages

setup(
	name="AeroViz",
    version="0.1.5",
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
	install_requires=[
		"pandas",
		"numpy",
		"matplotlib",
		"seaborn",
		"scipy",
		"scikit-learn",
		"windrose",
		"tabulate"
		# Add any other dependencies here
	],
	packages=find_packages(),
	include_package_data=True
)
