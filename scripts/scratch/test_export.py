import asyncio
from app.api.routes import export_full_report_excel

async def run():
    try:
        res = await export_full_report_excel(date=None, status="completed", mode="link")
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", type(e), e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    sys.path.append("/Users/admin/tescon/backend")
    import os
    os.chdir("/Users/admin/tescon/backend")
    asyncio.run(run())
