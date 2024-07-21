import logging
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from nacos import NacosClient

logger = logging.getLogger(__name__)

nacos_ip = "localhost"
nacos_port = "18848"
nacos_username = "nacos"
nacos_password = "nacos"


def test_nacosclient_config_get():
    logger.info("======= Testing NacosClient.config_get")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_get("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_config_listen():
    logger.info("======= Testing NacosClient.config_listen")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, old_data = nacos.config_get("test", "DEFAULT_GROUP")
    assert success
    logger.info(f'Config "test"\'s old value: {old_data}')
    logger.info(f'Waiting for config "test"\'s value changing...')
    success, new_data = nacos.config_listen(
        "test", "DEFAULT_GROUP", content=old_data, ret_new_content=True
    )
    assert success
    logger.info(f'Config "test"\'s new value: {new_data}')
    logger.info(f"======= Test result: {old_data!=new_data}")


def test_nacosclient_config_publish(content="test"):
    logger.info("======= Testing NacosClient.config_publish")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_publish("test", "DEFAULT_GROUP", content=content)
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_config_delete():
    logger.info("======= Testing NacosClient.config_delete")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_delete("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_config_history_get_items():
    logger.info("======= Testing NacosClient.config_history_get_items")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_history_get_items("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_config_history_get_details():
    logger.info("======= Testing NacosClient.config_history_get_details")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, items = nacos.config_history_get_items("test", "DEFAULT_GROUP")
    assert success
    success, data = nacos.config_history_get_details(
        items["pageItems"][0]["id"], "test", "DEFAULT_GROUP"
    )
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_config_history_get_previous():
    logger.info("======= Testing NacosClient.config_history_get_previous")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_history_get_previous(1, "test", "DEFAULT_GROUP")
    assert success
    logger.info(f"======= Test result: {data['content']!=None}, data:{data}")


def test_nacosclient_instance_register():
    logger.info("======= Testing NacosClient.instance_register")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_register(
        ip="127.0.0.1", port=22, service_name="ssh", weight=0.5
    )
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_instance_deregister():
    logger.info("======= Testing NacosClient.instance_deregister")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_deregister(
        ip="127.0.0.1", port=22, service_name="ssh"
    )
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_instance_modify():
    logger.info("======= Testing NacosClient.instance_modify")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_modify(
        service_name="ssh",
        ip="127.0.0.1",
        port=22,
        weight=0.6,
        metadata={"test": "test"},
    )
    assert success
    logger.info(f"======= Test result: {data}, data:{data}")


def test_nacosclient_instance_list():
    logger.info("======= Testing NacosClient.instance_list")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_list(service_name="ssh")
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_instance_detail():
    logger.info("======= Testing NacosClient.instance_detail")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_detail(service_name="ssh", ip="127.0.0.1", port=22)
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_instance_beat_send():
    logger.info("======= Testing NacosClient.instance_beat_send")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, beat_info = nacos.instance_detail(
        service_name="ssh", ip="127.0.0.1", port=22
    )
    assert success
    success, data = nacos.instance_beat_send(
        service_name="ssh", ip="127.0.0.1", port=22, beat=beat_info
    )
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_instance_update_healthy():
    logger.info("======= Testing NacosClient.instance_update_healthy")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.system_switches_modify(
        entry="healthCheckEnabled", value=False
    )
    assert success and data
    success, data = nacos.system_switches_modify(
        entry="autoChangeHealthCheckEnabled", value=False
    )
    assert success and data
    time.sleep(3)
    success, new_data = nacos.system_switches_get()
    assert success
    assert new_data["healthCheckEnabled"] == False
    assert new_data["autoChangeHealthCheckEnabled"] == False
    time.sleep(2)
    success, data = nacos.instance_update_healthy(
        service_name="ssh", ip="127.0.0.1", port=22, healthy=True
    )
    assert success, data
    time.sleep(2)
    success, detail = nacos.instance_detail(service_name="ssh", ip="127.0.0.1", port=22)
    assert success
    success, data = nacos.system_switches_modify(entry="healthCheckEnabled", value=True)
    assert success and data
    success, data = nacos.system_switches_modify(
        entry="autoChangeHealthCheckEnabled", value=True
    )
    assert success and data
    logger.info(f"======= Test result: {detail['healthy']==True}")


def test_nacosclient_service_create(service_name="test"):
    logger.info("======= Testing NacosClient.service_create")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.service_create(service_name=service_name)
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_service_delete(service_name="test"):
    logger.info("======= Testing NacosClient.service_delete")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.service_delete(service_name=service_name)
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_service_modify(service_name="test"):
    logger.info("======= Testing NacosClient.service_modify")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.service_modify(
        service_name=service_name, metadata={"test": "test"}
    )
    assert success
    logger.info(f"======= Test result: {data}")


def test_nacosclient_service_detail(service_name="test"):
    logger.info("======= Testing NacosClient.service_query")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.service_detail(
        service_name=service_name,
    )
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_service_list():
    logger.info("======= Testing NacosClient.service_list")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.service_list()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_system_switches_get():
    logger.info("======= Testing NacosClient.system_switches_get")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.system_switches_get()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_system_switches_modify():
    logger.info("======= Testing NacosClient.system_switches_modify")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.system_switches_modify(entry="pushEnabled", value=False)
    assert success and data
    time.sleep(2)
    success, new_data = nacos.system_switches_get()
    assert success
    success, data = nacos.system_switches_modify(entry="pushEnabled", value=True)
    assert success and data
    logger.info(f"======= Test result: {new_data['pushEnabled']==False}")


def test_nacosclient_system_metrics():
    logger.info("======= Testing NacosClient.system_metrics")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.system_metrics()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_cluster_list():
    logger.info("======= Testing NacosClient.cluster_list")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.cluster_list()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_cluster_leader():
    logger.info("======= Testing NacosClient.cluster_leader")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.cluster_leader()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_namespace_list():
    logger.info("======= Testing NacosClient.namespace_list")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.namespace_list()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_nacosclient_namespace_create():
    logger.info("======= Testing NacosClient.namespace_create")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.namespace_create(
        namespace_id="test", namespace_name="test", namespace_desc="test"
    )
    assert success and data == True
    time.sleep(2)
    success, new_data = nacos.namespace_list()
    assert success
    is_exist = False
    for item in new_data["data"]:
        if item["namespace"] == "test":
            is_exist = True
            break
    logger.info(f"======= Test result: {is_exist==True}")


def test_nacosclient_namespace_modify():
    logger.info("======= Testing NacosClient.namespace_modify")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.namespace_modify(
        namespace_id="test", namespace_name="test1", namespace_desc="test"
    )
    assert success and data == True
    time.sleep(2)
    success, new_data = nacos.namespace_list()
    assert success
    is_modified = False
    for item in new_data["data"]:
        if item["namespace"] == "test":
            is_modified = item["namespaceShowName"] == "test1"
            break
    logger.info(f"======= Test result: {is_modified==True}")


def test_nacosclient_namespace_delete():
    logger.info("======= Testing NacosClient.namespace_delete")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.namespace_delete(namespace_id="test")
    assert success
    logger.info(f"======= Test result: {data==True}")


def test_nacosclient():
    ## test config
    logger.info("Tests starting...")
    logger.info("Testing config...")
    test_nacosclient_config_publish(content="test1")
    test_nacosclient_config_get()
    test_nacosclient_config_publish(content="test2")
    test_nacosclient_config_listen()
    test_nacosclient_config_delete()
    test_nacosclient_config_publish(content="test3")
    test_nacosclient_config_history_get_items()
    test_nacosclient_config_history_get_details()
    test_nacosclient_config_history_get_previous()
    # test instance
    logger.info("Testing instance...")
    test_nacosclient_instance_register()
    test_nacosclient_instance_deregister()
    test_nacosclient_instance_register()
    test_nacosclient_instance_list()
    test_nacosclient_instance_modify()
    time.sleep(2)
    test_nacosclient_instance_detail()
    test_nacosclient_instance_beat_send()
    time.sleep(4)
    test_nacosclient_instance_beat_send()
    time.sleep(2)
    # test_nacosclient_instance_update_healthy()  # ignore and don't test
    # test service
    logger.info("Testing service...")
    test_nacosclient_service_create(service_name="test1")
    time.sleep(2)
    test_nacosclient_service_delete(service_name="test1")
    time.sleep(2)
    test_nacosclient_service_create(service_name="test1")
    time.sleep(2)
    test_nacosclient_service_modify(service_name="test1")
    time.sleep(2)
    test_nacosclient_service_detail(service_name="test1")
    time.sleep(2)
    test_nacosclient_service_list()
    time.sleep(2)
    test_nacosclient_service_delete(service_name="test1")
    time.sleep(2)
    # test system and cluster
    logger.info("Testing system and cluster...")
    test_nacosclient_system_switches_get()
    test_nacosclient_system_switches_modify()
    test_nacosclient_system_metrics()
    # test_nacosclient_cluster_list()  # ignore and don't test
    # test_nacosclient_cluster_leader()  # ignore and don't test
    logger.info("Testing namespace...")
    test_nacosclient_namespace_list()
    test_nacosclient_namespace_create()
    test_nacosclient_namespace_modify()
    test_nacosclient_namespace_delete()
    logger.info("Testing done.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    test_nacosclient()
