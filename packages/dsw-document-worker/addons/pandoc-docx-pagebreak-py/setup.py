from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name="pandoc-docx-pagebreak",
    description="Pandoc filter for docx output to insert pagebreak at will",  # Required
    url="https://github.com/pandocker/pandoc-docx-pagebreak-py",  # Original repository
    author="Kazuki Yamamoto, pandocker",
    author_email="k.yamamoto.08136891@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="pandoc filter docx",
    py_modules=["docx_pagebreak"],
    install_requires=[
        "panflute==2.3.1",
    ],
    entry_points={
        "console_scripts": [
            "pandoc-docx-pagebreakpy=docx_pagebreak:main",
        ],
    },
)
