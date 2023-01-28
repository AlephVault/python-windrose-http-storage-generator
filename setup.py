from setuptools import setup, find_namespace_packages

setup(
    name='gamemeanmachine-windrose-http-mongodb-storage-generator',
    version='0.0.4',
    packages=find_namespace_packages(),
    url='https://gitlab.com/gamemeanmachine/python-windrose-http-storage-generator',
    license='MIT',
    scripts=['bin/windrose-http-mongo-storage-generate'],
    author='luismasuelli',
    author_email='luismasuelli@hotmail.com',
    description='A generator of production-ready HTTP storage stacks for WindRose/NetRose games',
    install_requires=[
        'alephvault-http-mongodb-storage==0.0.5'
    ]
)
