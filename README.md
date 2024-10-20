# pytest-zephyr-scale-integration

![PyPI](https://img.shields.io/pypi/v/pytest-zephyr-scale-integration)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-brightgreen.svg)

`pytest-zephyr-scale-integration` is a library for integrating `pytest` with Jira Zephyr (Adaptavist\TM4J).
It allows you to automatically create test cycles in Zephyr, run tests and update their statuses in Jira.

## Features

- Automatic creation of test cycles in Zephyr (with the ability to create a folder or add to an existing one).
- Update test statuses in Jira Zephyr.
- Support for parameterized tests.
- Flexible configuration via `.env` file.

## Installation

You can install the library via `pip`:
```bash
pip install pytest_zephyr_scale_integration
```

## Launch
1. Create a `.env` file and fill it with fields
```commandline
# JIRA configuration
JIRA_PROJECT_ID=12345 # project id, can be found by calling `GET /rest/tests/1.0/project`
JIRA_URL='https://your-jira-instance.atlassian.net'
FOLDER_NAME='Regress v1.0.0'
```
2. Tests should be named by the Jira Zephyr test case key, for example, `"test_T123"`.
3. When running autotests via `pyest`, you need to specify additional parameters: <br>
`--zephyr` - optional. Enables the integration process. After passing the autotests, a test cycle will be automatically
created. <br>
`--jira_token` - the token of the TUZ that has an email configured. Mandatory field if `--zephyr`.

`--zephyr_test_run_name` - optional. The name of the test cycle, by default - "Test Run Cycle". <br>
For example, <br>
```pytest --zephyr --zephyr_test_run_name="Regress v.1.1.0"```

## Logic for creating a test cycle
- If FOLDER_NAME in `.env` is empty, then the test cycle with passed tests will be created in the root folder.
- If FOLDER_NAME in `.env` is filled, then:
- If the specified folder already exists, the test cycle will be created in it.
- If the specified folder does not exist, it will be automatically created in the root and the created test cycle will be located in it.

## Logic for setting test case statuses in Jira Zephyr
All test cases are assigned the corresponding pytest statuses in Jira Zephyr. <br>

If a parameterized test is written in Jira Zephyr, then in the test
cycle it will look like a single test with test scripts in a quantity equal to the set of parameters in the test case. Each such set is called `Test Script`. <br>
When automating such a test case, you need to do parameterization in the code as well. The sets in `pyest` should go in the same order as in Zephyr, since `pyest` executes them in order.

In the test cycle, the results of passing one parameterized test are displayed in the steps of `Test Script`, so that it is possible to clearly determine which of all the suites failed.
The logic for setting the statuses of the steps of parameterized tests:
- If the suite is passed successfully, then all the steps of `Test Script` are PASS
- If the suite fails, then all the steps of `Test Script` are FAIL.

There is no logic for matching actions in `pytest' and steps in Zephyr.

The logic for setting statuses and test cases:
- If all suites are passed successfully, then the test case is PASS
- If at least one suite fails, then the test case is marked as FAIL.
