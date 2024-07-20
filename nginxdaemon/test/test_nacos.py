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
    logger.info("Testing NacosClient.config_get")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_get("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {success}, data:{data}")


def test_nacosclient_config_listen():
    logger.info("Testing NacosClient.config_listen")
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
    logger.info(f"Test result: {old_data!=new_data}")


def test_nacosclient_config_publish(content="test"):
    logger.info("Testing NacosClient.config_publish")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_publish("test", "DEFAULT_GROUP", content=content)
    assert success
    logger.info(f"Test result: {data}")


def test_nacosclient_config_delete():
    logger.info("Testing NacosClient.config_delete")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_delete("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {data}")


def test_nacosclient_config_history_get_items():
    logger.info("Testing NacosClient.config_history_get_items")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_history_get_items("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {success}, data:{data}")


def test_nacosclient_config_history_get_details():
    logger.info("Testing NacosClient.config_history_get_details")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, items = nacos.config_history_get_items("test", "DEFAULT_GROUP")
    assert success
    success, data = nacos.config_history_get_details(
        items["pageItems"][0]["id"], "test", "DEFAULT_GROUP"
    )
    assert success
    logger.info(f"Test result: {success}, data:{data}")


def test_nacosclient_config_history_get_previous():
    logger.info("Testing NacosClient.config_history_get_previous")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_history_get_previous(1, "test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {data['content']!=None}, data:{data}")


def test_nacosclient_instance_register():
    logger.info("Testing NacosClient.instance_register")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_register(
        ip="127.0.0.1", port=22, service_name="ssh", weight=0.5
    )
    assert success
    logger.info(f"Test result: {data}")


def test_nacosclient_instance_deregister():
    logger.info("Testing NacosClient.instance_deregister")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_deregister(
        ip="127.0.0.1", port=22, service_name="ssh"
    )
    assert success
    logger.info(f"Test result: {data}")


def test_nacosclient_instance_modify():
    logger.info("Testing NacosClient.instance_modify")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_modify(
        service_name="ssh",
        ip="127.0.0.1",
        port=22,
        weight=0.6,
        metadata='{"test":"test"}',
    )
    assert success
    logger.info(f"Test result: {data}, data:{data}")


def test_nacosclient_instance_list():
    logger.info("Testing NacosClient.instance_list")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_list(service_name="ssh")
    assert success
    logger.info(f"Test result: {success}, data:{data}")


def test_nacosclient_instance_detail():
    logger.info("Testing NacosClient.instance_detail")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.instance_detail(service_name="ssh", ip="127.0.0.1", port=22)
    assert success
    logger.info(f"Test result: {success}, data:{data}")


def test_nacosclient_instance_beat_send():
    logger.info("Testing NacosClient.instance_beat_send")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, beat_info = nacos.instance_detail(
        service_name="ssh", ip="127.0.0.1", port=22
    )
    assert success
    success, data = nacos.instance_beat_send(
        service_name="ssh", ip="127.0.0.1", port=22, beat=beat_info
    )
    assert success
    logger.info(f"Test result: {data}")


def test_nacosclient_():
    logger.info("Testing NacosClient.config_get")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_delete("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {data['content']!=None}, data:{data}")


def test_nacosclient_():
    logger.info("Testing NacosClient.config_get")
    nacos = NacosClient(nacos_ip, nacos_port, nacos_username, nacos_password)
    success, data = nacos.config_delete("test", "DEFAULT_GROUP")
    assert success
    logger.info(f"Test result: {data['content']!=None}, data:{data}")


def test_nacosclient():
    # test config
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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    test_nacosclient()
