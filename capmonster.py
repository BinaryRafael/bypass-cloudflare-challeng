import time
import requests
from typing import Optional


class SolverCaptcha:

    def __init__(self, site_bypass: str, site_key: str) -> None:
        self.__site_bypass = site_bypass
        self.__site_key = site_key
        self.__key = 'SEU TOKEN'

    def __get_payload_create_task(self, dados: dict) -> dict:
        return {
            "clientKey": self.__key,
            "task": {
                "type": "TurnstileTask",
                "websiteURL": dados['pageurl'],
                "websiteKey": dados['sitekey'],
                "cloudflareTaskType": "token",
                "userAgent": dados["useragent"],
                "pageAction": dados["action"],
                "pageData": dados['pagedata'],
                "data": dados['data']
            }
        }

    def __get_payload_create_task_proxyless(self) -> dict:
        return {
            "clientKey": self.__key,
            "task":
            {
                "type": "TurnstileTaskProxyless",
                "websiteURL": self.__site_bypass,
                "websiteKey": self.__site_key
            }
        }

    def __create_task(self, dados: dict) -> Optional[str]:
        try:
            response = requests.post('https://api.capmonster.cloud/createTask',
                                     json=self.__get_payload_create_task(dados)).json()
            return response.get('taskId', None)
        except:
            pass

    def __create_task_proxyless(self) -> Optional[str]:
        try:
            response = requests.post('https://api.capmonster.cloud/createTask',
                                     json=self.__get_payload_create_task_proxyless()).json()
            return response.get('taskId', None)
        except:
            pass

    def __get_result(self, task_id: str) -> Optional[str]:

        while True:
            response = requests.post('https://api.capmonster.cloud/getTaskResult', json={
                "clientKey": self.__key,
                "taskId": task_id
            }).json()

            if response.get('status', None) is not None:

                if response.get('status') == 'processing':
                    time.sleep(2)
                    continue

                elif response.get('status') == 'ready':
                    return response.get('solution', {}).get('token', None)

                else:
                    break

    def main(self, dados: dict, type_captch: str) -> Optional[str]:

        if type_captch == 'V1':
            task_id = self.__create_task_proxyless()
            print(f'task_id={task_id}')
        else:
            task_id = self.__create_task(dados)

        if task_id is None:
            return

        return self.__get_result(task_id)
