with open("backend/tests/test_manual_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("app.dependency_overrides[get_current_user] = mock_get_current_user", 
                          "")

# We should put it inside the test setup
new_setup = """    def setUp(self):
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
    def tearDown(self):
        app.dependency_overrides.clear()
"""

content = content.replace("class TestManualScanRoute(unittest.TestCase):", "class TestManualScanRoute(unittest.TestCase):\n" + new_setup)

with open("backend/tests/test_manual_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
