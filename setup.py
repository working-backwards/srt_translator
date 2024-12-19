from setuptools import setup, find_packages

setup(
    name='srt_translator',  # Name of your project
    version='0.1.0',  # Version number
    packages=find_packages(),  # Automatically find packages in your project
    install_requires=[
        'openai',  # Add your dependencies here
        'python-dotenv',
    ],
    include_package_data=True,  # Include non-Python files specified in MANIFEST.in
    entry_points={
        'console_scripts': [
            'srt-translator=main:batch_translate_srt_files',  # Optional: Command-line entry point
        ],
    },
    description='A tool for batch-translating SRT subtitle files using OpenAI models.',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/srt_translator',  # Replace with your repo URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  # Specify minimum Python version
)
