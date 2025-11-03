from setuptools import setup, find_packages # pyright: ignore[reportMissingModuleSource]

setup(
    name="mct3",
    version="2.5.4",
    author="MichtOo",
    description="CLI tool for audio and file utilities.",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.3",
        "mutagen>=1.47.0",
        "requests>=2.32.5",
        "psutil>=7.1.3"
    ],
    entry_points={
        "console_scripts": [
            "mct3=mct3.main:cli",
        ],
    },
    include_package_data=True,
)