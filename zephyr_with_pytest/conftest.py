from pprint import pprint
import re
from datetime import datetime
import pytest

from .integration import Integration
from .utils import get_or_create_folder


executed_test_keys = [] # list of executed tests (pytest)
full_test_results = {} # dictionary with all tests and statuses (with parametrization)
set_test_results = {} # dictionary with tests and statuses without repetitions (to set the status for a test)
dict_test_statuses = {} # dictionary with statuses for test cases (e.g. {'PASS': 3238, 'FAIL': 3239})
date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Getting results of autotest runs"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        test_nodeid = item.nodeid
        test_key_match = re.search(r"T\d+", test_nodeid)

        if test_key_match:
            potential_key = test_key_match.group(0)

            if potential_key not in executed_test_keys:
                executed_test_keys.append(potential_key)

            # Creating a dictionary with statuses test_key: status_id
            # {'T123': 3238, 'T234': 3239}
            if report.outcome == "passed":
                full_test_results[test_nodeid] = dict_test_statuses.get('PASS')

                # If the test is parameterized, there will be several identical keys.
                # If at least one of them is FAIL, then FAIL.
                if potential_key not in set_test_results:
                    set_test_results[potential_key] = dict_test_statuses.get('PASS')
            else:
                full_test_results[test_nodeid] = dict_test_statuses.get('FAIL')
                set_test_results[potential_key] = dict_test_statuses.get('FAIL')


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Configuration"""

    # date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    zephyr_enabled = config.getoption("--zephyr", default=False)
    zephyr_test_run_name = config.getoption("--zephyr_test_run_name", default=f"Test Cycle {date}")
    jira_token = config.getoption("--jira_token")

    if zephyr_enabled and not jira_token:
        raise ValueError("To integrate with Zephyr, you must pass the --jira_token parameter.")

    # Save values in config for use in pytest_sessionfinish
    config._zephyr_enabled = zephyr_enabled
    config._zephyr_test_run_name = zephyr_test_run_name
    config._jira_token = jira_token

    # if --zephyr flag is set
    if zephyr_enabled:
        integration = Integration(jira_token)
        integration.load_environment_variables()

        # Get test statuses and save them in dict_test_statuses
        status_items = integration.get_test_statuses()
        for status_item in status_items:
            status = status_item.get('name').upper()
            if status not in dict_test_statuses:
                dict_test_statuses[status] = status_item.get('id')

        # Save data in config to use it in other hooks
        config._zephyr_integration = integration
        config._zephyr_test_run_name = zephyr_test_run_name


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    """Wrapper for performing actions before and after the main hook code"""

    yield

    zephyr_enabled = getattr(session.config, "_zephyr_enabled", False)
    zephyr_test_run_name = getattr(session.config, "_zephyr_test_run_name", f"Test Cycle {date}")
    integration = getattr(session.config, "_zephyr_integration", None)

    if zephyr_enabled and integration:
        project_key = integration.get_project_key_by_project_id()
        folder_name = integration.folder_name

        test_run_id = None
        folder_id = None
        if folder_name:
            folders = integration.get_test_run_folders()
            folder_id = get_or_create_folder(integration, folders, folder_name)

        test_run_id = integration.create_test_cycle(zephyr_test_run_name, folder_id)
        print('Test run created:', test_run_id)

        test_case_ids = [integration.get_test_case_id(project_key, test_case_key) for test_case_key in
                         executed_test_keys]
        integration.add_test_cases_to_cycle(test_run_id, test_case_ids)

        # Get a list of tests in a loop with their IDs
        test_run_items = integration.get_test_run_items(test_run_id)

        # In the dictionary with test cases and their statuses, replace the key of the type T123 with ID ["$lastTestResult"]["id"]
        updated_test_results = {}
        for item in test_run_items:
            test_case_key = item["$lastTestResult"]["testCase"]["key"].split('-')[-1]
            if test_case_key in set_test_results:
                updated_test_results[item['$lastTestResult']["id"]] = set_test_results[test_case_key]

        # Updating the status of test cases
        if updated_test_results:
            statuses_to_update = [{"id": k, "testResultStatusId": v} for k, v in updated_test_results.items()]
            integration.set_test_case_statuses(statuses_to_update)

        # Processing parameterized tests
        for test_key in executed_test_keys:
            relevant_results = [result for key, result in full_test_results.items() if test_key in key]
            # print('relevant_results')
            # pprint(relevant_results)

            for item in test_run_items:
                test_case_run_id = item["id"]
                script_results = integration.get_test_script_results(test_run_id, test_case_run_id)

                parameter_set_status = {}
                for script_result in script_results[0]["testScriptResults"]:
                    parameter_set_id = script_result.get('parameterSetId')
                    if parameter_set_id:
                        if parameter_set_id not in parameter_set_status:
                            parameter_set_status[parameter_set_id] = {"status": None, "steps": []}
                        parameter_set_status[parameter_set_id]["steps"].append(script_result['id'])

                sorted_parameter_set_status = dict(sorted(parameter_set_status.items()))
                # print('sorted_parameter_set_status')
                # print(sorted_parameter_set_status)

                for param_id, info in zip(sorted_parameter_set_status.keys(), relevant_results):
                    sorted_parameter_set_status[param_id]["status"] = info

                script_statuses_to_update = []
                for param_id, info in sorted_parameter_set_status.items():
                    for step_id in info["steps"]:
                        script_statuses_to_update.append({
                            "id": step_id,
                            "testResultStatusId": info["status"]
                        })

                # print('script_statuses_to_update')
                # print(script_statuses_to_update)

                if script_statuses_to_update:
                    integration.set_test_script_statuses(script_statuses_to_update)


def pytest_addoption(parser):
    """Custom parameters for running autotests."""
    parser.addoption("--zephyr", action="store_true", help="Enable Zephyr integration")
    parser.addoption("--zephyr_test_run_name", action="store", default=f"Test Cycle {date}",
                     help="Name of the test run cycle")
    parser.addoption("--jira_token", action="store", help="JIRA API token for authentication")
