from setuptools import setup

setup(
    name='knitpy',
    version='0.1.0',
    description='Elegant, flexible and fast dynamic report generation with python',
    #long_description=open('README').read(),
    author='Jan Schulz',
    author_email='jasc@gmx.net',
    url='https://github.com/janschulz/knitpy/issues',
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Utilities'
    ],
    packages=[
        'knitpy'
    ],
    entry_points ={
        'console_scripts': [
            'knitpy = knitpy.knitpyapp:launch_new_instance'
        ]
    },
    install_requires = [
        'IPython>=3.0'
    ]
)