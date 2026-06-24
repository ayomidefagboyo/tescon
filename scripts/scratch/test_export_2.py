import asyncio
from app.api.routes import export_full_report_excel

async def run():
    try:
        res = await export_full_report_excel(date="2026-05-10", status="completed", mode="link")
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", type(e), e)

if __name__ == "__main__":
    import sys
    sys.path.append("/Users/admin/tescon/backend")
    import os
    os.chdir("/Users/admin/tescon/backend")
    asyncio.run(run())
