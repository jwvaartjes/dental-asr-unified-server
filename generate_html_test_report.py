#!/usr/bin/env python3
"""
Generate comprehensive HTML test report for normalization pipeline
Collects results from all test cases and formats them in a nice HTML table
"""

import sys
import os
import asyncio
import time
from typing import List, Tuple

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory, NormalizationPipeline


async def run_all_tests():
    """Run all normalization tests and collect results"""
    
    # Initialize DataRegistry properly (fixed the error!)
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    
    # Create pipeline for admin user
    pipeline = await NormalizationFactory.create_for_admin(registry)
    
    print("🧪 Running comprehensive normalization tests...")
    
    # COMPREHENSIVE TEST CASES - All dental terminology
    test_cases = [
        # ===== BASIC ELEMENT PARSING =====
        ("1-4", "element 14"),
        ("2-6", "element 26"),
        ("de 11", "element 11"),
        ("de 46", "element 46"),
        ("de element 14", "element 14"),
        ("cariës distaal van de 1-4", "cariës distaal van element 14"),
        ("1 -4", "element 14"),
        ("14", "element 14"),
        ("element 14", "element 14"),
        ("element 26", "element 26"),
        ("18", "element 18"),
        ("48", "element 48"),
        
        # ===== DUTCH NUMBER WORDS =====
        ("element een vier", "element 14"),
        ("element twee zes", "element 26"),
        ("element drie vijf", "element 35"),
        ("element vier acht", "element 48"),
        ("element een acht", "element 18"),
        ("element drie zes", "element 36"),
        ("element vier zeven", "element 47"),
        
        # ===== DENTAL CONTEXT TRIGGERS =====
        ("tand een vier", "tand 14"),
        ("kies twee zes", "kies 26"),
        ("tand 14", "tand 14"),
        ("kies 1-4", "kies 14"),
        ("molaar drie vijf", "molaar 35"),
        ("premolaar vier vier", "premolaar 44"),
        ("snijtand een een", "snijtand 11"),
        ("hoektand een drie", "hoektand 13"),
        
        # ===== SURFACE TERMINOLOGY - EXTENSIVE =====
        ("element 14 distaal", "element 14 distaal"),
        ("tand een vier distaal", "tand 14 distaal"),
        ("1-4 mesiopalatinaal", "element 14 mesiopalatinaal"),
        ("kies 26 buccaal", "kies 26 buccaal"),
        ("distaal element 14", "distaal element 14"),
        ("mesiopalatinaal tand 26", "mesiopalatinaal tand 26"),
        ("element 16 mesio-occlusaal", "element 16 mesio-occlusaal"),
        ("element 36 disto-occlusaal", "element 36 disto-occlusaal"),
        ("tand 24 mesio-occlusaal-distaal", "tand 24 mesio-occlusaal-distaal"),
        
        # ===== LICH-MUCOSAAL EN ANDERE OPPERVLAKKEN =====
        ("lich-mucosaal", "lich-mucosaal"),
        ("lich mucosaal", "lich mucosaal"),
        ("lichmucosaal", "lichmucosaal"),
        ("element 14 lich-mucosaal", "element 14 lich-mucosaal"),
        ("tand 26 lich mucosaal", "tand 26 lich mucosaal"),
        ("palatinaal", "palatinaal"),
        ("linguaal", "linguaal"),
        ("vestibulair", "vestibulair"),
        ("cervicaal", "cervicaal"),
        ("occlusaal", "occlusaal"),
        ("incisaal", "incisaal"),
        ("approximaal", "approximaal"),
        ("interproximaal", "interproximaal"),
        
        # ===== EXTENSIVE SURFACE COMBINATIONS =====
        ("mesio-buccaal", "mesio-buccaal"),
        ("disto-buccaal", "disto-buccaal"),
        ("mesio-linguaal", "mesio-linguaal"),
        ("disto-linguaal", "disto-linguaal"),
        ("mesio-palatinaal", "mesio-palatinaal"),
        ("disto-palatinaal", "disto-palatinaal"),
        ("mesio-occlusaal-distaal", "mesio-occlusaal-distaal"),
        ("mesio-occlusaal-buccaal", "mesio-occlusaal-buccaal"),
        ("disto-occlusaal-buccaal", "disto-occlusaal-buccaal"),
        ("mesio-occlusaal-linguaal", "mesio-occlusaal-linguaal"),
        ("disto-occlusaal-linguaal", "disto-occlusaal-linguaal"),
        
        # ===== DENTAL CONDITIONS & PROCEDURES =====
        ("karius", "cariës"),
        ("Karius", "cariës"),
        ("KARIUS", "cariës"),
        ("karius!", "cariës"),
        ("karius,", "cariës"),
        ("pulpitis", "pulpitis"),
        ("parodontitis", "parodontitis"),
        ("gingivitis", "gingivitis"),
        ("apicale parodontitis", "apicale parodontitis"),
        ("chronische parodontitis", "chronische parodontitis"),
        ("acute pulpitis", "acute pulpitis"),
        
        # ===== RESTORATION MATERIALS =====
        ("composiet", "composiet"),
        ("composiet restauratie", "composiet restauratie"),
        ("amalgaam", "amalgaam"),
        ("amalgaam vulling", "amalgaam vulling"),
        ("keramiek", "keramiek"),
        ("goud", "goud"),
        ("porselein", "porselein"),
        ("glasionomeer", "glasionomeer"),
        ("tijdelijke vulling", "tijdelijke vulling"),
        
        # ===== RESTORATION TYPES =====
        ("inlay", "inlay"),
        ("onlay", "onlay"),
        ("kroon", "kroon"),
        ("brug", "brug"),
        ("implantaat", "implantaat"),
        ("prothese", "prothese"),
        ("gebitsprothese", "gebitsprothese"),
        ("frameprothese", "frameprothese"),
        ("partiele prothese", "partiële prothese"),
        
        # ===== SURFACE CORRECTIONS & VARIANTS =====
        ("bukkaal", "buccaal"),
        ("bukaal", "buccaal"),
        ("festubilair", "vestibulair"),
        ("festibulaal", "vestibulair"),
        ("lingaal", "linguaal"),
        ("palatinaal", "palatinaal"),
        ("palataal", "palatinaal"),
        ("oklusaal", "occlusaal"),
        ("okklusaal", "occlusaal"),
        ("incisaal", "incisaal"),
        ("insisaal", "incisaal"),
        
        # ===== CLINICAL TERMINOLOGY =====
        ("circa", "ca."),
        ("Circa", "ca."),
        ("CIRCA", "ca."),
        ("parodontaal", "parodontaal"),
        ("gingivaal", "gingivaal"),
        ("alveolaire", "alveolaire"),
        ("cemento-email grens", "cemento-email grens"),
        ("cemento-email-grens", "cemento-email-grens"),
        ("CEJ", "CEJ"),
        ("pulpakamer", "pulpakamer"),
        ("wortelkanaal", "wortelkanaal"),
        ("apex", "apex"),
        ("foramen apicale", "foramen apicale"),
        
        # ===== PATHOLOGY & DIAGNOSIS =====
        ("necrose", "necrose"),
        ("pulpanecrose", "pulpanecrose"),
        ("abces", "abces"),
        ("fistel", "fistel"),
        ("granuloom", "granuloom"),
        ("cyste", "cyste"),
        ("resorptie", "resorptie"),
        ("interne resorptie", "interne resorptie"),
        ("externe resorptie", "externe resorptie"),
        ("fractuur", "fractuur"),
        ("verticale fractuur", "verticale fractuur"),
        ("horizontale fractuur", "horizontale fractuur"),
        
        # ===== PERIODONTAL TERMS =====
        ("tandvleesrand", "tandvleesrand"),
        ("gingivarand", "gingivarand"),
        ("sulcus", "sulcus"),
        ("pocketdiepte", "pocketdiepte"),
        ("bleeding on probing", "bleeding on probing"),
        ("BOP", "BOP"),
        ("plaque", "plaque"),
        ("tandsteen", "tandsteen"),
        ("calculus", "calculus"),
        ("biofilm", "biofilm"),
        
        # ===== TREATMENT PROCEDURES =====
        ("wortelkanaalbehandeling", "wortelkanaalbehandeling"),
        ("endodontie", "endodontie"),
        ("extractie", "extractie"),
        ("extractie element", "extractie element"),
        ("chirurgische extractie", "chirurgische extractie"),
        ("scaling", "scaling"),
        ("root planing", "root planing"),
        ("curettage", "curettage"),
        ("debridement", "debridement"),
        
        # ===== COMPLEX COMBINATIONS =====
        ("cariës distaal van de 1-4", "cariës distaal van element 14"),
        ("element een vier distaal", "element 14 distaal"),
        ("karius op kies twee zes", "cariës op kies 26"),
        ("composiet restauratie element 16 mesio-occlusaal", "composiet restauratie element 16 mesio-occlusaal"),
        ("amalgaam vulling tand 36 disto-occlusaal", "amalgaam vulling tand 36 disto-occlusaal"),
        ("kroon op element 14 met lich-mucosaal preparaat", "kroon op element 14 met lich-mucosaal preparaat"),
        ("extractie van element vier zes", "extractie van element 46"),
        ("wortelkanaalbehandeling element drie zes", "wortelkanaalbehandeling element 36"),
        
        # ===== COMMA-SEPARATED TESTS (should NOT combine) =====
        ("1, 2, 3", "1, 2, 3"),
        ("1, 2, 3, 4", "1, 2, 3, 4"),
        ("5, 6, 7, 8", "5, 6, 7, 8"),
        ("element 14, element 26", "element 14, element 26"),
        ("tand 11, tand 21", "tand 11, tand 21"),
        
        # ===== HYPHENATED RANGES (SHOULD work) =====
        ("1-4", "element 14"),
        ("2-6", "element 26"),
        ("3-5", "element 35"),
        ("4-7", "element 47"),
        ("1-8", "element 18"),
        ("3-6", "element 36"),
        ("4-6", "element 46"),
        ("2-4", "element 24"),
        
        # ===== ELEMENT WITH HYPHEN =====
        ("element 1-4", "element 14"),
        ("element 2-6", "element 26"),
        ("tand 3-5", "tand 35"),
        ("kies 4-8", "kies 48"),
        ("molaar 1-6", "molaar 16"),
        ("premolaar 2-4", "premolaar 24"),
        
        # ===== PERIOD-SEPARATED (should NOT combine) =====
        ("1. 2", "1. 2"),
        ("1.2", "1.2"),
        ("3.4", "3.4"),
        ("2.5", "2.5"),
        ("1.5 mm", "1.5 mm"),
        ("3.2 mm", "3.2 mm"),
        
        # ===== ADDITIONAL TOOTH TYPES =====
        ("centrale snijtand", "centrale snijtand"),
        ("laterale snijtand", "laterale snijtand"),
        ("hoektand", "hoektand"),
        ("canine", "canine"),
        ("eerste premolaar", "eerste premolaar"),
        ("tweede premolaar", "tweede premolaar"),
        ("eerste molaar", "eerste molaar"),
        ("tweede molaar", "tweede molaar"),
        ("derde molaar", "derde molaar"),
        ("verstandskies", "verstandskies"),
        ("melktand", "melktand"),
        ("blijvende tand", "blijvende tand"),
        
        # ===== QUADRANT TERMINOLOGY =====
        ("eerste kwadrant", "eerste kwadrant"),
        ("tweede kwadrant", "tweede kwadrant"),
        ("derde kwadrant", "derde kwadrant"),
        ("vierde kwadrant", "vierde kwadrant"),
        ("bovenkant rechts", "bovenkant rechts"),
        ("bovenkant links", "bovenkant links"),
        ("onderkant links", "onderkant links"),
        ("onderkant rechts", "onderkant rechts"),
        
        # ===== MEASUREMENT & CLINICAL VALUES =====
        ("2 mm", "2 mm"),
        ("3.5 mm", "3.5 mm"),
        ("pocket 4 mm", "pocket 4 mm"),
        ("BOP positief", "BOP positief"),
        ("BOP negatief", "BOP negatief"),
        ("mobiliteit graad 1", "mobiliteit graad 1"),
        ("mobiliteit graad 2", "mobiliteit graad 2"),
        ("mobiliteit graad 3", "mobiliteit graad 3"),
    ]
    
    print(f"📊 Testing {len(test_cases)} cases...")
    
    results = []
    passed = 0
    failed = 0
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        start_time = time.time()
        try:
            # Run normalization
            result = pipeline.normalize(input_text)
            actual = result.normalized_text
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Check if test passed
            success = actual == expected
            if success:
                passed += 1
                status = "✅ PASS"
            else:
                failed += 1
                status = "❌ FAIL"
            
            # Store result
            results.append({
                'test_num': i,
                'input': input_text,
                'expected': expected,
                'actual': actual,
                'success': success,
                'status': status,
                'time_ms': elapsed_ms
            })
            
            print(f"{status} {elapsed_ms:6.1f}ms: \"{input_text}\" → \"{actual}\"")
            if not success:
                print(f"              Expected: \"{expected}\"")
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            failed += 1
            results.append({
                'test_num': i,
                'input': input_text,
                'expected': expected,
                'actual': f"ERROR: {e}",
                'success': False,
                'status': "💥 ERROR",
                'time_ms': elapsed_ms
            })
            print(f"💥 {elapsed_ms:6.1f}ms: \"{input_text}\" → ERROR: {e}")
    
    print(f"\n📊 Test Summary:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📝 Total: {len(test_cases)}")
    
    return results


def generate_html_report(results: List[dict]) -> str:
    """Generate HTML report from test results"""
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    total_time = sum(r['time_ms'] for r in results)
    avg_time = total_time / len(results) if results else 0
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dental Normalization Test Results</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            display: flex;
            justify-content: space-around;
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .summary-item {{
            text-align: center;
        }}
        .summary-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .summary-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .passed {{ color: #27ae60; }}
        .failed {{ color: #e74c3c; }}
        .total {{ color: #3498db; }}
        .time {{ color: #f39c12; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #bdc3c7;
        }}
        th {{
            background-color: #34495e;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e8f4fd;
        }}
        .status {{
            font-weight: bold;
            text-align: center;
        }}
        .pass {{ background-color: #d4edda; color: #155724; }}
        .fail {{ background-color: #f8d7da; color: #721c24; }}
        .error {{ background-color: #f5c6cb; color: #721c24; }}
        
        .input-col {{ 
            max-width: 200px; 
            word-wrap: break-word; 
            background-color: #e3f2fd;
        }}
        .expected-col {{ 
            max-width: 200px; 
            word-wrap: break-word; 
            background-color: #e8f5e8;
        }}
        .actual-col {{ 
            max-width: 200px; 
            word-wrap: break-word; 
        }}
        .time-col {{ 
            text-align: right; 
            color: #f39c12;
            font-family: monospace;
        }}
        .test-num {{ 
            text-align: center; 
            font-weight: bold;
            color: #3498db;
        }}
        
        .filter-bar {{
            margin: 20px 0;
            text-align: center;
        }}
        .filter-btn {{
            margin: 0 10px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }}
        .filter-all {{ background-color: #3498db; color: white; }}
        .filter-pass {{ background-color: #27ae60; color: white; }}
        .filter-fail {{ background-color: #e74c3c; color: white; }}
        
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #bdc3c7;
            text-align: center;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🦷 Dental Normalization Pipeline Test Results</h1>
        
        <div class="summary">
            <div class="summary-item">
                <div class="summary-value passed">{passed}</div>
                <div class="summary-label">Passed</div>
            </div>
            <div class="summary-item">
                <div class="summary-value failed">{failed}</div>
                <div class="summary-label">Failed</div>
            </div>
            <div class="summary-item">
                <div class="summary-value total">{len(results)}</div>
                <div class="summary-label">Total Tests</div>
            </div>
            <div class="summary-item">
                <div class="summary-value time">{avg_time:.1f}ms</div>
                <div class="summary-label">Avg Time</div>
            </div>
        </div>
        
        <div class="filter-bar">
            <button class="filter-btn filter-all" onclick="filterRows('all')">Show All</button>
            <button class="filter-btn filter-pass" onclick="filterRows('pass')">Show Passed</button>
            <button class="filter-btn filter-fail" onclick="filterRows('fail')">Show Failed</button>
        </div>
        
        <table id="results-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Input Text</th>
                    <th>Expected Output</th>
                    <th>Actual Output</th>
                    <th>Status</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>"""
    
    # Add table rows
    for result in results:
        status_class = "pass" if result['success'] else ("error" if "ERROR" in result['actual'] else "fail")
        row_class = "pass-row" if result['success'] else "fail-row"
        
        html += f"""
                <tr class="{row_class}">
                    <td class="test-num">{result['test_num']}</td>
                    <td class="input-col">"{result['input']}"</td>
                    <td class="expected-col">"{result['expected']}"</td>
                    <td class="actual-col">"{result['actual']}"</td>
                    <td class="status {status_class}">{result['status']}</td>
                    <td class="time-col">{result['time_ms']:.1f}ms</td>
                </tr>"""
    
    html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🧪 Dutch Dental ASR Normalization Pipeline | Total processing time: {total_time:.1f}ms</p>
        </div>
    </div>
    
    <script>
        function filterRows(filter) {{
            const table = document.getElementById('results-table');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {{
                if (filter === 'all') {{
                    row.style.display = '';
                }} else if (filter === 'pass') {{
                    row.style.display = row.classList.contains('pass-row') ? '' : 'none';
                }} else if (filter === 'fail') {{
                    row.style.display = row.classList.contains('fail-row') ? '' : 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""
    
    return html


async def main():
    """Main function to run tests and generate HTML report"""
    print("🚀 Starting comprehensive test run...")
    
    # Run all tests
    results = await run_all_tests()
    
    # Generate HTML report
    html_content = generate_html_report(results)
    
    # Save to file
    html_file = "/tmp/dental_normalization_test_results.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ HTML report generated: {html_file}")
    print(f"🌐 Open in browser: file://{html_file}")
    
    return html_file


if __name__ == "__main__":
    asyncio.run(main())