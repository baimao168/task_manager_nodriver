
class Config:

    # 代理池配置
    # PROXY_POOLS = {
    #     'lt_proxy': {
    #         'api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
    #         'mobile_api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
    #         'auth_type': 'basic',
    #         'username': '',
    #         'password': '',
    #         'max_retries': 10
    #     },
    #     'qm_proxy': {
    #         'api_url': 'https://resource-extract.quanminip.com/ip?secret=qOfsYlSJ&num=1&port=2&type=txt&mr=1&sign=190dcc0a936fe58b3192e523c72fadba',
    #         'mobile_api_url': 'https://resource-extract.quanminip.com/ip?secret=qOfsYlSJ&num=1&port=2&type=txt&mr=1&sign=190dcc0a936fe58b3192e523c72fadba',
    #         'auth_type': 'basic',
    #         'username': '202510160595027050',
    #         'password': '6as7Wnaw',
    #         'max_retries': 10
    #     }
    # }
    PROXY_POOLS = {
        'qm_proxy': {
            'api_url': 'https://resource-extract.quanminip.com/ip?secret=qOfsYlSJ&num=1&port=2&type=txt&mr=1&sign=190dcc0a936fe58b3192e523c72fadba',
            'mobile_api_url': 'https://resource-extract.quanminip.com/ip?secret=qOfsYlSJ&num=1&port=2&type=txt&mr=1&sign=190dcc0a936fe58b3192e523c72fadba',
            'auth_type': 'basic',
            'username': '202510160595027050',
            'password': '6as7Wnaw',
            'max_retries': 10
        }
    }

    # PROXY_MOBILE_POOLS = {
    #     'qm_proxy': {
    #         'api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
    #         'mobile_api_url': 'https://www.lthttp.com/iplist?key=027228b7df6f2a18&count=1&protocol=0&type=1&isp=0&distinct=1&os=1&cs=0&is=0&es=0&textSep=0&isAuth=false&province=&city=',
    #         'auth_type': 'basic',
    #         'username': '',
    #         'password': '',
    #         'max_retries': 10
    #     }
    # }
