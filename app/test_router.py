"""
Test router for running normalization tests via web interface.
"""
import subprocess
import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class TestRequest(BaseModel):
    test_type: str = "simple_debug"

class NormalizeRequest(BaseModel):
    text: str
    language: Optional[str] = "nl"

class NormalizeResponse(BaseModel):
    raw_text: str
    normalized_text: str
    language: str

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
        # Get the project root directory (where run_all_normalization_tests.py is located)
        base_dir = Path(__file__).parent.parent
        
        # Path to the comprehensive test script (runs ALL tests from test_normalization.py)
        script_path = base_dir / "run_all_normalization_tests.py"
        
        if not script_path.exists():
            return PlainTextResponse(
                f"Error: Test script not found at {script_path}\n\n"
                f"Available files in {base_dir}:\n" + 
                "\n".join([f.name for f in base_dir.iterdir() if f.is_file() and f.suffix == '.py'])
            )
        
        # Run the test script from the project root directory
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

@router.get("/run-test-direct", response_class=HTMLResponse)
async def run_test_direct():
    """Enhanced test page with normalization testing and comprehensive test runner."""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦷 Dental Normalization Test Suite</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        h1 {
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.2em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        h2 {
            color: #764ba2;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .text-input {
            width: 100%;
            min-height: 120px;
            padding: 15px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
            font-family: 'Courier New', monospace;
            resize: vertical;
            transition: border-color 0.3s ease;
        }
        .text-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            display: inline-block;
            margin: 10px 10px 10px 0;
            transition: all 0.3s ease;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .button:active {
            transform: translateY(0);
        }
        .button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .result-container {
            margin-top: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e9ecef;
        }
        .result-header {
            background: #667eea;
            color: white;
            padding: 10px 15px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .result-content {
            padding: 15px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.4;
        }
        .comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 15px;
        }
        .comparison-item {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #667eea;
        }
        .comparison-item h4 {
            margin-top: 0;
            color: #667eea;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .comparison-item .text {
            font-family: 'Courier New', monospace;
            background: white;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
            white-space: pre-wrap;
            min-height: 40px;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
            vertical-align: middle;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .status {
            margin: 15px 0;
            padding: 10px 15px;
            border-radius: 6px;
            font-weight: 500;
        }
        .status.loading {
            background: #e3f2fd;
            color: #1976d2;
            border: 1px solid #bbdefb;
        }
        .status.success {
            background: #e8f5e8;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
        }
        .status.error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
        }
        .examples {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }
        .examples h4 {
            margin-top: 0;
            color: #667eea;
        }
        .example-item {
            background: white;
            border-radius: 4px;
            padding: 8px 12px;
            margin: 8px 0;
            border-left: 3px solid #667eea;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: 'Courier New', monospace;
        }
        .example-item:hover {
            background: #f0f7ff;
            transform: translateX(3px);
        }
        .grid-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        @media (max-width: 768px) {
            .grid-layout {
                grid-template-columns: 1fr;
            }
            .comparison {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <h1>🦷 Dental Normalization Test Suite</h1>
    
    <div class="grid-layout">
        <!-- Free Text Normalization Section -->
        <div class="container">
            <h2>📝 Free Text Normalization</h2>
            <div class="section">
                <p>Enter any text to see how the normalization pipeline processes it:</p>
                
                <textarea id="inputText" class="text-input" placeholder="Enter dental text here, for example: 'karius op kies twee zes'"></textarea>
                
                <button id="normalizeBtn" class="button" onclick="normalizeText()">
                    🔄 Normalize Text
                </button>
                <button class="button" onclick="clearResults()">🗑️ Clear</button>
                
                <div id="normalizeStatus"></div>
                
                <div id="normalizeResults" style="display: none;">
                    <div class="comparison">
                        <div class="comparison-item">
                            <h4>📥 Original Text</h4>
                            <div id="originalText" class="text"></div>
                        </div>
                        <div class="comparison-item">
                            <h4>✨ Normalized Text</h4>
                            <div id="normalizedText" class="text"></div>
                        </div>
                    </div>
                </div>
                
                <div class="examples">
                    <h4>💡 Example Texts (Click to Try)</h4>
                    <div class="example-item" onclick="setExampleText('karius op kies twee zes')">
                        karius op kies twee zes
                    </div>
                    <div class="example-item" onclick="setExampleText('element 1, 2, 3')">
                        element 1, 2, 3
                    </div>
                    <div class="example-item" onclick="setExampleText('de 11 en de 21')">
                        de 11 en de 21
                    </div>
                    <div class="example-item" onclick="setExampleText('tand een vier met restauratie')">
                        tand een vier met restauratie
                    </div>
                    <div class="example-item" onclick="setExampleText('14;15;16 hebben behandeling nodig')">
                        14;15;16 hebben behandeling nodig
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Comprehensive Test Runner Section -->
        <div class="container">
            <h2>🧪 Comprehensive Test Runner</h2>
            <div class="section">
                <p>Run the complete normalization test suite to verify pipeline functionality:</p>
                
                <button id="runTestsBtn" class="button" onclick="runComprehensiveTests()">
                    🧪 Run All Tests
                </button>
                
                <div id="testStatus"></div>
                
                <div id="testResults" class="result-container" style="display: none;">
                    <div class="result-header">📊 Test Results</div>
                    <div id="testOutput" class="result-content"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Free Text Normalization Functions
        async function normalizeText() {
            const inputText = document.getElementById('inputText').value.trim();
            const normalizeBtn = document.getElementById('normalizeBtn');
            const statusDiv = document.getElementById('normalizeStatus');
            const resultsDiv = document.getElementById('normalizeResults');
            
            if (!inputText) {
                setStatus('error', '⚠️ Please enter some text to normalize');
                return;
            }
            
            // Update UI
            normalizeBtn.disabled = true;
            setStatus('loading', '🔄 Normalizing text...');
            resultsDiv.style.display = 'none';
            
            try {
                const response = await fetch('/normalize-text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: inputText,
                        language: 'nl'
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                // Display results
                document.getElementById('originalText').textContent = result.raw_text;
                document.getElementById('normalizedText').textContent = result.normalized_text;
                resultsDiv.style.display = 'block';
                
                if (result.raw_text === result.normalized_text) {
                    setStatus('success', '✅ No normalization changes needed');
                } else {
                    setStatus('success', '✅ Text normalized successfully');
                }
                
            } catch (error) {
                console.error('Normalization failed:', error);
                setStatus('error', `❌ Normalization failed: ${error.message}`);
            } finally {
                normalizeBtn.disabled = false;
            }
        }
        
        function setExampleText(text) {
            document.getElementById('inputText').value = text;
            normalizeText(); // Auto-normalize when example is clicked
        }
        
        function clearResults() {
            document.getElementById('inputText').value = '';
            document.getElementById('normalizeStatus').innerHTML = '';
            document.getElementById('normalizeResults').style.display = 'none';
        }
        
        // Comprehensive Test Runner Functions
        async function runComprehensiveTests() {
            const runTestsBtn = document.getElementById('runTestsBtn');
            const statusDiv = document.getElementById('testStatus');
            const resultsDiv = document.getElementById('testResults');
            const outputDiv = document.getElementById('testOutput');
            
            // Update UI
            runTestsBtn.disabled = true;
            setTestStatus('loading', '🧪 Running comprehensive test suite...');
            resultsDiv.style.display = 'none';
            outputDiv.textContent = '';
            
            try {
                const response = await fetch('/run-test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        test_type: 'comprehensive'
                    })
                });
                
                const result = await response.text();
                
                outputDiv.textContent = result;
                resultsDiv.style.display = 'block';
                
                if (response.ok) {
                    setTestStatus('success', '✅ Test suite completed');
                } else {
                    setTestStatus('error', '❌ Some tests may have failed');
                }
                
            } catch (error) {
                console.error('Test execution failed:', error);
                setTestStatus('error', `❌ Test execution failed: ${error.message}`);
                outputDiv.textContent = `Error: ${error.message}\\n\\nTo run tests manually:\\n1. Open terminal\\n2. Navigate to the pairing_server directory\\n3. Run: python3 run_all_normalization_tests.py`;
                resultsDiv.style.display = 'block';
            } finally {
                runTestsBtn.disabled = false;
            }
        }
        
        // Utility Functions
        function setStatus(type, message) {
            const statusDiv = document.getElementById('normalizeStatus');
            statusDiv.className = `status ${type}`;
            statusDiv.innerHTML = type === 'loading' ? `<span class="spinner"></span>${message}` : message;
        }
        
        function setTestStatus(type, message) {
            const statusDiv = document.getElementById('testStatus');
            statusDiv.className = `status ${type}`;
            statusDiv.innerHTML = type === 'loading' ? `<span class="spinner"></span>${message}` : message;
        }
        
        // Auto-focus on page load
        window.onload = function() {
            document.getElementById('inputText').focus();
        };
        
        // Enter key to normalize
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && event.ctrlKey) {
                normalizeText();
            }
        });
    </script>
</body>
</html>
    """)

@router.post("/normalize-text", response_model=NormalizeResponse)
async def normalize_text(request: NormalizeRequest, req: Request):
    """Normalize text using the configured normalization pipeline."""
    try:
        # Get the normalization pipeline from app state
        pipeline = getattr(req.app.state, 'normalization_pipeline', None)
        
        if not pipeline:
            return NormalizeResponse(
                raw_text=request.text,
                normalized_text=request.text,
                language=request.language
            )
        
        # Apply normalization
        result = pipeline.normalize(request.text, language=request.language)
        
        return NormalizeResponse(
            raw_text=request.text,
            normalized_text=result.normalized_text,
            language=request.language
        )
        
    except Exception as e:
        # If normalization fails, return raw text
        return NormalizeResponse(
            raw_text=request.text,
            normalized_text=f"Normalization failed: {str(e)}",
            language=request.language
        )

@router.get("/execute-python")
async def execute_python_fallback():
    """Fallback endpoint for Python script execution."""
    return await run_test_direct()