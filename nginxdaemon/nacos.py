import requests
import logging
import time
import hashlib
import json

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

    def _request(self, method, uri, ret_type: str = "json", **kwargs):
        # check params
        if "params" not in kwargs:
            kwargs["params"] = {}
        # add access token
        if self.access_token is not None:
            kwargs["params"]["accessToken"] = self.access_token
        # check bool params
        kwargs["params"] = {
            k: (str(v).lower() if isinstance(v, bool) else v)
            for k, v in kwargs["params"].items()
        }
        logger.debug(f"Requesting {method} {uri} with params {kwargs}")
        # do request
        response = requests.request(
            method=method, url=f"{self.base_url}/{uri}", **kwargs
        )
        # get request status code
        if response.status_code != 200:
            msg = f"Request failed with status code [{response.status_code}] and response: [{response.text}]"
            logger.error(msg)
            # check access token timeout
            if self.login_timestamp + self.access_token_ttl <= int(time.time()):
                logger.warning("Access token expired, retrying login...")
                success, data = self.login()
                if success:
                    return self._request(method, uri, **kwargs)
            return False, msg
        logger.debug(response)
        # parse response
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

    def config_get(self, data_id: str, group: str, tenant: str = None):
        """get config from nacos

        Args:
            data_id (str): config id
            group (str): config group
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and config_data or False and msg
        """
        method = "GET"
        uri = "cs/configs"
        params = {"dataId": data_id, "group": group, "tenant": tenant}
        success, data = self._request(method, uri, ret_type="text", params=params)
        logger.debug(f"Get config result: {success}, data: {data}")
        return success, data

    def config_listen(
        self,
        data_id: str,
        group: str,
        content: str = "",
        content_md5: str = None,
        pulling_timeout: int = 30000,
        listen_until_change: bool = False,
        ret_new_content: bool = True,
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
            success, data: return False and msg if failed, otherwise return True and data (data is config content if ret_new_content is True, otherwise return the "dataId%02group%02tenant%01").
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
                return self.config_get(data_id, group, tenant)
        return success, data

    def config_publish(
        self,
        data_id: str,
        group: str,
        content: str,
        type: str = None,
        tenant: str = None,
    ):
        """Publish config.

        Args:
            data_id (str): config id
            group (str): config group
            content (str): config content
            type (str, optional): config type. Defaults to None.
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and publish result (bool) or False and msg
        """
        method = "POST"
        uri = "cs/configs"
        params = {"dataId": data_id, "group": group, "content": content}
        if type is not None:
            params["type"] = type
        if tenant is not None:
            params["tenant"] = tenant
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "true"
        logger.debug(f"Publish config result: {success}, data: {data}")
        return success, data

    def config_delete(self, data_id: str, group: str, tenant: str = None):
        """Delete config.

        Args:
            data_id (str): config id
            group (str): config group
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and delete success or not | False and msg
        """
        method = "DELETE"
        uri = "cs/configs"
        params = {"dataId": data_id, "group": group}
        if tenant is not None:
            params["tenant"] = tenant
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "true"
        logger.debug(f"Delete config result: {success}, data: {data}")
        return success, data

    def config_history_get_items(
        self,
        data_id: str,
        group: str,
        page_no: int = None,
        page_size: int = 100,
        tenant: str = None,
    ):
        """Get history config but not include content and md5 etc.

        Args:
            data_id (str): config id
            group (str): config group
            page_no (int, optional): page number. Defaults to None.
            page_size (int, optional): page size. Defaults to 100.
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and history config items or False and msg
            data:{
                "totalCount": 1,
                "pageNumber": 1,
                "pagesAvailable": 1,
                "pageItems": [
                    {
                    'id': '1',
                    'lastId': -1,
                    'dataId': 'test',
                    'group': 'DEFAULT_GROUP',
                    'tenant': '',
                    'appName': '',
                    'md5': None,
                    'content': None,
                    'srcIp': '172.20.0.1',
                    'srcUser': 'nacos',
                    'opType': 'I',
                    'createdTime': '2024-07-18T16:01:40.000+08:00',
                    'lastModifiedTime': '2024-07-19T00:01:41.000+08:00',
                    'encryptedDataKey': None
                    }
                ]
            }
        """
        method = "GET"
        uri = "cs/history?search=accurate"
        params = {"dataId": data_id, "group": group}
        if page_no is not None:
            params["pageNo"] = page_no
        if page_size is not None:
            params["pageSize"] = page_size
        if tenant is not None:
            params["tenant"] = tenant
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Get history config items result: {success}, data: {data}")
        return success, data

    def config_history_get_details(self, nid: int, data_id, group, tenant: str = None):
        """Get history config details (include content).

        Args:
            nid (int): history config id
            data_id (str): config id
            group (str): config group
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and history config details or False and msg
            data: {
                'id': '12',
                'lastId': -1,
                'dataId': 'test',
                'group': 'DEFAULT_GROUP',
                'tenant': '',
                'appName': '',
                'md5': 'b198c4d5d234d0b8444e8b519af96784',
                'content': 'testpublishpublish',
                'srcIp': '172.20.0.1',
                'srcUser': 'nacos',
                'opType': 'U',
                'createdTime': '2024-07-19T13:58:55.000+08:00',
                'lastModifiedTime': '2024-07-19T21:58:55.000+08:00',
                'encryptedDataKey': ''
            }
        """
        method = "GET"
        uri = "cs/history"
        params = {"nid": nid, "dataId": data_id, "group": group}
        if tenant is not None:
            params["tenant"] = tenant
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Get history config detail result: {success}, data: {data}")
        return success, data

    def config_history_get_previous(self, id: int, data_id, group, tenant: str = None):
        """Get previous config.

        Args:
            id (int): config history item's id, should be the same as the first nid of dataId in history config items
            data_id (str): config id
            group (str): config group
            tenant (str, optional): tenant namespace. Defaults to None.

        Returns:
            success, data: True and previous config or False and msg
            data: {
                'id': '12',
                'lastId': -1,
                'dataId': 'test',
                'group': 'DEFAULT_GROUP',
                'tenant': '',
                'appName': '',
                'md5': 'b198c4d5d234d0b8444e8b519af96784',
                'content': 'testpublishpublish',
                'srcIp': '172.20.0.1',
                'srcUser': 'nacos',
                'opType': 'U',
                'createdTime': '2024-07-19T13:58:55.000+08:00',
                'lastModifiedTime': '2024-07-19T21:58:55.000+08:00',
                'encryptedDataKey': ''
            }
        """
        method = "GET"
        uri = "cs/history/previous"
        params = {"id": id, "dataId": data_id, "group": group}
        if tenant is not None:
            params["tenant"] = tenant
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Get previous config result: {success}, data: {data}")
        return success, data

    def instance_register(
        self,
        service_name: str,
        ip: str,
        port: int,
        enabled: bool = None,
        healthy: bool = None,
        ephemeral: bool = None,
        weight: float = None,
        metadata: dict = None,
        group_name: str = None,
        cluster_name: str = None,
        namespace_id: str = None,
    ):
        """Register instance.

        Args:
            service_name (str): service name
            ip (str): instance ip
            port (int): instance port
            enabled (bool, optional): instance enabled. Defaults to None.
            healthy (bool, optional): instance healthy. Defaults to None.
            ephemeral (bool, optional): instance ephemeral. Defaults to None.
            weight (float, optional): instance weight. Defaults to None.
            metadata (dict, optional): instance metadata. Defaults to None.
            group_name (str, optional): instance group name. Defaults to None.
            cluster_name (str, optional): instance cluster name. Defaults to None.
            namespace_id (str, optional): instance namespace id. Defaults to None.
        Returns:
            success, data: True and instance register result(bool: success or not) or False and msg
        """
        method = "POST"
        uri = "ns/instance"
        params = {
            "ip": ip,
            "port": port,
            "serviceName": service_name,
            "enabled": enabled,
            "healthy": healthy,
            "ephemeral": ephemeral,
            "weight": weight,
            "metadata": json.dumps(metadata),
            "clusterName": cluster_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Register instance result: {success}, data: {data}")
        return success, data

    def instance_deregister(
        self,
        service_name: str,
        ip: str,
        port: int,
        ephemeral: bool = None,
        group_name: str = None,
        cluster_name: str = None,
        namespace_id: str = None,
    ):
        """Deregister instance.

        Args:
            service_name (str): service name
            ip (str): instance ip
            port (int): instance port
            ephemeral (bool, optional): instance ephemeral. Defaults to None.
            group_name (str, optional): service group name. Defaults to None.
            cluster_name (str, optional): service cluster name. Defaults to None.
            namespace_id (str, optional): service namespace id. Defaults to None.
        Returns:
            success, data: True and instance deregister result(bool: success or not) or False and msg
        """
        method = "DELETE"
        uri = "ns/instance"
        params = {
            "ip": ip,
            "port": port,
            "serviceName": service_name,
            "groupName": group_name,
            "clusterName": cluster_name,
            "ephemeral": ephemeral,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Deregister instance result: {success}, data: {data}")
        return success, data

    def instance_modify(
        self,
        service_name: str,
        ip: str,
        port: int,
        enabled: bool = None,
        ephemeral: bool = None,
        weight: float = None,
        metadata: dict = None,
        group_name: str = None,
        cluster_name: str = None,
        namespace_id: str = None,
    ):
        """Modify instance.

        Args:
            service_name (str): service name
            ip (str): instance ip
            port (int): instance port
            enabled (bool, optional): instance enabled. Defaults to None.
            ephemeral (bool, optional): instance ephemeral. Defaults to None.
            weight (float, optional): instance weight. Defaults to None.
            metadata (dict, optional): instance metadata. Defaults to None.
            group_name (str, optional): instance group name. Defaults to None.
            cluster_name (str, optional): instance cluster name. Defaults to None.
            namespace_id (str, optional): instance namespace id. Defaults to None.
        Returns:
            success, data: True and instance modify result(bool: success or not) or False and msg
        """
        method = "PUT"
        uri = "ns/instance"
        params = {
            "ip": ip,
            "port": port,
            "serviceName": service_name,
            "enabled": enabled,
            "ephemeral": ephemeral,
            "weight": weight,
            "metadata": json.dumps(metadata),
            "clusterName": cluster_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Instance modify result: {success}, data: {data}")
        return success, data

    def instance_list(
        self,
        service_name: str,
        group_name: str = None,
        clusters: str = None,
        namespace_id: str = None,
        healthy_only: bool = False,
    ):
        """Query instance list of service_name.

        Args:
            service_name (str): service name
            group_name (str, optional): group name. Defaults to None.
            clusters (str, optional): clusters,Multiple clusters separated by ','. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.
            healthy_only (bool, optional): healthy only. Defaults to False.
        Returns:
            success, data: True and instance list or False and msg
            data: {
                'name': 'DEFAULT_GROUP@@ssh',
                'groupName': 'DEFAULT_GROUP',
                'clusters': '',
                'cacheMillis': 10000,
                'hosts': [{
                    'instanceId': '127.0.0.1#22#DEFAULT#DEFAULT_GROUP@@ssh',
                    'ip': '127.0.0.1',
                    'port': 22,
                    'weight': 1.0,
                    'healthy': True,
                    'enabled': True,
                    'ephemeral': True,
                    'clusterName': 'DEFAULT',
                    'serviceName': 'DEFAULT_GROUP@@ssh',
                    'metadata': {},
                    'instanceHeartBeatInterval': 5000,
                    'instanceHeartBeatTimeOut': 15000,
                    'ipDeleteTimeout': 30000,
                    'instanceIdGenerator': 'simple'
                }],
            lastRefTime': 1721456819294,
            'checksum': '',
            'allIPs': False,
            'reachProtectionThreshold': False,
            'valid': True}
        """
        method = "GET"
        uri = "ns/instance/list"
        params = {
            "serviceName": service_name,
            "groupName": group_name,
            "clusters": clusters,
            "namespaceId": namespace_id,
            "healthyOnly": healthy_only,
        }
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Instance list result: {success}, data: {data}")
        return success, data

    def instance_detail(
        self,
        service_name: str,
        ip: str,
        port: int,
        ephemeral: bool = None,
        group_name: str = None,
        cluster_name: str = None,
        namespace_id: str = None,
        healthy_only: bool = False,
    ):
        """Get instance detail

        Args:
            service_name (str): service name
            ip (str): ip
            port (int): port
            ephemeral (bool, optional): ephemeral. Defaults to None.
            group_name (str, optional): group name. Defaults to None.
            cluster_name (str, optional): cluster name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.
            healthy_only (bool, optional): healthy only. Defaults to False.
        Returns:
            success, data: True and instance detail or False and msg
        Example:
            data: {
                'service': 'DEFAULT_GROUP@@ssh',
                'ip': '127.0.0.1',
                'port': 22,
                'clusterName': 'DEFAULT',
                'weight': 0.6,
                'healthy': False,
                'instanceId': '127.0.0.1#22#DEFAULT#DEFAULT_GROUP@@ssh',
                'metadata': {'test': 'test'}
            }
        """
        method = "GET"
        uri = "ns/instance"
        params = {
            "serviceName": service_name,
            "ip": ip,
            "port": port,
            "ephemeral": ephemeral,
            "groupName": group_name,
            "clusterName": cluster_name,
            "namespaceId": namespace_id,
            "healthyOnly": healthy_only,
        }
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Instance detail result: {success}, data: {data}")
        return success, data

    def instance_beat_send(
        self,
        service_name: str,
        ip: str,
        port: int,
        beat: str | dict,
        ephemeral: bool = None,
        group_name: str = None,
        namespace_id: str = None,
    ):
        """Send instance beat. By default, the instance sends heartbeat packets at:
            1. 1 beat / 5 s, healthy
            2. > 15 s, unhealthy
            3. > 30 s, remove instance

        Args:
            service_name (str): service name
            ip (str): ip
            port (int): port
            beat (str): Instance heartbeat content, is the "instance detail" in fact, str of json or dict
            ephemeral (bool, optional): ephemeral. Defaults to None.
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.
        Returns:
            success, data: True and instance beat data or False and msg
        Example:
            data: {
                'clientBeatInterval': 5000,
                'code': 10200,
                'lightBeatEnabled': True
            }
        """
        method = "PUT"
        uri = "ns/instance/beat"
        params = {
            "serviceName": service_name,
            "ip": ip,
            "port": port,
            "beat": beat if type(beat) == str else json.dumps(beat),
            "ephemeral": ephemeral,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Instance beat result: {success}, data: {data}")
        return success, data

    def instance_update_healthy(
        self,
        service_name: str,
        ip: str,
        port: int,
        healthy: bool,
        group_name: str = None,
        cluster_name: str = None,
        namespace_id: str = None,
    ):
        """Update instance healthy status.
        Health check of cluster should be turned off!!!

        Args:
            service_name (str): service name
            ip (str): instance ip
            port (int): instance port
            healthy (bool): instance healthy status
            group_name (str, optional): service group name. Defaults to None.
            cluster_name (str, optional): service cluster name. Defaults to None.
            namespace_id (str, optional): service namespace id. Defaults to None.

        Returns: success, data: True and update result (bool, success or not) or False and msg
        """
        method = "PUT"
        uri = "ns/health/instance"
        params = {
            "serviceName": service_name,
            "ip": ip,
            "port": port,
            "healthy": healthy,
            "groupName": group_name,
            "clusterName": cluster_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Instance update healthy result: {success}, data: {data}")
        return success, data

    def service_create(
        self,
        service_name: str,
        group_name: str = None,
        namespace_id: str = None,
        protect_threshold: float = 0,
        metadata: dict = None,
        selector: dict = None,
    ):
        """Create service

        Args:
            service_name (str): service name
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.
            protect_threshold (float, optional): protect threshold. Defaults to None.
            metadata (dict, optional): metadata. Defaults to None.
            selector (dict, optional): selector, access policy. Defaults to None.

        Returns: success, data: True and create result(bool, success or not) or False and msg
        """
        method = "POST"
        uri = "ns/service"
        params = {
            "serviceName": service_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
            "protectThreshold": protect_threshold,
            "metadata": json.dumps(metadata),
        }
        if selector:
            params["selector"] = json.dumps(selector)
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Service create result: {success}, data: {data}")
        return success, data

    def service_delete(
        self,
        service_name: str,
        group_name: str = None,
        namespace_id: str = None,
    ):
        """Delete service

        Args:
            service_name (str): service name
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.

        Returns: success, data: True and create result(bool, success or not) or False and msg
        """
        method = "DELETE"
        uri = "ns/service"
        params = {
            "serviceName": service_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Service delete result: {success}, data: {data}")
        return success, data

    def service_modify(
        self,
        service_name: str,
        group_name: str = None,
        namespace_id: str = None,
        protect_threshold: float = 0,
        metadata: dict = None,
        selector: dict = None,
    ):
        """Modify service

        Args:
            service_name (str): service name
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.
            protect_threshold (float, optional): protect threshold. Defaults to None.
            metadata (dict, optional): metadata. Defaults to None.
            selector (dict, optional): selector, access policy. Defaults to None.

        Returns: success, data: True and create result(bool, success or not) or False and msg
        """
        method = "PUT"
        uri = "ns/service"
        params = {
            "serviceName": service_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
            "protectThreshold": protect_threshold,
            "metadata": json.dumps(metadata),
        }
        if selector:
            params["selector"] = json.dumps(selector)
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"Service modify result: {success}, data: {data}")
        return success, data

    def service_detail(
        self,
        service_name: str,
        group_name: str = None,
        namespace_id: str = None,
    ):
        """Query a service to get service detail

        Args:
            service_name (str): service name
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.

        Returns: success, data: True and service data or False and msg
        Example:
            data:{
                metadata: {},
                groupName: "DEFAULT_GROUP",
                namespaceId: "public",
                name: "nacos.test.2",
                selector: {
                    type: "none"
                },
                protectThreshold: 0,
                clusters: [
                    {
                        healthChecker: {
                            type: "TCP"
                        },
                        metadata: {},
                        name: "c1"
                    }
                ]
            }
        """
        method = "GET"
        uri = "ns/service"
        params = {
            "serviceName": service_name,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Service detail result: {success}, data: {data}")
        return success, data

    def service_list(
        self,
        page_no: int = 1,
        page_size: int = 100,
        group_name: str = None,
        namespace_id: str = None,
    ):
        """Query services to get service list

        Args:
            page_no (int, optional): page number. Defaults to 1.
            page_size (int, optional): page size. Defaults to 100.
            group_name (str, optional): group name. Defaults to None.
            namespace_id (str, optional): namespace id. Defaults to None.

        Returns: success, data: True and service data or False and msg
        Example:
            data: {
                "count": 3,
                "doms": [
                    "nacos.test.1",
                    "nacos.test.2",
                    "test"
                ]
            }
        """
        method = "GET"
        uri = "ns/service/list"
        params = {
            "pageNo": page_no,
            "pageSize": page_size,
            "groupName": group_name,
            "namespaceId": namespace_id,
        }
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Service list result: {success}, data: {data}")
        return success, data

    def system_switches_get(
        self,
    ):
        """Query system switches

        Args:

        Returns: success, data: True and system switches status data or False and msg
        Example:
            data: {
                "name": "00-00---000-NACOS_SWITCH_DOMAIN-000---00-00",
                "masters": None,
                "adWeightMap": {},
                "defaultPushCacheMillis": 10000,
                "clientBeatInterval": 5000,
                "defaultCacheMillis": 3000,
                "distroThreshold": 0.7,
                "healthCheckEnabled": True,
                "autoChangeHealthCheckEnabled": True,
                "distroEnabled": True,
                "enableStandalone": True,
                "pushEnabled": True,
                "checkTimes": 3,
                "httpHealthParams": {"max": 5000, "min": 500, "factor": 0.85},
                "tcpHealthParams": {"max": 5000, "min": 1000, "factor": 0.75},
                "mysqlHealthParams": {"max": 3000, "min": 2000, "factor": 0.65},
                "incrementalList": [],
                "serverStatusSynchronizationPeriodMillis": 2000,
                "serviceStatusSynchronizationPeriodMillis": 5000,
                "disableAddIP": False,
                "sendBeatOnly": False,
                "lightBeatEnabled": True,
                "limitedUrlMap": {},
                "distroServerExpiredMillis": 10000,
                "pushGoVersion": "0.1.0",
                "pushJavaVersion": "0.1.0",
                "pushPythonVersion": "0.4.3",
                "pushCVersion": "1.0.12",
                "pushCSharpVersion": "0.9.0",
                "enableAuthentication": False,
                "overriddenServerStatus": None,
                "defaultInstanceEphemeral": True,
                "healthCheckWhiteList": [],
                "checksum": None,
            }
        """
        method = "GET"
        uri = "ns/operator/switches"
        success, data = self._request(method, uri, ret_type="json")
        logger.debug(f"System switches result: {success}, data: {data}")
        return success, data

    def system_switches_modify(self, entry: str, value: str, debug: bool = False):
        """Modify system switches

        Args:
            entry (str): switch name
            value (str): switch value
            debug (bool, optional): if True effective on local nacos else cluster. Defaults to False.

        Returns: success, data: True and modify result (bool, success or not) or False and msg
        Example: data: True
        """
        method = "PUT"
        uri = "ns/operator/switches"
        params = {"entry": entry, "value": value, "debug": debug}
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "ok"
        logger.debug(f"System switches modify result: {success}, data: {data}")
        return success, data

    def system_metrics(self):
        """Get system metrics

        Args:

        Returns: success, data: True and metrics data or False and msg
        Example:
            data: {
                # serviceCount: 336,
                # load: 0.09,
                # mem: 0.46210432,
                # responsibleServiceCount: 98,
                # instanceCount: 4,
                # cpu: 0.010242796,
                status: "UP",
                # responsibleInstanceCount: 0
            }
        """
        method = "GET"
        uri = "ns/operator/metrics"
        success, data = self._request(method, uri, ret_type="json")
        logger.debug(f"System metrics result: {success}, data: {data}")
        return success, data

    def cluster_list(self, health_only: bool = False):
        """Get cluster server list. Nacos Not Implemented!!!

        Args:
            health_only (bool, optional): if True only return healthy cluster. Defaults to False.

        Returns: success, data: True and cluster list or False and msg
        Example:
            data: [{
                ip: "1.1.1.1",
                servePort: 8848,
                site: "unknown",
                weight: 1,
                adWeight: 0,
                alive: false,
                lastRefTime: 0,
                lastRefTimeStr: null,
                key: "1.1.1.1:8848"
            }]
        """
        method = "GET"
        uri = "ns/operator/servers"
        params = {"healthy": health_only}
        success, data = self._request(method, uri, ret_type="json", params=params)
        logger.debug(f"Cluster list result: {success}, data: {data}")
        return success, data

    def cluster_leader(self):
        """Get cluster server list. Nacos Not Implemented!!!

        Args:

        Returns: success, data: True and cluster list or False and msg
        Example:
            data: {
                leader: "{"heartbeatDueMs":2500,"ip":"1.1.1.1:8848","leaderDueMs":12853,"state":"LEADER","term":54202,"voteFor":"1.1.1.1:8848"}"
            }
        """
        method = "GET"
        uri = "ns/raft/leader"
        success, data = self._request(method, uri, ret_type="json")
        logger.debug(f"Cluster leader result: {success}, data: {data}")
        return success, data

    def namespace_list(self):
        """Get namespace list.

        Returns: success, data: True and namespace list or False and msg
        Example:
            data: {
                "code": 200,
                "message": None,
                "data": [
                    {
                        "namespace": "",
                        "namespaceShowName": "public",
                        "namespaceDesc": None,
                        "quota": 200,
                        "configCount": 1,
                        "type": 0,
                    }
                ],
            }
        """
        method = "GET"
        uri = "console/namespaces"
        success, data = self._request(method, uri, ret_type="json")
        logger.debug(f"Namespace list result: {success}, data: {data}")
        return success, data

    def namespace_create(
        self, namespace_id: str, namespace_name: str, namespace_desc: str = None
    ):
        """Create namespace

        Args:
            namespace_id (str): custom namespace id
            namespace_name (str): namespace name
            namespace_desc (str): namespace description

        Returns: success, data: True and create status (bool, success or not) or False and msg
        """
        method = "POST"
        uri = "console/namespaces"
        params = {
            "customNamespaceId": namespace_id,
            "namespaceName": namespace_name,
            "namespaceDesc": namespace_desc,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "true"
        logger.debug(f"Namespace create result: {success}, data: {data}")
        return success, data

    def namespace_modify(
        self, namespace_id: str, namespace_name: str, namespace_desc: str = None
    ):
        """Modify namespace

        Args:
            namespace_id (str): (custom) namespace id
            namespace_name (str): namespace show name
            namespace_desc (str): namespace description

        Returns: success, data: True and create status (bool, success or not) or False and msg
        """
        method = "PUT"
        uri = "console/namespaces"
        params = {
            "namespace": namespace_id,
            "namespaceShowName": namespace_name,
            "namespaceDesc": namespace_desc,
        }
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "true"
        logger.debug(f"Namespace create result: {success}, data: {data}")
        return success, data

    def namespace_delete(self, namespace_id: str):
        """Delete namespace

        Args:
            namespace_id (str): namespace id

        Returns: success, data: True and delete status (bool, success or not) or False and msg
        """
        method = "DELETE"
        uri = "console/namespaces"
        params = {"namespaceId": namespace_id}
        success, data = self._request(method, uri, ret_type="text", params=params)
        if success:
            data = data == "true"
        logger.debug(f"Namespace delete result: {success}, data: {data}")
        return success, data
