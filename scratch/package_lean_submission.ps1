$base = "c:\Users\rasyaad\Downloads\PredictaGuard-main\PredictaGuard-main"
$sub = "$base\ASTRA_Project_Submission"

Write-Host "1. Generating 14-page official PDF report matching example..."
python "$base\scripts\generate_academic_pdf_report.py"

Write-Host "2. Rebuilding strict submission directory..."
if (Test-Path $sub) { Remove-Item $sub -Recurse -Force -ErrorAction SilentlyContinue }

New-Item -ItemType Directory -Path "$sub\01_Report_and_Documentation" -Force | Out-Null
New-Item -ItemType Directory -Path "$sub\02_Source_Code" -Force | Out-Null
New-Item -ItemType Directory -Path "$sub\02_Source_Code\ml" -Force | Out-Null
New-Item -ItemType Directory -Force -Path "$sub\03_Notebooks" | Out-Null
New-Item -ItemType Directory -Force -Path "$sub\04_Docker" | Out-Null
New-Item -ItemType Directory -Force -Path "$sub\05_Models_and_Data" | Out-Null

# 1. Reports
Copy-Item "$base\docs\WINTEQ_SmartMaint_AI_System_Documentation.pdf" "$sub\01_Report_and_Documentation\WINTEQ_SmartMaint_AI_System_Documentation.pdf" -Force
Copy-Item "$base\docs\Project_ASTRA_Technical_Report.md" "$sub\01_Report_and_Documentation\Project_ASTRA_Technical_Report.md" -Force

# 2. Source Code
Copy-Item "$base\dashboard" "$sub\02_Source_Code\dashboard" -Recurse -Force
Copy-Item "$base\scripts" "$sub\02_Source_Code\scripts" -Recurse -Force
Copy-Item "$base\run_dashboard.bat" "$sub\02_Source_Code\run_dashboard.bat" -Force
Copy-Item "$base\README.md" "$sub\02_Source_Code\README.md" -Force

Copy-Item "$base\ml\src" "$sub\02_Source_Code\ml\src" -Recurse -Force
Copy-Item "$base\ml\requirements.txt" "$sub\02_Source_Code\ml\requirements.txt" -Force
Copy-Item "$base\ml\README.md" "$sub\02_Source_Code\ml\README.md" -Force

# Clean __pycache__ from Source Code
Get-ChildItem "$sub\02_Source_Code" -Recurse -Include "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3. Notebooks
Get-ChildItem "$base\notebooks" | Copy-Item -Destination "$sub\03_Notebooks" -Force

# 4. Docker
Copy-Item "$base\Dockerfile" "$sub\04_Docker\Dockerfile" -Force
Copy-Item "$base\docker-compose.yml" "$sub\04_Docker\docker-compose.yml" -Force
Copy-Item "$base\docs\docker_setup_guide.md" "$sub\04_Docker\docker_setup_guide.md" -Force

# 5. Models & Data
Copy-Item "$base\ml\models" "$sub\05_Models_and_Data\models" -Recurse -Force
Copy-Item "$base\data" "$sub\05_Models_and_Data\data" -Recurse -Force
Get-ChildItem "$sub\05_Models_and_Data" -Recurse -Include "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Re-create ZIP archive
$zipPath = "$base\ASTRA_Project_Submission.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$sub\*" -DestinationPath $zipPath -Force

Write-Host "SUCCESS: Clean submission package with academic PDF ready!"
