from setuptools import find_packages, setup

setup(
    name="zephyr_with_pytest",
    version="1.0.0",
    description="A library for integrating Jira Zephyr Scale with pytest",
    packages=find_packages(),
    entry_points={
        'pytest11': [
            'pytest_zephyr_integration = zephyr_with_pytest.conftest',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
install_requires=[
    'requests',
    'requests_toolbelt',
],
    python_requires='>=3.6',
)
