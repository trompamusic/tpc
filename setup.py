from setuptools import setup

setup(
    name='tpl',
    version='1.0',
    packages=['tpl'],
    url='https://github.com/trompamusic/tpc',
    license='Apache 2.0',
    author='aggelos',
    author_email='aggelos.gkiokas@upf.edu',
    description='TROMPA Processing Library',
    install_requires=open("requirements.txt").read().split(),
)
