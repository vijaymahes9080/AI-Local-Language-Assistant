# LingoSphere AI - Launcher & Verification Orchestrator (Windows PowerShell)

Clear-Host
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                  LINGOSPHERE AI LOCAL GATEWAY                       " -ForegroundColor Magenta
Write-Host "     Startup-Grade Multilingual Assistant Platform (No-Docker)       " -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Seeded Credentials for Testing:" -ForegroundColor Yellow
Write-Host "  - Account Email: admin@lingosphere.ai" -ForegroundColor White
Write-Host "  - Security Key:  adminpass" -ForegroundColor White
Write-Host "  - Client Web Portal: http://localhost:3000" -ForegroundColor White
Write-Host "  - Admin Control Panel: http://localhost:3001" -ForegroundColor White
Write-Host ""

$Action = Read-Host @"
Select an operation to perform:
  [1] Install dependencies (Backend Python packages & Frontend node_modules)
  [2] Start FastAPI Backend Gateway Server (Port 8000)
  [3] Start Next.js Customer Web Application (Port 3000)
  [4] Start Next.js Admin Dashboard Console (Port 3001)
  [5] Run System Test Validation Suite (Pytest)
  [6] Exit Launcher
Choose an option (1-6)
"@

switch ($Action) {
    "1" {
        Write-Host "`n>>> Checking and installing Python virtual environment dependencies..." -ForegroundColor Green
        if (!(Test-Path "apps/backend/.venv")) {
            Write-Host "Creating Python virtual environment in apps/backend/.venv..." -ForegroundColor Cyan
            python -m venv apps/backend/.venv
        }
        Write-Host "Activating virtual environment & installing requirements.txt..." -ForegroundColor Cyan
        & "apps/backend/.venv/Scripts/pip" install -r apps/backend/requirements.txt
        
        Write-Host "`n>>> Installing root Node workspace dependencies..." -ForegroundColor Green
        npm install
        
        Write-Host "`nInstallation Completed! You are now ready to run the servers." -ForegroundColor Green
    }
    "2" {
        Write-Host "`n>>> Launching FastAPI Backend Server on port 8000..." -ForegroundColor Green
        $venvPip = "apps/backend/.venv/Scripts/pip"
        if (Test-Path $venvPip) {
            Write-Host "Using virtual environment Python runner..." -ForegroundColor Cyan
            & "apps/backend/.venv/Scripts/uvicorn" app.main:app --reload --port 8000 --app-dir apps/backend
        } else {
            Write-Host "Using global Python runner (ensure packages in requirements.txt are installed)..." -ForegroundColor Yellow
            uvicorn app.main:app --reload --port 8000 --app-dir apps/backend
        }
    }
    "3" {
        Write-Host "`n>>> Starting Next.js Customer Web Portal on http://localhost:3000..." -ForegroundColor Green
        npm run dev:web
    }
    "4" {
        Write-Host "`n>>> Starting Next.js Admin Panel Console on http://localhost:3001..." -ForegroundColor Green
        npm run dev:admin
    }
    "5" {
        Write-Host "`n>>> Running API, integration and unit security tests using Pytest..." -ForegroundColor Green
        $venvPip = "apps/backend/.venv/Scripts/pip"
        if (Test-Path $venvPip) {
            & "apps/backend/.venv/Scripts/pytest" apps/backend/tests -v
        } else {
            pytest apps/backend/tests -v
        }
    }
    "6" {
        Write-Host "`nExiting Launcher. Have a great day!" -ForegroundColor White
        Exit
    }
    Default {
        Write-Host "`nInvalid selection. Run the script again to select options 1 to 6." -ForegroundColor Red
    }
}
