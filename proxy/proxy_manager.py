import logging
import random
import re
import time
from typing import Dict, Optional

import requests
from requests.auth import HTTPProxyAuth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self, config: Dict):
        self.proxy_pools = config
        self.mobile_pools = config.get("mobile_pools")
        self.valid_proxies = []
        self.failed_proxies = set()
        self.ip_list = None

    def get_proxy_from_pool(self, pool_name: str,is_mobile=False) -> Optional[Dict]:
        """从指定代理池获取代理"""
        if pool_name not in self.proxy_pools:
            logger.error(f"代理池 {pool_name} 不存在")
            return None

        # pool_config = self.proxy_pools[pool_name]

        if is_mobile:
            pool_config = self.proxy_pools['qm_proxy']
            print("使用的移动数据代理")
        else:
            pool_config = self.proxy_pools[pool_name]
            print("使用的家庭宽带")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            auth = None

            # 设置认证信息
            if pool_config['auth_type'] == 'basic':
                auth = (pool_config['username'], pool_config['password'])

            response = requests.get(
                pool_config['api_url'],
                headers=headers,
                auth=auth,
                timeout=10
            )

            if response.status_code == 200:
                #proxy_data = response.text()
                proxy_data = response.text.strip().split('\n')
                for proxy in proxy_data:
                    proxy = proxy.strip()
                    proxy_data_dict = {
                        "ip": proxy.split(':')[0],
                        "port": proxy.split(':')[1]
                    }
                    self.valid_proxies.append(proxy_data_dict)
                    return self._parse_proxy_response(proxy_data_dict, pool_config)
                #return self._parse_proxy_response(proxy_data, pool_config)
            else:
                logger.error(f"从 {pool_name} 获取代理失败: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"从 {pool_name} 获取代理时出错: {str(e)}")
            return None

    def _parse_proxy_response(self, proxy_data: Dict, pool_config: Dict) -> Dict:
        """解析代理池响应"""
        # 适配不同代理池的响应格式
        if 'ip' in proxy_data and 'port' in proxy_data:
            ip = proxy_data['ip']
            port = proxy_data['port']
        elif 'proxy' in proxy_data:
            ip = proxy_data['proxy'].split(':')[0]
            port = proxy_data['proxy'].split(':')[1]
        else:
            # 默认处理
            ip = proxy_data.get('server', '').split(':')[0]
            port = proxy_data.get('server', '').split(':')[1] if ':' in proxy_data.get('server', '') else '80'

        username = pool_config.get('username', '')
        password = pool_config.get('password', '')

        if username and password:
            proxy_url = f"http://{username}:{password}@{ip}:{port}"
        else:
            proxy_url = f"http://{ip}:{port}"

        return {
            'http': proxy_url,
            'https': proxy_url,
            'pool': pool_config.get('name', 'unknown'),
            'ip': ip,
            'port': port,
            'username': username,
            'password': password,
            'raw': proxy_data
        }

    def validate_proxy(self, proxy_config: Dict, test_url: str, timeout: int = 10,is_mobile = False) -> bool:
        """验证代理是否可用"""
        try:
            proxies = {
                'http': proxy_config['http'],
                'https': proxy_config['https']
            }

            print(proxy_config.get('http'))

            auth = None
            if proxy_config['username'] and proxy_config['password']:
                auth = HTTPProxyAuth(proxy_config['username'], proxy_config['password'])

            response = requests.get(
                test_url,
                proxies=proxies,
                auth=auth,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )

            if response.status_code == 200:
                ip_ip_response = self.parse_ipip_response(response.text.strip())

                print(ip_ip_response.get("ip"))

                check_city_address = ip_ip_response.get("location").rpartition(' ')[0].replace(' ', '')

                # 从已经用的ip中，匹配是否ip头2段数据是否一样，一样则重新获取
                is_match_address = self.add_ip_with_prefix_check(self.ip_list,ip_ip_response.get("ip"))

                if is_match_address:
                    # 该ip已经用过之前的ip头部了
                    print("ip匹配上了")
                    return False

                # 验证地区是否匹配
                # city_address_url = f"https://api.ipplus360.com/ip/geo/v1/district/?key=xESpXp0MruowKbxqAlcqkKkt6KGiyGm8dUQf2y9h6vdh69bvDtkkQ7eEM5E9e0Zf&ip={ip_ip_response.get("ip")}&coordsys=WGS84"
                #
                # city_address_response = requests.get(city_address_url, timeout=timeout)
                #
                # if city_address_response.status_code == 200:
                #     city_string = city_address_response.json()['data']['country'] + city_address_response.json()['data']['prov'] + city_address_response.json()['data']['city']
                #     city_string = city_string.replace('市','').replace('区','').replace('县','')
                #     print(city_string)
                #     if check_city_address not in city_string:
                #         print("ip地区匹配失败")
                #         return False
                # else:
                #     print("获取城市数据失败")
                #     return False
                # # 验证代码是否是移动代理，家庭宽带，通过第三方离线库，或者api接口
                # ip_address_url = f"https://api.ipplus360.com/ip/info/v1/scene/?key=xESpXp0MruowKbxqAlcqkKkt6KGiyGm8dUQf2y9h6vdh69bvDtkkQ7eEM5E9e0Zf&ip={ip_ip_response.get("ip")}&lang=cn"
                #
                # ip_address_response = requests.get(test_url,timeout=timeout)
                #
                # if ip_address_response.status_code != 200:
                #     print("获取代理网络类型失败")
                #     return False
                # else:
                #     if is_mobile and ip_address_response.json()['data']['scene'] == '移动网络':
                #         print("获取移动网络成功")
                #     elif is_mobile is False and ip_address_response.json()['data']['scene'] == '家庭宽带':
                #         print('获取家庭带宽成功')
                #     else:
                #         return False
                #         print("获取数据失败")
                #
                # ip_address_risk_url = f"https://api.ipplus360.com/ip/info/v3/portrait/?key=poQvB8tJrgfBgsZsTHxNFDCKQr4HSBqYmGcaNIxk4jvfGztZ0twtKnJqHiqVOW8E&ip={ip_address_url}&coordsys=WGS84"
                #
                # ip_address_risk_response = requests.get(ip_address_risk_url,timeout=timeout)
                #
                # if ip_address_risk_response.status_code == 200:
                #     if ip_address_risk_response.json()['code'] == 200 and ip_address_risk_response.json()['data'] is None:
                #         print('该ip风险选项')
                #     else:
                #         print(f"风险选项是: {ip_address_risk_response.json()['data']['tag']}")
                #         return False
                # logger.info(f"代理验证成功: {proxy_config['ip']}:{proxy_config['port']}")
                return True
            else:
                logger.warning(f"代理验证失败 - 状态码: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"代理验证出错: {str(e)}")
            return False

    def add_ip_with_prefix_check(self,ip_list, new_ip):
        """
        使用集合优化前两段匹配检查
        """
        # 提取现有IP的前两段到集合中
        existing_prefixes = set()
        if ip_list is None:
            return False
        for ip in ip_list:
            segments = ip.split('.')
            if len(segments) >= 2:
                prefix = f"{segments[0]}.{segments[1]}"
                existing_prefixes.add(prefix)

        # 提取新IP的前两段
        new_segments = new_ip.split('.')
        if len(new_segments) < 2:
            # 如果IP格式不正确，添加到列表但返回False
            ip_list.append(new_ip)
            return False

        new_prefix = f"{new_segments[0]}.{new_segments[1]}"

        # 检查是否匹配
        is_match = new_prefix in existing_prefixes

        # 添加IP到列表
        if is_match is False:
           ip_list.append(new_ip)

        return is_match
    def parse_ipip_response(self,response_text):
        """
        解析myip.ipip.net响应
        """
        ip_pattern = r'当前 IP：(\d+\.\d+\.\d+\.\d+)'
        location_pattern = r'来自于：(.*)'

        ip_match = re.search(ip_pattern, response_text)
        location_match = re.search(location_pattern, response_text)

        return {
            'ip': ip_match.group(1) if ip_match else None,
            'location': location_match.group(1).strip() if location_match else None,
            'raw_response': response_text
        }

    def get_valid_proxy(self, pool_name: str = None,is_mobile=False,stats_manager=None) -> Optional[Dict]:
        """获取有效的代理"""
        max_retries = 2

        self.ip_list = stats_manager.stats.ip_address_list

        for attempt in range(max_retries):
            if pool_name:
                pools_to_try = [pool_name]
            else:
                pools_to_try = list(self.proxy_pools.keys())

            random.shuffle(pools_to_try)

            for pool in pools_to_try:
                proxy_config = self.get_proxy_from_pool(pool,is_mobile)
                if proxy_config and self.validate_proxy(proxy_config, 'http://myip.ipip.net',10,is_mobile):
                # if proxy_config and self.validate_proxy(proxy_config, 'https://www.ip138.com'):
                    return proxy_config

            time.sleep(2)  # 重试前等待

        return None