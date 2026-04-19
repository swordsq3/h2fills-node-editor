from setuptools import setup, find_packages
import re


def get_version():
    with open("__init__.py", "r", encoding="utf-8") as f:
        return re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
            f.read(), re.MULTILINE,
        ).group(1)


setup(
    name="h2fills",
    version=get_version(),
    packages=find_packages(),
    package_data={
        "": ["res/fonts/*", "res/icons/*", "scenarios/*.json"],
    },
    include_package_data=True,
    description="Hydrogen Filling Simulation — Simulink-style node editor",
    python_requires=">=3.10",
    install_requires=[
        "dearpygui==1.11.1",
        "numpy>=1.24",
        "fpdf2>=2.7.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "h2fills=h2sim_main:main",
        ],
    },
)
