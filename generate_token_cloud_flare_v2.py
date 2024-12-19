import json
import traceback
from time import sleep
from typing import Optional
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from capmonster import SolverCaptcha


class CloudFlareToken:
    def __init__(self, site_bypass: str, site_key: Optional[str] = None) -> None:
        self.__site_bypass = site_bypass
        self.__site_key = site_key
        self.__browser = self.__get_browser()

    def __get_browser(self) -> Optional[webdriver.Chrome]:
        try:
            chrome_options = Options()
            # chrome_options.add_argument("--headless")  # Executa sem interface gráfica
            chrome_options.add_argument("--disable-gpu")  # Necessário em algumas plataformas
            chrome_options.add_argument("--no-sandbox")  # Recomendado em ambientes Linux
            chrome_options.add_argument("--disable-dev-shm-usage")  # Evita problemas de memória em contêineres
            chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
            return webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print("Erro ao iniciar o navegador:", e)
            return None

    def __execute_interception_script(self) -> None:
        script = """
            const i = setInterval(() => {
                if (window.turnstile) {
                    clearInterval(i)
                    window.turnstile.render = (a, b) => {
                        let p = {
                            sitekey: b.sitekey,
                            pageurl: window.location.href,
                            data: b.cData,
                            pagedata: b.chlPageData,
                            action: b.action,
                            useragent: navigator.userAgent
                        }
                        console.log('intercepted-params:' + JSON.stringify(p))
                        window.cfCallback = b.callback
                    }
                }
            }, 50);
        """
        if self.__browser:
            self.__browser.execute_script(script)
            sleep(5)

    def __extract_params_from_logs(self):
        for entry in self.__browser.get_log('browser'):
            message = entry['message']
            if 'intercepted-params:' in message:
                params = message.split('intercepted-params:')[1].strip()
                params = params[:len(params) - 1].replace(r'\"', '"').replace(r'\r', '').replace(r'\n', '').replace(
                    r'\t', '')
                return json.loads(params)
        return {}

    def __get_token_csrf(self) -> Optional[str]:
        try:
            # Define o tempo máximo de espera como 10 segundos
            wait = WebDriverWait(self.__browser, 10)

            # Aguarda até que o elemento esteja presente no DOM e visível
            element = wait.until(EC.presence_of_element_located((By.NAME, '_csrf_token')))

            # Retorna o valor do atributo 'value'
            return element.get_attribute('value')
        except:
            return

    def main(self, timeout_seconds: int) -> Optional[dict]:
        end_time = datetime.now() + timedelta(seconds=timeout_seconds)
        try:
            while True:

                if datetime.now() >= end_time:
                    print("Function timed out")
                    return

                if not self.__browser:
                    return

                self.__browser.get(self.__site_bypass)
                self.__execute_interception_script()
                dados_site = self.__extract_params_from_logs()

                if not dados_site:
                    sleep(1)
                    continue

                solved = SolverCaptcha(self.__site_bypass, self.__site_key).main(dados_site, 'V2')
                if solved is None:
                    continue

                self.__browser.execute_script(f'window.cfCallback("{solved}");')

                is_cookies_present: bool = False
                while True:
                    if datetime.now() >= end_time:
                        return

                    cookies = self.__browser.get_cookies()

                    if not cookies:
                        sleep(1)
                        continue

                    for cookie in cookies:
                        if cookie['name'] == 'cf_clearance':
                            cookie_dict = {c['name']: c['value'] for c in cookies}
                            cookie_dict['user_agente'] = self.__browser.execute_script("return navigator.userAgent;")
                            cookie_dict['_csrf_token'] = self.__get_token_csrf()
                            return cookie_dict

                    break

                if not is_cookies_present:
                    continue

                return
        except:
            traceback.print_exc()
            return


if __name__ == '__main__':
    #solver = CloudFlareToken('https://duplecast.com/client/login/', '').main(30)

    #solver = CloudFlareToken('https://smartone-iptv.com/client/login/', '').main(30)

    solver = CloudFlareToken('https://www.xior-booking.com/', '').main(30)

    print(solver)
