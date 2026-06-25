import logging
import mimetypes
import requests
import base64
from typing import List, Dict, Any, Optional, Tuple
import os
import time

logger = logging.getLogger(__name__)

class TestRailAPI:
    def __init__(self):
        self.base_url = ""
        self.email = ""
        self.api_key = ""
        self.session = requests.Session()

    def set_credentials(self, base_url: str, email: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_key = api_key
        
        auth_str = f"{email}:{api_key}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/json"
        })

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _guess_mime_type(file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def _ensure_file_ready(self, file_path: str, timeout: float = 5.0, interval: float = 0.1) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        size = os.path.getsize(file_path)
        if size == 0:
            raise ValueError(f"Attachment file is empty: {file_path}")

        if size > 10 * 1024 * 1024:
            logger.warning("Attachment %s is %d bytes; may exceed TestRail upload limits", file_path, size)

        last_size = size
        end_time = time.time() + timeout
        while time.time() < end_time:
            time.sleep(interval)
            size = os.path.getsize(file_path)
            if size > 0 and size == last_size:
                return
            last_size = size

        if size == 0:
            raise ValueError(f"Attachment file is empty after waiting: {file_path}")

    @staticmethod
    def _format_http_error(e: requests.exceptions.RequestException) -> str:
        details = []
        if getattr(e, 'response', None) is not None:
            resp = e.response
            status = getattr(resp, 'status_code', None)
            reason = getattr(resp, 'reason', '')
            status_line = f"HTTP {status} {reason}".strip()
            details.append(status_line)
            try:
                text = resp.text or ""
            except Exception:
                text = ""
            if text:
                trimmed = text.strip().replace('\n', ' ').replace('\r', ' ')
                if len(trimmed) > 1000:
                    trimmed = trimmed[:1000] + "..."
                details.append(f"Response body: {trimmed}")
            try:
                json_body = resp.json()
                if isinstance(json_body, dict) and 'error' in json_body:
                    details.append(f"Error: {json_body['error']}")
            except ValueError:
                pass
        if e.args:
            details.append(str(e))
        return " | ".join([d for d in details if d])

    def _post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/index.php?/api/v2/{endpoint}"
        headers = self.session.headers.copy()
        response = self.session.post(url, headers=headers, json=data)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logger.error("Request failed for %s with status %s", url, getattr(response, 'status_code', None))
            logger.error("Request headers: %s", getattr(response, 'request', None) and response.request.headers)
            logger.error("Response headers: %s", response.headers)
            logger.error("Response text: %s", response.text[:1000])
            logger.exception("HTTP request failed for %s", url)
            raise

        if response.text:
            try:
                return response.json()
            except ValueError:
                logger.warning("Non-JSON response from %s: %s %s", url, response.status_code, response.text[:200])
                return {}
        return {}

    def validate_login(self) -> bool:
        try:
            # We use get_user_by_email to validate
            self._get(f"get_user_by_email&email={self.email}")
            return True
        except requests.exceptions.RequestException:
            return False

    def get_projects(self) -> List[Dict[str, Any]]:
        try:
            res = self._get("get_projects")
            # The v2 API sometimes returns a list directly or a dict with 'projects'
            if isinstance(res, list):
                return res
            return res.get('projects', [])
        except requests.exceptions.RequestException:
            return []

    def get_plans(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f"get_plans/{project_id}")
            if isinstance(res, list):
                return res
            return res.get('plans', [])
        except requests.exceptions.RequestException:
            return []

    def get_plan_runs(self, plan_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f"get_plan/{plan_id}")
            # A plan has an 'entries' array. Each entry has a 'runs' array.
            runs = []
            entries = res.get('entries', [])
            for entry in entries:
                runs.extend(entry.get('runs', []))
            return runs
        except requests.exceptions.RequestException:
            return []

    def get_runs(self, project_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f"get_runs/{project_id}")
            if isinstance(res, list):
                return res
            return res.get('runs', [])
        except requests.exceptions.RequestException:
            return []

    def get_tests(self, run_id: int) -> List[Dict[str, Any]]:
        try:
            res = self._get(f"get_tests/{run_id}")
            if isinstance(res, list):
                return res
            return res.get('tests', [])
        except requests.exceptions.RequestException:
            return []

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        try:
            res = self._get(f"get_case/{case_id}")
            return res if isinstance(res, dict) else None
        except requests.exceptions.RequestException:
            return None

    def get_users(self) -> List[Dict[str, Any]]:
        try:
            res = self._get("get_users")
            if isinstance(res, list):
                return res
            return res.get('users', [])
        except requests.exceptions.RequestException:
            return []

    def get_statuses(self) -> List[Dict[str, Any]]:
        try:
            res = self._get("get_statuses")
            if isinstance(res, list):
                return res
            return res.get('statuses', [])
        except requests.exceptions.RequestException:
            logger.warning("Failed to fetch TestRail statuses")
            return []

    def upload_attachment_to_run(self, run_id: int, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            self._ensure_file_ready(file_path)
            
            # Read file as bytes to avoid file handle issues
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            mime_type = self._guess_mime_type(file_path)
            logger.debug("Uploading %s (%s bytes, type=%s) to run %s", filename, len(file_content), mime_type, run_id)
            
            # Create fresh session for upload to avoid Content-Type: application/json conflict
            # TestRail API strictly requires multipart/form-data for file uploads
            upload_session = requests.Session()
            auth_str = f"{self.email}:{self.api_key}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            upload_session.headers.update({
                "Authorization": f"Basic {b64_auth}"
            })
            
            url = f"{self.base_url}/index.php?/api/v2/add_attachment_to_run/{run_id}"
            files = {'attachment': (filename, file_content, mime_type)}
            logger.debug("POST %s with file %s (%d bytes, mime=%s)", url, filename, len(file_content), mime_type)
            
            response = upload_session.post(url, files=files, timeout=30)
            response.raise_for_status()
            
            res = response.json() if response.text else {}
            logger.debug("add_attachment_to_run response: %s", res)
            
            aid = None
            if isinstance(res, dict):
                aid = res.get('attachment_id') or res.get('id')
            elif isinstance(res, list) and res:
                aid = res[0].get('attachment_id') or res[0].get('id')
            
            if not aid:
                msg = f"Upload attachment returned no id: {res}"
                logger.error(msg)
                return None, msg
            
            logger.info("Successfully uploaded %s with attachment_id=%s", filename, aid)
            return aid, None
            
        except (FileNotFoundError, ValueError) as e:
            msg = str(e)
            logger.error("File validation error for %s: %s", file_path, msg)
            return None, msg
        except requests.exceptions.RequestException as e:
            msg = self._format_http_error(e) or str(e)
            logger.error("HTTP request failed for upload: %s", msg)
            return None, msg
        except OSError as e:
            msg = f"File I/O error for {file_path}: {e}"
            logger.error(msg)
            return None, msg
        except Exception as e:
            msg = f"Unexpected error uploading {file_path}: {e}"
            logger.exception(msg)
            return None, msg

    def upload_attachment_to_result(self, result_id: int, file_path: str) -> Optional[str]:
        try:
            self._ensure_file_ready(file_path)
            
            # Read file as bytes to avoid file handle issues
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            mime_type = self._guess_mime_type(file_path)
            logger.debug("Uploading %s (%s bytes, type=%s) to result %s", filename, len(file_content), mime_type, result_id)
            
            # Create fresh session for upload to avoid Content-Type: application/json conflict
            # TestRail API strictly requires multipart/form-data for file uploads
            upload_session = requests.Session()
            auth_str = f"{self.email}:{self.api_key}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            upload_session.headers.update({
                "Authorization": f"Basic {b64_auth}"
            })
            
            url = f"{self.base_url}/index.php?/api/v2/add_attachment_to_result/{result_id}"
            files = {'attachment': (filename, file_content, mime_type)}
            logger.debug("POST %s with file %s (%d bytes, mime=%s)", url, filename, len(file_content), mime_type)
            
            response = upload_session.post(url, files=files, timeout=30)
            response.raise_for_status()
            
            res = response.json() if response.text else {}
            
            aid = None
            if isinstance(res, dict):
                aid = res.get('attachment_id') or res.get('id')
            elif isinstance(res, list) and res:
                aid = res[0].get('attachment_id') or res[0].get('id')
            
            if aid:
                logger.info("Successfully uploaded %s to result %s with attachment_id=%s", filename, result_id, aid)
            return aid
            
        except (FileNotFoundError, ValueError) as e:
            logger.error("File validation error for %s: %s", file_path, e)
            return None
        except requests.exceptions.RequestException as e:
            msg = self._format_http_error(e) or str(e)
            logger.error("HTTP request failed for upload to result: %s", msg)
            return None
        except Exception as e:
            logger.exception("Unexpected error uploading to result %s: %s", result_id, e)
            return None

    def add_result_for_case(
        self,
        run_id: int,
        case_id: int,
        status_id: int,
        comment: str,
        elapsed: Optional[str] = None,
        custom_step_results: Optional[list] = None
    ) -> Optional[int]:
        try:
            data = {
                "status_id": status_id,
                "comment": comment
            }
            if elapsed:
                data["elapsed"] = elapsed
            if custom_step_results:
                data["custom_step_results"] = custom_step_results
            res = self._post(f"add_result_for_case/{run_id}/{case_id}", data=data)
            if res and isinstance(res, list) and len(res) > 0:
                return res[0].get('id')
            elif res and isinstance(res, dict):
                return res.get('id')
            return None
        except requests.exceptions.RequestException as e:
            msg = f"Failed to add result: {e}"
            if getattr(e, 'response', None) is not None:
                try:
                    body = e.response.text
                except Exception:
                    body = None
                msg += f" (status={e.response.status_code} body={body[:300] if body else 'N/A'})"
            logger.exception(msg)
            return None

api_client = TestRailAPI()