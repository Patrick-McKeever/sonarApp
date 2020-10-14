from setuptools import setup

setup(
    name = 'sonarApp',
    version = '1.0.9',
    author = 'Patrick McKeever III',
    author_email = 'patrick.mckeever@protonmail.com',
    install_requires = [
        'kivy',
        'scapy',
        'netifaces',
        'ipaddress',
        'mac-vendor-lookup',
        'elevate',
        'screeninfo',
        'pygame',
        'sox'
    ],
    dependency_links = [
        'https://github.com/kivymd/KivyMD/tarball/master#egg=package-1.0'
    ],
    packages = ['sonar'],
    entry_points = {
        'console_scripts': ['sonarApp=sonar.main:main']
    }
)
