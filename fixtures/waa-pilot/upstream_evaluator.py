from __future__ import annotations
import os, re, logging
from datetime import datetime
from typing import *
logger=logging.getLogger("waa.pilot")

def exact_match(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result == expect:
        return 1.
    else:
        return 0.

def compare_text_file(actual: str, expected: str, **options) -> float:
    """
    Args:
        actual (str): path to result text file
        expected (str): path to gold text file

    Return:
        float: the score
    """
    if not actual:
        return 0.

    with open(actual) as f1:
        actual_text = f1.read()
    with open(expected) as f2:
        expected_text = f2.read()

    ignore_blanks = options.get('ignore_blanks', False)
    if ignore_blanks:
        actual_text = re.sub(r'[\t\n]', ' ', actual_text).strip()
        actual_text = re.sub(r'\s+', ' ', actual_text)
        expected_text = re.sub(r'[\t\n]', ' ', expected_text).strip()
        expected_text = re.sub(r'\s+', ' ', expected_text)

    ignore_case = options.get('ignore_case', False)
    if ignore_case:
        actual_text = actual_text.lower()
        expected_text = expected_text.lower()

    if actual_text == expected_text:
        return 1.0
    return 0.0

def get_vm_file(env, config: Dict[str, Any]) -> Union[Optional[str], List[Optional[str]]]:
    """
    Config:
        path (str): absolute path on the VM to fetch
        dest (str): file name of the downloaded file
        multi (bool) : optional. if path and dest are lists providing
          information of multiple files. defaults to False
        gives (List[int]): optional. defaults to [0]. which files are directly
          returned to the metric. if len==1, str is returned; else, list is
          returned.
        only support for single file now:
        time_suffix(bool): optional. defaults to False. if True, append the current time in required format.
        time_format(str): optional. defaults to "%Y_%m_%d". format of the time suffix.
    """
    time_format = "%Y_%m_%d"
    if not config.get("multi", False):
        paths: List[str] = [config["path"]]
        dests: List[str] = [config["dest"]]
        if "time_suffix" in config.keys() and config["time_suffix"]:
            if "time_format" in config.keys():
                time_format = config["time_format"]
            # Insert time before . in file type suffix
            paths = [p.split(".")[0] + datetime.now().strftime(time_format) + "." + p.split(".")[1] if "." in p else p for p in paths]
            dests = [d.split(".")[0] + datetime.now().strftime(time_format) + "." + d.split(".")[1] if "." in d else d for d in dests]
    else:
        paths: List[str] = config["path"]
        dests: List[str] = config["dest"]


    cache_paths: List[str] = []

    gives: Set[int] = set(config.get("gives", [0]))

    for i, (p, d) in enumerate(zip(paths, dests)):
        _path = os.path.join(env.cache_dir, d)
        file = env.controller.get_file(p)
        if file is None:
            #return None
            # raise FileNotFoundError("File not found on VM: {:}".format(config["path"]))
            if i in gives:
                cache_paths.append(None)
            continue

        if i in gives:
            cache_paths.append(_path)
        with open(_path, "wb") as f:
            f.write(file)
    return cache_paths[0] if len(cache_paths)==1 else cache_paths

def get_cloud_file(env, config: Dict[str, Any]) -> Union[str, List[str]]:
    """
    Config:
        path (str|List[str]): the url to download from
        dest (str|List[str])): file name of the downloaded file
        multi (bool) : optional. if path and dest are lists providing
          information of multiple files. defaults to False
        gives (List[int]): optional. defaults to [0]. which files are directly
          returned to the metric. if len==1, str is returned; else, list is
          returned.
    """

    if not config.get("multi", False):
        paths: List[str] = [config["path"]]
        dests: List[str] = [config["dest"]]
    else:
        paths: List[str] = config["path"]
        dests: List[str] = config["dest"]
    cache_paths: List[str] = []

    gives: Set[int] = set(config.get("gives", [0]))

    for i, (p, d) in enumerate(zip(paths, dests)):
        _path = os.path.join(env.cache_dir, d)
        if i in gives:
            cache_paths.append(_path)

        if os.path.exists(_path):
            #return _path
            continue

        url = p
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return cache_paths[0] if len(cache_paths)==1 else cache_paths

def get_vm_file_exists_in_vm_folder(env, config) -> str:
    folder_name = config["folder_name"]
    logger.info(f"Folder name: {folder_name}")
    file_name = config["file_name"]
    logger.info(f"File name: {file_name}")
    if not folder_name or not file_name:
        return 0.0

    file_path = os.path.join(folder_name, file_name)
    if env.controller.get_file(file_path):
        return 1.0
    else:
        return 0.0

def get_is_details_view(env, config):
    if not config["folder_path"]:
        return False
    is_details_view = env.controller.get_vm_file_explorer_is_details_view(config["folder_path"])
    return is_details_view

def get_vm_active_window_title(env, config) -> str:
    window_title = env.controller.execute_python_command("import pyautogui; print(pyautogui.getActiveWindowTitle())")['output'].strip()
    logger.info(f"Window title: {window_title}")
    return window_title

def get_system_notifications(env, config: Dict[str,str]):
    """
    Checks if system notifications are enabled or disabled.
    If the `ToastEnabled` key exists and its value is 1, notifications are enabled.
    If the value is 0, notifications are disabled.
    If the key does not exist, assume notifications are enabled.
    """
    key_path = r"HKCU:Software\Microsoft\Windows\CurrentVersion\PushNotifications"
    setting_path = "ToastEnabled"
    is_notification_enabled  = env.controller.get_registry_key(key_path, setting_path)
    try:
        if is_notification_enabled is None or is_notification_enabled['output'] == "" :
            # Key doesn't exist, assume notifications are enabled
            return 'False'
        elif is_notification_enabled['output']:
            toast_enabled =  is_notification_enabled['output'].replace('\n','')
            if toast_enabled == '0':
                return 'True'
        else:
            return 'False'
    except Exception as e:
        print("Error retrieving notification setting")
        return "Uanble to get the notifications settings state"

def get_rule(env, config: Dict[str, R]) -> R:
    """
    Returns the rule as-is.
    """
    return config["rules"]

def evaluate(self):
        """
        Evaluate whether the task is successfully completed.
        """

        self.setup_controller.setup(self.evaluator.get("postconfig", []))

        # logger.info(f"ACTION HISTORY: {self.action_history}")

        if self.evaluator['func'] == "infeasible":
            if len(self.action_history) > 0 and self.action_history[-1] == "FAIL":
                # logger.info("Infeasible task and last agent action = FAIL")
                return 1
            else:
                # logger.info("Infeasible task but last agent action != FAIL")
                return 0
        else:
            if len(self.action_history) > 0 and self.action_history[-1] == "FAIL":
                # logger.info("Feasible task but last agent = FAIL")
                return 0

        if type(self.metric) == list:
            results = []
            for idx, metric in enumerate(self.metric):
                try:
                    config = self.evaluator["result"][idx]
                    result_state = self.result_getter[idx](self, config)
                except FileNotFoundError:
                    logger.error("File not found!")
                    if self.metric_conj == 'and':
                        return 0

                expected = self.evaluator["expected"][idx]
                expected_state = self.expected_getter[idx](self, expected) if expected else None

                metric: int = metric(result_state, expected_state,
                                     **self.metric_options[idx]) if expected_state is not None \
                    else metric(result_state, **self.metric_options[idx])

                if self.metric_conj == 'and' and float(metric) == 0.0:
                    return 0
                elif self.metric_conj == 'or' and float(metric) == 1.0:
                    return 1
                else:
                    results.append(metric)
            return sum(results) / len(results) if self.metric_conj == 'and' else max(results)
        else:
            try:
                result_state = self.result_getter(self, self.evaluator["result"])
            except FileNotFoundError:
                logger.error("File not found!")
                return 0
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return 0
            expected_state = self.expected_getter(self, self.evaluator["expected"]) if "expected" in self.evaluator \
                else None

            # logger.info(f"RESULT STATE: {result_state}")
            # logger.info(f"EXPECTED STATE: {expected_state}")

            metric: float = self.metric(result_state, expected_state,
                                        **self.metric_options) if expected_state is not None \
                else self.metric(result_state, **self.metric_options)

        if isinstance(metric, (float, int, bool)):
            return metric
        else:
            logger.error("Task metric value produced is neither numeric nor boolean: returning 0 instead")
            return 0            

        return metric
