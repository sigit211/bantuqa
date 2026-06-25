import os

with open('src/api.py', 'r') as f:
    content = f.read()

old_get_runs = '''    def get_runs(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f\"get_runs/{project_id}\")
            if isinstance(res, list):
                return res
            return res.get('runs', [])
        except requests.exceptions.RequestException:
            return []'''

new_get_runs = old_get_runs + '''

    def get_tests(self, run_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f\"get_tests/{run_id}\")
            if isinstance(res, list):
                return res
            return res.get('tests', [])
        except requests.exceptions.RequestException:
            return []'''

content = content.replace(old_get_runs, new_get_runs)

old_upload = '''    def upload_attachment_to_run(self, run_id: int, file_path: str) -> Optional[str]:
        try:
            with open(file_path, 'rb') as f:
                files = {'attachment': (os.path.basename(file_path), f, 'image/png')}
                res = self._post(f\"add_attachment_to_run/{run_id}\", files=files)
                return res.get('attachment_id')
        except requests.exceptions.RequestException as e:
            print(f\"Failed to upload attachment: {e}\")
            return None'''

new_upload = old_upload + '''

    def upload_attachment_to_result(self, result_id: int, file_path: str) -> Optional[str]:
        try:
            with open(file_path, 'rb') as f:
                files = {'attachment': (os.path.basename(file_path), f, 'image/png')}
                res = self._post(f\"add_attachment_to_result/{result_id}\", files=files)
                return res.get('attachment_id')
        except requests.exceptions.RequestException as e:
            print(f\"Failed to upload attachment to result: {e}\")
            return None'''

content = content.replace(old_upload, new_upload)

old_add_result = '''    def add_result_for_case(self, run_id: int, case_id: int, status_id: int, comment: str) -> bool:
        try:
            data = {
                \"status_id\": status_id,
                \"comment\": comment
            }
            self._post(f\"add_result_for_case/{run_id}/{case_id}\", data=data)
            return True
        except requests.exceptions.RequestException as e:
            print(f\"Failed to add result: {e}\")
            return False'''

new_add_result = '''    def add_result_for_case(self, run_id: int, case_id: int, status_id: int, comment: str) -> Optional[int]:
        try:
            data = {
                \"status_id\": status_id,
                \"comment\": comment
            }
            res = self._post(f\"add_result_for_case/{run_id}/{case_id}\", data=data)
            if res and isinstance(res, list) and len(res) > 0:
                return res[0].get('id')
            elif res and isinstance(res, dict):
                return res.get('id')
            return None
        except requests.exceptions.RequestException as e:
            print(f\"Failed to add result: {e}\")
            return None'''

content = content.replace(old_add_result, new_add_result)

with open('src/api.py', 'w') as f:
    f.write(content)
