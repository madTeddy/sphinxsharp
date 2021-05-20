from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name = 'sphinxsharp',
  packages = ['sphinxsharp'],
  include_package_data=True,
  version = '1.0.2',
  license='MIT',
  description = 'CSharp (C#) domain for sphinx.',
  long_description=long_description,
  author = 'Andrey Mignevich',
  author_email = 'andrey.mignevich@gmail.com',
  url = 'https://github.com/madTeddy/sphinxsharp',
  download_url = 'https://github.com/madTeddy/sphinxsharp/archive/refs/tags/v1.0.2.tar.gz',
  keywords = ['Documentation','Sphinx','Domain','CSharp','C#','Sphinxsharp'],
  install_requires=[
          'docutils',
          'sphinx',
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Documentation :: Sphinx',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9'
  ]
)