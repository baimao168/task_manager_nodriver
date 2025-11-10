
class Config:

    # 代理池配置
    PROXY_POOLS = {
        'lt_proxy': {
            'api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
            'mobile_api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
            'auth_type': 'basic',
            'username': '',
            'password': '',
            'max_retries': 10
        }
    }