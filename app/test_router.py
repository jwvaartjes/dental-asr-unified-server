"""
Test router for running normalization tests via web interface.
"""
import subprocess
import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

router = APIRouter()

class TestRequest(BaseModel):
    test_type: str = "simple_debug"

@router.get("/test-normalization", response_class=HTMLResponse)
async def serve_test_page():
    """Serve the normalization test page."""
    html_path = Path(__file__).parent.parent / "test_normalization_button.html"
    
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Update the JavaScript to use the correct API endpoint
        html_content = html_content.replace(
            '/api/run-test',
            '/run-test'
        ).replace(
            '/api/execute-python', 
            '/execute-python'
        )
        
        return HTMLResponse(html_content)
    else:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Page Not Found</title></head>
        <body>
            <h1>Test page not found</h1>
            <p>The test HTML file could not be located.</p>
            <p>Expected location: {}</p>
            <button onclick="location.href='/run-test-direct'">Run Test Direct</button>
        </body>
        </html>
        """.format(html_path))

@router.post("/run-test")
async def run_normalization_test(request: TestRequest):
    """Run the normalization test and return results."""
    try:
        # Get the pairing_server directory (where debug_simple.py is located)
        base_dir = Path(__file__).parent.parent
        
        # Path to the comprehensive test script (runs ALL tests from test_normalization.py)
        script_path = base_dir / "run_all_normalization_tests.py"
        
        if not script_path.exists():
            return PlainTextResponse(
                f"Error: Test script not found at {script_path}\n\n"
                f"Available files in {base_dir}:\n" + 
                "\n".join([f.name for f in base_dir.iterdir() if f.is_file() and f.suffix == '.py'])
            )
        
        # Run the test script
        result = subprocess.run(
            ["python3", str(script_path)],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Format the output
        output = f"Exit code: {result.returncode}\n\n"
        output += "STDOUT:\n" + "="*50 + "\n"
        output += result.stdout + "\n\n"
        
        if result.stderr:
            output += "STDERR:\n" + "="*50 + "\n"
            output += result.stderr + "\n"
        
        return PlainTextResponse(output)
        
    except subprocess.TimeoutExpired:
        return PlainTextResponse("Error: Test execution timed out after 60 seconds")
    except Exception as e:
        return PlainTextResponse(f"Error executing test: {str(e)}")

@router.get("/run-test-direct")
async def run_test_direct():
    """Direct test execution endpoint."""
    try:
        # Get the pairing_server directory (where comprehensive test script is located)
        base_dir = Path(__file__).parent.parent
        script_path = base_dir / "run_all_normalization_tests.py"
        
        if not script_path.exists():
            available_scripts = [f.name for f in base_dir.iterdir() if f.is_file() and f.suffix == '.py']
            return PlainTextResponse(
                f"❌ Script not found: {script_path}\n\n"
                f"📁 Base directory: {base_dir}\n"
                f"📄 Available Python scripts:\n" + 
                "\n".join(f"  • {script}" for script in available_scripts)
            )
        
        # Execute the script
        result = subprocess.run(
            ["python3", str(script_path)],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = f"🧪 Normalization Test Results\n{'='*60}\n\n"
        output += f"📍 Script: {script_path.name}\n"
        output += f"📂 Working directory: {base_dir}\n"
        output += f"🔢 Exit code: {result.returncode}\n\n"
        
        if result.stdout:
            output += "📊 Test Output:\n" + "-"*40 + "\n"
            output += result.stdout + "\n\n"
        
        if result.stderr:
            output += "⚠️ Error Output:\n" + "-"*40 + "\n"  
            output += result.stderr + "\n"
        
        return PlainTextResponse(output, media_type="text/plain; charset=utf-8")
        
    except subprocess.TimeoutExpired:
        return PlainTextResponse("⏱️ Error: Test execution timed out after 60 seconds")
    except Exception as e:
        return PlainTextResponse(f"💥 Error: {str(e)}")

@router.get("/execute-python")
async def execute_python_fallback():
    """Fallback endpoint for Python script execution."""
    return await run_test_direct()