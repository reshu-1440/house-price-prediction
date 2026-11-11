@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem start.bat - Launch House Price Prediction FastAPI server, MLflow UI,
rem             monitoring dashboard, or Docker Compose stack on Windows.
rem ============================================================================

cd /d "%~dp0"

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MLFLOW_DISABLE_AGENT_HINT=1"

set "MODE=api"
set "HOST=127.0.0.1"
set "PORT=8000"
set "PORT_SET=0"
set "RELOAD_FLAG="
set "OPEN_BROWSER=0"
set "ALLOW_DEGRADED=0"
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
echo Starts the House Price Prediction FastAPI inference service by default.
echo Run setup.bat first if you have not yet set up .venv and trained the model.
echo.
echo Modes:
echo   ^(default^)         Start FastAPI server at http://127.0.0.1:8000
echo   --prod            Start FastAPI with config\production.yaml ^(APP_ENV=production^)
echo   --mlflow          Start MLflow Tracking UI ^(default port 5000^)
echo   --dashboard       Open the HTML monitoring dashboard in your browser
echo   --docker          Build and start API + MLflow via Docker Compose
echo.
echo Options:
echo   --host HOST       Bind host address ^(default: 127.0.0.1^)
echo   --port PORT       Bind port ^(default: 8000 for API, 5000 for MLflow^)
echo   --reload          Enable uvicorn auto-reload for development
echo   --open            Open Swagger UI / MLflow UI in default web browser
echo   --allow-degraded  Start API even if models\house_price_pipeline.joblib is missing
echo   --no-pause        Do not pause on error
echo   --help, -h        Show this help message and exit
echo.
exit /b 0

:args_done
if /i "%MODE%"=="docker" goto :run_docker
if /i "%MODE%"=="dashboard" goto :run_dashboard

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at ".venv\Scripts\python.exe".
    echo Please run setup.bat first to create .venv, download data, and train the model.
    goto :fail
)

if /i "%MODE%"=="mlflow" goto :run_mlflow

if not exist "models\house_price_pipeline.joblib" (
    if "%ALLOW_DEGRADED%"=="0" (
        echo [ERROR] Trained model artifact not found: "models\house_price_pipeline.joblib".
        echo Please run setup.bat first to train and serialize the pipeline,
        echo or pass --allow-degraded to start the server in degraded health mode.
        goto :fail
    ) else (
        echo [WARN] Model artifact missing; starting API in degraded mode ^(/predict returns 503^).
    )
)

set "DISPLAY_HOST=%HOST%"
if "%HOST%"=="0.0.0.0" set "DISPLAY_HOST=127.0.0.1"

if /i "%MODE%"=="prod" goto :run_prod

echo ============================================================================
echo   House Price Prediction - FastAPI Inference Server
echo ============================================================================
echo   Swagger Docs : http://%DISPLAY_HOST%:%PORT%/docs
echo   ReDoc        : http://%DISPLAY_HOST%:%PORT%/redoc
echo   Health Check : http://%DISPLAY_HOST%:%PORT%/health
echo   Model Info   : http://%DISPLAY_HOST%:%PORT%/model/info
echo.
echo   Other modes  : start.bat --mlflow  ^|  start.bat --dashboard  ^|  start.bat --docker
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
