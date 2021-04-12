from setuptools import setup

setup(
    name='tpc',
    version='1.0',
    packages=['tpc'],
    url='https://github.com/trompamusic/tpc',
    license='Apache 2.0',
    author='aggelos',
    author_email='aggelos.gkiokas@upf.edu',
    description='TROMPA Processing Component',
    install_requires=open("requirements.txt").read().split(),
)
