@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem start.bat - Verify installation, start FastAPI backend + React/Vite
rem             frontend (default), and open the web app automatically.
rem             Also supports API-only, Frontend-only, MLflow, Dashboard,
rem             and Docker Compose modes.
rem ============================================================================

cd /d "%~dp0"

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MLFLOW_DISABLE_AGENT_HINT=1"

set "MODE=fullstack"
set "HOST=127.0.0.1"
set "PORT=8000"
set "FE_PORT=5173"
set "PORT_SET=0"
set "RELOAD_FLAG="
set "OPEN_BROWSER=1"
set "ALLOW_DEGRADED=0"
set "CHECK_ONLY=0"
set "NO_PAUSE=0"

for %%A in (%*) do (
    if /i "%%~A"=="--no-pause" set "NO_PAUSE=1"
)

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--host" (
    if "%~2"=="" goto :missing_arg
    set "HOST=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--port" (
    if "%~2"=="" goto :missing_arg
    set "PORT=%~2"
    set "FE_PORT=%~2"
    set "PORT_SET=1"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--reload" (
    set "RELOAD_FLAG=--reload"
    shift
    goto :parse_args
)
if /i "%~1"=="--open" (
    set "OPEN_BROWSER=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--no-open" (
    set "OPEN_BROWSER=0"
    shift
    goto :parse_args
)
if /i "%~1"=="--fullstack" (
    set "MODE=fullstack"
    shift
    goto :parse_args
)
if /i "%~1"=="--api" (
    set "MODE=api"
    shift
    goto :parse_args
)
if /i "%~1"=="--frontend" (
    set "MODE=frontend"
    shift
    goto :parse_args
)
if /i "%~1"=="--prod" (
    set "MODE=prod"
    shift
    goto :parse_args
)
if /i "%~1"=="--mlflow" (
    set "MODE=mlflow"
    shift
    goto :parse_args
)
if /i "%~1"=="--dashboard" (
    set "MODE=dashboard"
    shift
    goto :parse_args
)
if /i "%~1"=="--docker" (
    set "MODE=docker"
    shift
    goto :parse_args
)
if /i "%~1"=="--allow-degraded" (
    set "ALLOW_DEGRADED=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--check-only" (
    set "CHECK_ONLY=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :usage
if /i "%~1"=="-h" goto :usage
if "%~1"=="/?" goto :usage
echo [ERROR] Unknown argument: %~1
echo Run "start.bat --help" for usage information.
goto :fail

:missing_arg
echo [ERROR] Missing value for %~1.
goto :fail

:usage
echo.
echo Usage: start.bat [OPTIONS]
echo.
echo By default, verifies all backend + model + frontend installations, starts the
echo FastAPI backend ^(http://127.0.0.1:8000^), starts the React/Vite frontend
echo ^(http://127.0.0.1:5173^), and opens the web UI in your browser.
echo.
echo Modes:
echo   ^(default^)         Verify everything and start Backend + Frontend together
echo   --fullstack       Explicit alias for default Backend + Frontend mode
echo   --api             Start FastAPI backend server only ^(http://127.0.0.1:8000^)
echo   --frontend        Start React/Vite frontend only ^(http://127.0.0.1:5173^)
echo   --prod            Start FastAPI with config\production.yaml ^(APP_ENV=production^)
echo   --mlflow          Start MLflow Tracking UI ^(default port 5000^)
echo   --dashboard       Open the HTML monitoring dashboard in your browser
echo   --docker          Build and start API + MLflow via Docker Compose
echo.
echo Options:
echo   --host HOST       Bind host address ^(default: 127.0.0.1^)
echo   --port PORT       Override port ^(default: 8000 API / 5173 Frontend / 5000 MLflow^)
echo   --reload          Enable uvicorn auto-reload in --api mode
echo   --open            Open web UI / docs in default browser ^(enabled by default^)
echo   --no-open         Do not automatically open the browser
echo   --allow-degraded  Start API even if models\house_price_pipeline.joblib is missing
echo   --check-only      Verify all installations and artifacts, then exit
echo   --no-pause        Do not pause on error
echo   --help, -h        Show this help message and exit
echo.
exit /b 0

:args_done
if /i "%MODE%"=="docker" goto :run_docker
if /i "%MODE%"=="dashboard" goto :run_dashboard

if /i "%MODE%"=="frontend" (
    call :verify_frontend
    if errorlevel 1 goto :fail
    if "%CHECK_ONLY%"=="1" (
        echo [OK] Frontend installation checks passed.
        exit /b 0
    )
    goto :run_frontend_only
)

call :verify_backend
if errorlevel 1 goto :fail

if /i "%MODE%"=="mlflow" (
    if "%CHECK_ONLY%"=="1" (
        echo [OK] Backend and MLflow checks passed.
        exit /b 0
    )
    goto :run_mlflow
)

call :verify_model
if errorlevel 1 goto :fail

if /i "%MODE%"=="api" (
    if "%CHECK_ONLY%"=="1" (
        echo [OK] Backend and model checks passed.
        exit /b 0
    )
    goto :run_api_only
)

if /i "%MODE%"=="prod" (
    if "%CHECK_ONLY%"=="1" (
        echo [OK] Production backend and model checks passed.
        exit /b 0
    )
    goto :run_prod
)

rem Default fullstack mode: also verify frontend installation before starting anything
call :verify_frontend
if errorlevel 1 goto :fail

if "%CHECK_ONLY%"=="1" (
    echo.
    echo [OK] All installation and model checks passed. Ready to run start.bat.
    exit /b 0
)
goto :run_fullstack

rem ============================================================================
rem Verification Subroutines
rem ============================================================================

:verify_backend
echo [Check] Verifying Python virtual environment and backend packages...
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Python virtual environment not found at ".venv\Scripts\python.exe".
    echo         Run setup.bat first to create .venv and install dependencies.
    exit /b 1
)
"%VENV_PYTHON%" -c "import importlib.metadata, fastapi, uvicorn, pydantic, joblib, pandas, numpy, sklearn, lightgbm, yaml, src.api.app, src.pipeline.inference_pipeline; importlib.metadata.version('house-price-prediction')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Required Python packages or local package are missing or broken in .venv.
    echo         Run setup.bat to install all required Python dependencies.
    exit /b 1
)
echo [OK] Python .venv and FastAPI/ML packages verified.
exit /b 0

:verify_model
echo [Check] Verifying trained model artifacts...
if exist "models\house_price_pipeline.joblib" (
    if not exist "models\metadata.json" (
        echo [WARN] models\metadata.json not found; API will use fallback metadata.
    ) else (
        echo [OK] Trained pipeline and metadata verified ^(models\house_price_pipeline.joblib^).
    )
    exit /b 0
)
if "%ALLOW_DEGRADED%"=="1" (
    echo [WARN] Model artifact missing; API will start in degraded mode ^(/predict returns 503^).
    exit /b 0
)
echo [ERROR] Trained model artifact not found: "models\house_price_pipeline.joblib".
echo         Run setup.bat first to train and serialize the pipeline,
echo         or pass --allow-degraded to start the API in degraded mode.
exit /b 1

:verify_frontend
echo [Check] Verifying Node.js, npm, and React frontend dependencies...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH.
    echo         Install Node.js LTS from https://nodejs.org/ and run setup.bat.
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    exit /b 1
)
if not exist "frontend\package.json" (
    echo [ERROR] Frontend manifest missing at "frontend\package.json".
    exit /b 1
)
if not exist "frontend\node_modules\vite\bin\vite.js" (
    echo [ERROR] Frontend dependencies are not installed ^(frontend\node_modules missing^).
    echo         Run setup.bat first to install frontend packages.
    exit /b 1
)
if not exist "frontend\node_modules\react\package.json" (
    echo [ERROR] React package is missing in frontend\node_modules.
    echo         Run setup.bat to repair frontend dependencies.
    exit /b 1
)
echo [OK] Node.js and React/Vite frontend dependencies verified.
exit /b 0

rem ============================================================================
rem Launch Modes
rem ============================================================================

:run_fullstack
set "API_PORT=8000"
if "%PORT_SET%"=="1" set "FE_PORT=%PORT%"
set "DISPLAY_HOST=%HOST%"
if "%HOST%"=="0.0.0.0" set "DISPLAY_HOST=127.0.0.1"

echo.
echo [Launch 1/2] Checking FastAPI backend port ^(starting from %API_PORT%^)...
set "API_MODE=start"
for /f "tokens=1,2 delims=:" %%A in ('"%VENV_PYTHON%" scripts\resolve_port.py --mode api --host 127.0.0.1 --start %API_PORT%') do (
    set "API_MODE=%%A"
    set "API_PORT=%%B"
)

if "%API_PORT%"=="0" (
    echo [ERROR] Could not find an available backend port between 8000 and 8020.
    goto :fail
)

if /i "%API_MODE%"=="reuse" (
    echo [OK] Reusing existing House Price API on http://127.0.0.1:%API_PORT%.
) else (
    if not "%API_PORT%"=="8000" (
        echo [INFO] Port 8000 is busy; automatically switched backend to port %API_PORT%.
    )
    start "House Price Prediction - Backend API (%API_PORT%)" "%VENV_PYTHON%" -m uvicorn src.api.app:app --host 127.0.0.1 --port %API_PORT%
    echo Waiting for FastAPI backend on port %API_PORT% to load model...
    set "API_READY=0"
    for /L %%I in (1,1,30) do (
        if "!API_READY!"=="0" (
            "%VENV_PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:%API_PORT%/health', timeout=1.5); raise SystemExit(0 if r.status==200 else 1)" >nul 2>&1
            if not errorlevel 1 (
                set "API_READY=1"
            ) else (
                ping -n 2 127.0.0.1 >nul
            )
        )
    )
    if "!API_READY!"=="0" (
        echo [ERROR] FastAPI backend did not respond on http://127.0.0.1:%API_PORT%/health within 30s.
        echo         Check the "House Price Prediction - Backend API (%API_PORT%)" window for details.
        goto :fail
    )
    echo [OK] FastAPI backend is live and healthy on http://127.0.0.1:%API_PORT%.
)

echo.
echo [Launch 2/2] Checking React + Vite frontend port ^(starting from %FE_PORT%^)...
set "SELECTED_FE_PORT=0"
for /f "delims=" %%P in ('"%VENV_PYTHON%" scripts\resolve_port.py --mode free --host 127.0.0.1 --start %FE_PORT%') do set "SELECTED_FE_PORT=%%P"

if "%SELECTED_FE_PORT%"=="0" (
    echo [ERROR] Could not find an available frontend port starting from %FE_PORT%.
    goto :fail
)
if not "%SELECTED_FE_PORT%"=="%FE_PORT%" (
    echo [INFO] Port %FE_PORT% is busy; automatically switched frontend to port %SELECTED_FE_PORT%.
)
set "FE_PORT=%SELECTED_FE_PORT%"
set "VITE_API_PROXY_TARGET=http://127.0.0.1:%API_PORT%"

echo ============================================================================
echo   House Price Prediction - Full Stack Running
echo ============================================================================
echo   Frontend UI  : http://%DISPLAY_HOST%:%FE_PORT%
echo   Backend API  : http://127.0.0.1:%API_PORT%
echo   API Proxy    : /api -^> %VITE_API_PROXY_TARGET%
echo   Swagger Docs : http://127.0.0.1:%API_PORT%/docs
echo.
echo   Press Ctrl+C to stop the frontend ^(close the API window to stop backend^).
echo ============================================================================
echo.

set "VITE_OPEN_FLAG="
if "%OPEN_BROWSER%"=="1" set "VITE_OPEN_FLAG=--open"
call npm --prefix frontend run dev -- --host %HOST% --port %FE_PORT% %VITE_OPEN_FLAG%
if errorlevel 1 (
    echo [ERROR] Frontend dev server exited with an error.
    goto :fail
)
exit /b 0

:run_api_only
set "DISPLAY_HOST=%HOST%"
if "%HOST%"=="0.0.0.0" set "DISPLAY_HOST=127.0.0.1"
echo ============================================================================
echo   House Price Prediction - FastAPI Inference Server
echo ============================================================================
echo   Swagger Docs : http://%DISPLAY_HOST%:%PORT%/docs
echo   ReDoc        : http://%DISPLAY_HOST%:%PORT%/redoc
echo   Health Check : http://%DISPLAY_HOST%:%PORT%/health
echo   Model Info   : http://%DISPLAY_HOST%:%PORT%/model/info
echo   Press Ctrl+C to stop the server.
echo ============================================================================
echo.
if "%OPEN_BROWSER%"=="1" (
    start "" "http://%DISPLAY_HOST%:%PORT%/docs"
)
"%VENV_PYTHON%" -m uvicorn src.api.app:app --host %HOST% --port %PORT% %RELOAD_FLAG%
if errorlevel 1 (
    echo [ERROR] FastAPI server exited with an error.
    goto :fail
)
exit /b 0

:run_frontend_only
if "%PORT_SET%"=="0" set "FE_PORT=5173"
set "DISPLAY_HOST=%HOST%"
if "%HOST%"=="0.0.0.0" set "DISPLAY_HOST=127.0.0.1"
echo ============================================================================
echo   House Price Prediction - React + Vite Frontend
echo ============================================================================
echo   Frontend URL : http://%DISPLAY_HOST%:%FE_PORT%
echo   API Proxy    : /api -^> http://127.0.0.1:8000
echo   Press Ctrl+C to stop the dev server.
echo ============================================================================
echo.
set "VITE_OPEN_FLAG="
if "%OPEN_BROWSER%"=="1" set "VITE_OPEN_FLAG=--open"
call npm --prefix frontend run dev -- --host %HOST% --port %FE_PORT% %VITE_OPEN_FLAG%
if errorlevel 1 (
    echo [ERROR] Frontend dev server exited with an error.
    goto :fail
)
exit /b 0

:run_prod
echo ============================================================================
echo   House Price Prediction - Production Server ^(config\production.yaml^)
echo ============================================================================
echo   Running with APP_ENV=production. Press Ctrl+C to stop.
echo ============================================================================
echo.
set "APP_ENV=production"
"%VENV_PYTHON%" -m src.api.app
if errorlevel 1 (
    echo [ERROR] Production FastAPI server exited with an error.
    goto :fail
)
exit /b 0

:run_mlflow
if "%PORT_SET%"=="0" set "PORT=5000"
set "DISPLAY_HOST=%HOST%"
if "%HOST%"=="0.0.0.0" set "DISPLAY_HOST=127.0.0.1"

if not exist "mlflow_experiments\mlflow.db" (
    echo [WARN] MLflow database not found at "mlflow_experiments\mlflow.db".
    echo Run setup.bat first if you want populated experiment runs and registered models.
)

echo ============================================================================
echo   House Price Prediction - MLflow Tracking UI
echo ============================================================================
echo   MLflow UI : http://%DISPLAY_HOST%:%PORT%
echo   Backend   : sqlite:///mlflow_experiments/mlflow.db
echo   Press Ctrl+C to stop the server.
echo ============================================================================
echo.

if "%OPEN_BROWSER%"=="1" (
    start "" "http://%DISPLAY_HOST%:%PORT%"
)

"%VENV_PYTHON%" -m mlflow ui --backend-store-uri sqlite:///mlflow_experiments/mlflow.db --host %HOST% --port %PORT%
if errorlevel 1 (
    echo [ERROR] MLflow UI exited with an error.
    goto :fail
)
exit /b 0

:run_dashboard
if not exist "reports\monitoring\monitoring_dashboard.html" (
    echo [ERROR] Monitoring dashboard not found at "reports\monitoring\monitoring_dashboard.html".
    goto :fail
)
echo Opening monitoring dashboard: "%CD%\reports\monitoring\monitoring_dashboard.html"
start "" "%CD%\reports\monitoring\monitoring_dashboard.html"
exit /b 0

:run_docker
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker CLI was not found on PATH.
    goto :fail
)
echo Starting API and MLflow containers via Docker Compose...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start services. Ensure Docker Desktop is running.
    goto :fail
)
echo.
echo Docker services started:
echo   FastAPI Docs : http://127.0.0.1:8000/docs
echo   MLflow UI    : http://127.0.0.1:5000
exit /b 0

:fail
echo.
echo [FAILED] Unable to start service.
if "%NO_PAUSE%"=="0" pause
exit /b 1
