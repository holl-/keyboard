from setuptools import setup

long_description = """
Enumerate raw input devices and receive input events with device ID on Windows.

Homepage: https://github.com/holl-/win-raw-in
"""

setup(
    name='win-raw-in',
    version='0.2.1',
    author='Philipp Holl',
    author_email='philipp@mholl.de',
    packages=['winrawin'],
    package_data={'': ['usb.ids']},
    include_package_data=True,
    url='https://github.com/holl-/win-raw-in',
    license='MIT',
    description='Enumerate raw input devices and receive input events with device ID on Windows',
    keywords='keyboard mouse hook raw input',
    long_description=long_description,
    install_requires=['dataclasses'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
