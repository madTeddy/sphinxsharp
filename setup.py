from setuptools import setup
from os import path
from glob import glob

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name = 'sphinxsharp',
  packages = ['sphinxsharp'],
  include_package_data=True,
  version = '1.0.1',
  license='MIT',
  description = 'CSharp (C#) domain for sphinx.',
  long_description=long_description,
  author = 'Andrey Mignevich',
  author_email = 'andrey.mignevich@gmail.com',
  url = 'https://github.com/madTeddy/sphinxsharp',
  download_url = 'https://github.com/madTeddy/sphinxsharp/archive/v1.0.0.tar.gz',
  keywords = ['Sphinx','Domain','CSharp','C#','Sphinxsharp'],
  install_requires=[
          'docutils',
          'sphinx',
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7'
  ],
)