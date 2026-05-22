from setuptools import setup, find_namespace_packages

VERSION = "2.2.1"
DESCRIPTION = "Class Wrapper for sqlalchemy, pandas and mongo"
LONG_DESCRIPTION = ""
# install_requires = open("requirements.txt").read().strip().split("\n")
# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="DataEngine",
    version=VERSION,
    author="tlibs",
    author_email="<youremail@email.com>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_namespace_packages(where='src'),
    package_dir={"": "src"},
    install_requires=[
        "dnspython>=2.6.1",
        "greenlet>=3.0.3",
        "numpy>=1.26.4",
        "pandas>=2.2.1,<3.0.0",
        "psycopg2>=2.9.9,<3.0.0",
        "pymongo>=4.6.2,<5.0.0",
        "pymssql>=2.2.11,<3.0.0",
        "pyodbc>=5.1.0,<6.0.0",
        "python-dateutil>=2.9.0.post0",
        "python-dotenv>=1.0.1",
        "pytz>=2024.1",
        "six>=1.16.0",
        "SQLAlchemy>=2.0.29,<3.0.0",
        "typing_extensions>=4.10.0",
        "tzdata>=2024.1",
    ],
    python_requires=">=3.10",
    keywords=["python", "sqlalchemy", "pandas", "mongo"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
    ],
)


#pip install -U git+https://consumers-checkbook@dev.azure.com/consumers-checkbook/DataEngine/_git/DataEngine@master
