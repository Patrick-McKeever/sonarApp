from setuptools import setup

setup(
    name = 'sonarApp',
    version = '1.0.9',
    author = 'Patrick McKeever III',
    author_email = 'patrick.mckeever@protonmail.com',
    install_requires = [
        'kivy',
        'kivymd',
        'scapy',
        'netifaces',
        'ipaddress',
        'mac-vendor-lookup',
        'elevate',
        'screeninfo',
        'pygame',
        'sox'
    ],
    packages = ["sonar"],
    entry_points = {
        'console_scripts': ['sonarApp=sonar.main:main']
    }
)