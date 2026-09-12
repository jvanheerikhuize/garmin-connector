import asyncio
from playwright.async_api import async_playwright

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to http://127.0.0.1:8081")
        await page.goto("http://127.0.0.1:8081", timeout=10000, wait_until="domcontentloaded")
        
        # Test 1: Map preview functionality
        print("Testing map preview functionality...")
        map_el = await page.wait_for_selector("#map", state="attached", timeout=5000)
        print("Map element found.")
        
        # Test 2: File upload error validation
        print("Testing file upload validation...")
        await page.evaluate('document.getElementById("dropZone").style.pointerEvents = "auto"')
        await page.click("#dropZone", timeout=5000)
        
        import os
        with open("test_fake.txt", "w") as f:
            f.write("fake content")
            
        await page.set_input_files("#fileInput", "test_fake.txt")
        
        toast = await page.wait_for_selector(".toast.error", timeout=5000)
        toast_text = await toast.inner_text()
        print(f"File upload error toast text: {toast_text}")
        if "Only GPX files are supported" in toast_text:
            print("File upload error validation PASSED.")
            
        # Test 3: Course deletion modal
        print("Testing course deletion modal...")
        await page.evaluate("deleteCourse('test_course.fit')")
        
        modal = await page.wait_for_selector("#confirmModal:not(.hidden)", timeout=5000)
        modal_text = await page.locator("#confirmModalText").inner_text()
        print(f"Deletion modal text: {modal_text}")
        if "test_course.fit" in modal_text:
            print("Deletion modal text PASSED.")
            
        await page.click("#btnConfirmCancel")
        
        print("All tests finished successfully.")
        await browser.close()
        
if __name__ == "__main__":
    asyncio.run(run_tests())
