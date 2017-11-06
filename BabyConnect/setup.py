# Installer for the BabyConnect Package.

from distutils.core import setup
from textwrap import dedent

pkgMainDir = 'src/BabyConnect'
webDir = 'src/BabyConnect/Web'
sqsDir = 'src/BabyConnect/Sqs'

setup(
    name='BabyConnect',
    description='Baby Connect Sqs Interface',
    long_description=dedent('''
    This package is a tool to allow the monitoring of an Amazon Sqs Messaging queue
    for BabyConnect logs and logging them into the Baby Connect website using
    a headless selenium web browser.'''),
    author='Nate Bazar',
    packages=['BabyConnect', 'BabyConnect.Web', 'BabyConnect.Sqs'],
    package_dir={
        'BabyConnect': pkgMainDir,
        'BabyConnect.Web': webDir,
        'BabyConnect.Sqs': sqsDir,
        },
    scripts=['src/BabyConnect-Service.py'],
    requires=['selenium', 'pyvirtualdisplay', 'boto3'],
    version='0.0.1',
    url='https://github.com/bloominonion/BabyConnect'
    )