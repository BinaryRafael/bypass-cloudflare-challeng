import json
import traceback
from time import sleep
from typing import Optional
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from capmonster import SolverCaptcha


class CloudFlareToken:
    def __init__(self, site_bypass: str, site_key: Optional[str] = None) -> None:
        self.__site_bypass = site_bypass
        self.__site_key = site_key
        self.__browser = self.__initialize_browser()

    def __initialize_browser(self) -> Optional[webdriver.Chrome]:
        """Inicializa o navegador Chrome com opções específicas."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--no-sandbox")  # Recomendado em ambientes Linux
            chrome_options.add_argument("--disable-dev-shm-usage")  # Evita problemas de memória em contêineres
            chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
            return webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print("Erro ao iniciar o navegador:", e)
            return None

    def __intercept_turnstile_script(self) -> None:
        """Injeta um script para interceptar parâmetros do Turnstile."""
        script = """
            (function() {
                function waitForTurnstile() {
                    if (window.turnstile && window.turnstile.render) {
                        const originalRender = window.turnstile.render;
                        window.turnstile.render = function(element, params) {
                            let p = {
                                sitekey: params.sitekey,
                                pageurl: window.location.href,
                                data: params.cData,
                                pagedata: params.chlPageData,
                                action: params.action,
                                useragent: navigator.userAgent
                            };
                            console.log('intercepted-params:' + JSON.stringify(p));
                            window.cfCallback = params.callback;
                            return originalRender(element, params);
                        };
                    } else {
                        setTimeout(waitForTurnstile, 100);
                    }
                }
                waitForTurnstile();
            })();
        """
        if self.__browser:
            self.__browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
            sleep(5)

    def __extract_params_from_logs(self) -> dict:
        """Extrai os parâmetros de log interceptados."""
        for entry in self.__browser.get_log('browser'):
            message = entry['message']
            if 'intercepted-params:' in message:
                params = message.split('intercepted-params:')[1].strip()
                params = params[:len(params) - 1].replace(r'\"', '"').replace(r'\r', '').replace(r'\n', '').replace(r'\t', '')
                return json.loads(params)
        return {}

    def main(self, timeout_seconds: int) -> Optional[dict]:
        """Executa o processo principal de resolução e coleta de cookies."""
        end_time = datetime.now() + timedelta(seconds=timeout_seconds)
        try:
            while datetime.now() < end_time:
                if not self.__browser:
                    return None

                self.__intercept_turnstile_script()
                self.__browser.get(self.__site_bypass)

                dados_site = self.__extract_params_from_logs()
                if not dados_site:
                    sleep(1)
                    continue

                solved = SolverCaptcha(self.__site_bypass, self.__site_key).main(dados_site, 'V2')
                if solved is None:
                    continue

                self.__browser.execute_script(f'window.cfCallback("{solved}");')

            return None
        except Exception:
            traceback.print_exc()
            return None


if __name__ == '__main__':
    #solver = CloudFlareToken('https://duplecast.com/client/login/', '').main(30)

    #solver = CloudFlareToken('https://smartone-iptv.com/client/login/', '').main(30)

    solver = CloudFlareToken('https://www.xior-booking.com/', '').main(30)

    print(solver)