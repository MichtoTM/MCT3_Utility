from setuptools import setup, find_packages

setup(
    name="mct3",
    version="2.0.3",
    packages=find_packages(),
    install_requires=[
        "mutagen",
        "click",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'mct3=mct3.main:cli',
        ],
    },
)