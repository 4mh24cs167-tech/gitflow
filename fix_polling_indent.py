with open("backend/app/workers/polling.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    for line in lines:
        if line.startswith("        response = await client.get(url, headers=headers)"):
            f.write("        " + line.strip() + "\n")
        elif line.startswith("        if response.status_code in (403, 429):"):
            f.write("        " + line.strip() + "\n")
        elif line.startswith("            reset_time = response.headers.get(\"x-ratelimit-reset\")"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            retry_after = response.headers.get(\"retry-after\")"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            wait_seconds = 60"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            import time"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            if retry_after:"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("                wait_seconds = int(retry_after)"):
            f.write("                " + line.strip() + "\n")
        elif line.startswith("            elif reset_time:"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("                wait_seconds = max(60, int(reset_time) - int(time.time()))"):
            f.write("                " + line.strip() + "\n")
        elif line.startswith("            print(f\"Rate limited by GitHub. Waiting {wait_seconds} seconds.\")"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            await asyncio.sleep(wait_seconds)"):
            f.write("            " + line.strip() + "\n")
        elif line.startswith("            continue"):
            f.write("            " + line.strip() + "\n")
        else:
            f.write(line)
