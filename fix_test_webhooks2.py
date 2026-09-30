with open("backend/tests/test_webhooks.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("}    payload_bytes =", "}\n    import json\n    payload_bytes =")

with open("backend/tests/test_webhooks.py", "w", encoding="utf-8") as f:
    f.write(content)
