from typing import Any, Dict, List


class NodriverResultParser:
    """nodriver 结果解析器"""

    @staticmethod
    def parse_result(raw_result: Any) -> Dict[str, Any]:
        """解析 nodriver 返回的复杂结果格式"""
        if raw_result is None:
            return {'success': False, 'error': '结果为None'}

        # 如果是字典，直接返回
        if isinstance(raw_result, dict):
            return raw_result

        # 如果是列表，处理 nodriver 的特殊格式
        if isinstance(raw_result, list):
            return NodriverResultParser._parse_list_format(raw_result)

        # 如果是基本类型，包装返回
        if isinstance(raw_result, (str, int, float, bool)):
            return {'success': True, 'result': raw_result}

        # 其他未知类型
        return {'success': False, 'error': f'未知结果类型: {type(raw_result)}'}

    @staticmethod
    def _parse_list_format(result_list: List) -> Dict[str, Any]:
        """解析列表格式的结果"""
        parsed = {'success': False}

        try:
            # 遍历列表中的每个键值对
            for item in result_list:
                if isinstance(item, list) and len(item) == 2:
                    key = item[0]
                    value_info = item[1]

                    # 提取实际值
                    if isinstance(value_info, dict):
                        value_type = value_info.get('type')
                        value = value_info.get('value')

                        if value_type == 'boolean':
                            parsed[key] = bool(value)
                        elif value_type == 'string':
                            parsed[key] = str(value)
                        elif value_type == 'number':
                            parsed[key] = float(value) if '.' in str(value) else int(value)
                        elif value_type == 'undefined':
                            parsed[key] = None
                        else:
                            parsed[key] = value
                    else:
                        parsed[key] = value_info
                else:
                    # 如果不是键值对格式，直接存储
                    parsed[str(len(parsed))] = item

            # 如果有success字段，设置主success
            if 'success' in parsed:
                parsed['success'] = bool(parsed['success'])
            else:
                parsed['success'] = True  # 默认成功

            return parsed

        except Exception as e:
            return {'success': False, 'error': f'解析列表格式失败: {e}', 'raw': str(result_list)}