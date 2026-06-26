import json

def json_script(value, element_id):
    json_str = json.dumps(value).translate(
        {
            ord(">"): "\\u003E",
            ord("<"): "\\u003C",
            ord("&"): "\\u0026",
        }
    )
    return '<script id="{}" type="application/json">{}</script>'.format(
        element_id, json_str
    )

print(json_script([{'role': 'agent', 'status': 'completed', 'result': 'coded', 'model_used': 'gpt-4o'}, {'role': 'auxiliary', 'status': 'failed', 'error': 'boom'}], 'deleg-data'))
