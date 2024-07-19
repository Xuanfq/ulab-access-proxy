import requests
import logging
import time
import hashlib

logger = logging.getLogger(__name__)


class NacosClient:
    def __init__(self, ip, port, username, password, https: bool = False):
        self.openapi_nacos_version = "2.3.2"
        self.ip = ip
        self.port = port
        self.https = https
        self.username = username
        self.password = password
        self.base_url = f"{'https' if https else 'http'}://{ip}:{port}/nacos/v1"
        self.access_token = None
        self.access_token_ttl = 0  # seconds
        self.global_admin = False
        self.login_timestamp = 0  # seconds
        self.login()

    def _request(self, method, url, ret_type: str = "json", **kwargs):
        if self.access_token is not None:
            kwargs["params"]["accessToken"] = self.access_token
        logger.debug(f"Requesting {method} {url} with params {kwargs}")
        response = requests.request(method, f"{self.base_url}/{url}", **kwargs)
        if response.status_code != 200:
            msg = f"Request failed with status code [{response.status_code}] and response: [{response.text}]"
            logger.error(msg)
            if self.login_timestamp + self.access_token_ttl <= int(time.time()):
                logger.warning("Access token expired, retrying login...")
                success, data = self.login()
                if success:
                    return self._request(method, url, **kwargs)
            return False, msg
        logger.debug(response)
        if ret_type == "json":
            data = response.json()
        elif ret_type == "text":
            data = response.text
        return True, data

    def login(self):
        self.login_timestamp = 0
        self.access_token = None
        self.access_token_ttl = 0
        self.global_admin = False
        method = "POST"
        uri = "auth/login"
        params = {"username": self.username, "password": self.password}
        login_timestamp = int(time.time())
        success, data = self._request(method, uri, params=params)
        logger.debug(f"Login result: {success}, data: {data}")
        count = 1
        while not success and count <= 3:
            logger.error(f"Login failed [the {count} time(s)]: {data}")
            time.sleep(3)
            count += 1
            logger.warning(f"Retry login [the {count} time(s)]...")
            login_timestamp = int(time.time())
            success, data = self._request(method, uri, params=params)
        if success:
            self.login_timestamp = login_timestamp
            self.access_token = data["accessToken"]
            self.access_token_ttl = data["tokenTtl"]
            self.global_admin = data["globalAdmin"]
        else:
            logger.error(f"Login failed [the {count} time(s)]: {data}")
            self.login_timestamp = login_timestamp
            self.access_token = None
            self.access_token_ttl = 0
            self.global_admin = False
        return success, data

    def get_config(self, data_id: str, group: str, tenant: str = None):
        """get config from nacos

        Args:
            data_id (str): config id
            group (str): config group
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: return success, data if success, otherwise return False and msg
        """
        method = "GET"
        uri = "cs/configs"
        params = {"dataId": data_id, "group": group, "tenant": tenant}
        success, data = self._request(method, uri, ret_type="text", params=params)
        logger.debug(f"Get config result: {success}, data: {data}")
        return success, data

    def listen_config(
        self,
        data_id: str,
        group: str,
        content: str = "",
        content_md5: str = None,
        pulling_timeout: int = 30000,
        listen_until_change: bool = False,
        ret_new_content: bool = False,
        tenant: str = None,
    ):
        """Listen config changes. (Thread blocking)

        Args:
            data_id (str): config id
            group (str): config group
            content (str, optional): config content. Defaults to "".
            content_md5 (str, optional): config content md5, compute the md5 from content if it is None. Defaults to None.
            pulling_timeout (int, optional): Long rotation training waiting for 30 seconds, fill in 30000 here. Defaults to 30000.
            listen_until_change (bool, optional): listen all the time (will not return until the config changes). Defaults to False.
            ret_new_content (bool, optional): return the new config if config changes. Defaults to False.
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: return False and msg if failed, otherwise return True and data (config content if ret_new_content is True, otherwise return the "dataId%02group%02tenant%01").
        """
        if content_md5 is None:
            content_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()
        method = "POST"
        uri = "cs/configs/listener"
        char2 = chr(2)
        char1 = chr(1)
        listening_configs = f"{data_id}{char2}{group}{char2}{content_md5}{char1}"
        if tenant is not None:
            listening_configs = (
                f"{data_id}{char2}{group}{char2}{content_md5}{char2}{tenant}{char1}"
            )
        params = {"Listening-Configs": listening_configs}
        headers = {"Long-Pulling-Timeout": str(pulling_timeout)}
        success, data = self._request(
            method, uri, ret_type="text", params=params, headers=headers
        )
        logger.debug(f"Listen config result: {success}, data: {data}")
        while listen_until_change and success and data == "":
            success, data = self._request(
                method, uri, ret_type="text", params=params, headers=headers
            )
            logger.debug(f"Listen config result: {success}, data: {data}")
        if success and data != "":
            if ret_new_content:
                return self.get_config(data_id, group, tenant)
        return success, data


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    nacos = NacosClient("localhost", "8848", "nacos", "nacos")
    # nacos = NacosClient("localhost", "8848", "test", "test")
    success, data = nacos.get_config("test", "DEFAULT_GROUP")  # 获取配置
    logger.info(f"Test get config: {success}, data: {data}")
    success, new_data = nacos.listen_config(
        "test",
        "DEFAULT_GROUP",
        # content=data,
        content_md5=hashlib.md5(data.encode("utf-8")).hexdigest(),
        listen_until_change=True,
        ret_new_content=True,
    )  # 监听配置
    logger.info(f"Test listen config: {success}, new data: {new_data}")
    logger.info("Test finished.")
