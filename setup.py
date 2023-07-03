from setuptools import setup, find_namespace_packages

setup(
    name='alephvault-windrose-http-mongodb-storage-generator',
    version='0.0.8',
    packages=find_namespace_packages(),
    url='https://github.com/AlephVault/python-windrose-http-storage-generator',
    license='MIT',
    scripts=['bin/windrose-http-mongo-storage-generate'],
    author='luismasuelli',
    author_email='luismasuelli@hotmail.com',
    description='A generator of production-ready HTTP storage stacks for WindRose/NetRose games',
    install_requires=[
        'alephvault-http-mongodb-storage==0.0.10'
    ]
)
