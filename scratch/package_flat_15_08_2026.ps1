$base = "c:\Users\rasyaad\Downloads\PredictaGuard-main\PredictaGuard-main"
$sub = "$base\15-08-2026"

Write-Host "1. Rebuilding clean submission folder: $sub"
if (-not (Test-Path $sub)) {
    New-Item -ItemType Directory -Path $sub -Force | Out-Null
}

# Generate notebook files
python "$base\scratch\build_notebooks.py"

# Generate matching Technical Report PDF
python "$base\scratch\generate_sample_matching_pdf.py"

# Copy flat Docker files & requirements
Copy-Item "$base\Dockerfile" "$sub\Dockerfile" -Force
Copy-Item "$base\docker-compose.yml" "$sub\docker-compose.yml" -Force
Copy-Item "$base\ml\requirements.txt" "$sub\requirements.txt" -Force

# Create ZIP archive
$zipPath = "$base\15-08-2026.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$sub\*" -DestinationPath $zipPath -Force

Write-Host "SUCCESS: Complete submission package with PDF report ready!"
