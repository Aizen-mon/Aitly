param(
    [switch]$FlutterAnalyze
)

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location "$repoRoot\backend"
try {
    python -m unittest discover -s tests -p "test_*.py"
} finally {
    Pop-Location
}

if ($FlutterAnalyze) {
    Push-Location "$repoRoot\frontend\flutter"
    try {
        flutter pub get
        flutter analyze
    } finally {
        Pop-Location
    }
}