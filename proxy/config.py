
class Config:

    # 代理池配置
    PROXY_POOLS = {
        'lt_proxy': {
            'api_url': 'https://www.lthttp.com/iplist?key=1b94ee57171ef054&count=1&protocol=0&type=1&isp=0&distinct=0&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
            'mobile_api_url': 'https://www.lthttp.com/iplist?key=1b94ee57171ef054&count=1&protocol=0&type=1&isp=0&distinct=0&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
            'auth_type': 'basic',
            'username': '7df5dbf022185187',
            'password': 'a627011dddd743ef8935aa804d61af20',
            'max_retries': 3
        }
    }