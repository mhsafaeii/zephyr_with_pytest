import os
import time
from datetime import datetime
from dotenv import load_dotenv
import requests
from requests import HTTPError
from requests_toolbelt.utils import dump


JIRA_TOKEN = None
JIRA_PROJECT_ID = None
JIRA_URL = None


class Integration:
    def __init__(self, jira_token):
        self.session = requests.Session()
        self.max_retries = 5
        self.retry_delay = 1

        self.JIRA_TOKEN = jira_token
        self.JIRA_PROJECT_ID = None
        self.JIRA_URL = None
        self.folder_name = None


        self.session.headers.update({
            'Authorization': f'Bearer {self.JIRA_TOKEN}',
            'Content-Type': 'application/json'
        })

    def load_environment_variables(self):

        load_dotenv(".env")
        date = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        self.JIRA_PROJECT_ID = int(os.getenv("JIRA_PROJECT_ID"))
        self.JIRA_URL = os.getenv("JIRA_URL")
        self.folder_name = f'Regression {date}'#os.getenv("FOLDER_NAME", None)

        missing_env_vars = [var for var in ["JIRA_TOKEN", "JIRA_PROJECT_ID", "JIRA_URL"] if not getattr(self, var)]
        if missing_env_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_env_vars)}")
        else:
            print(
                f'Variables loaded: {self.JIRA_TOKEN} \t {self.JIRA_PROJECT_ID} \t '
                f'{self.JIRA_URL} \t {self.JIRA_PROJECT_ID}')

    def _send_request_with_retries(self, method, url, **kwargs):

        retries = 0
        while retries < self.max_retries:
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 429:
                retries += 1
                wait_time = self.retry_delay * (2 ** (retries - 1))
                print(f"The limit of the number of messages sent has been exceeded. "
                      f"Waiting {wait_time} seconds before resending...")
                time.sleep(wait_time)
            else:
                response.raise_for_status()
                return response
        raise HTTPError(f"Failed to complete request after {self.max_retries} "
                        f" attempts due to rate limits on sending requests.")

    def get_project_key_by_project_id(self):

        url = f"{self.JIRA_URL}/rest/tests/1.0/project/{self.JIRA_PROJECT_ID}"
        response = self.session.get(url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('key')

    def create_test_cycle(self, cycle_name, folder_id=None):
        test_cycle_statuses = self.get_test_cycle_statuses()
        test_cycle_status_id = None
        for test_cycle_status in test_cycle_statuses:
            if test_cycle_status.get('name').lower() == 'Not Executed':
                test_cycle_status_id = test_cycle_status.get('id')

        url = f"{self.JIRA_URL}/rest/tests/1.0/testrun"
        payload = {
            "name": cycle_name,
            "projectId": self.JIRA_PROJECT_ID,
            "statusId": test_cycle_status_id if not test_cycle_status_id else test_cycle_statuses[0].get('id')
        }

        if folder_id:
            payload["folderId"] = folder_id

        response = self.session.post(url, json=payload)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('id')

    def create_test_run_folder(self, folder_name):

        url = f"{self.JIRA_URL}/rest/tests/1.0/folder/testrun"
        payload = {
            "name": folder_name,
            "projectId": self.JIRA_PROJECT_ID,
            "index": 0
        }
        response = self._send_request_with_retries('POST', url, json=payload)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('id')

    def get_test_run_folders(self):

        url = f"{self.JIRA_URL}/rest/tests/1.0/project/{self.JIRA_PROJECT_ID}/foldertree/testrun"
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        return response.json()

    def get_test_case_id(self, project_key, test_case_key):

        url = f"{self.JIRA_URL}/rest/tests/1.0/testcase/{project_key}-{test_case_key}?fields=id"
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('id')

    def get_test_run_id(self, test_cycle_key):
        url = f"{self.JIRA_URL}/rest/tests/1.0/testrun/{test_cycle_key}?fields=id"
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('id')

    def add_test_cases_to_cycle(self, test_run_id, test_case_ids):

        url = f"{self.JIRA_URL}/rest/tests/1.0/testrunitem/bulk/save"
        added_test_run_items = [
            {"index": i, "lastTestResult": {"testCaseId": test_case_id}}
            for i, test_case_id in enumerate(test_case_ids)
        ]
        payload = {
            "testRunId": test_run_id,
            "addedTestRunItems": added_test_run_items
        }
        response = self._send_request_with_retries('PUT', url, json=payload)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()

    def get_test_run_items(self, test_run_id):

        url = (f"{self.JIRA_URL}/rest/tests/1.0/testrun/{test_run_id}/testrunitems?"
               f"fields=testCaseId,testScriptResults(id),testRunId")
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json().get('testRunItems', [])

    def get_test_script_results(self, test_run_id, item_id):

        url = (f"{self.JIRA_URL}/rest/tests/1.0/testrun/{test_run_id}"
               f"/testresults?fields=testScriptResults(id,parameterSetId)&itemId={item_id}")
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json()

    def get_test_statuses(self):

        url = f'{self.JIRA_URL}/rest/tests/1.0/project/{self.JIRA_PROJECT_ID}/testresultstatus'
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json()

    def get_test_cycle_statuses(self):
        url = f'{self.JIRA_URL}/rest/tests/1.0/project/{self.JIRA_PROJECT_ID}/testrunstatus'
        response = self._send_request_with_retries('GET', url)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
        return response.json()


    def set_test_case_statuses(self, statuses):

        url = f"{self.JIRA_URL}/rest/tests/1.0/testresult"
        response = self._send_request_with_retries('PUT', url, json=statuses)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()

    def set_test_script_statuses(self, script_statuses):

        url = f"{self.JIRA_URL}/rest/tests/1.0/testscriptresult"
        response = self._send_request_with_retries('PUT', url, json=script_statuses)

        data = dump.dump_all(response)
        print(data.decode('utf-8'))

        response.raise_for_status()
