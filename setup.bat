@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem setup.bat - One-time complete environment setup for House Price Prediction:
rem             Python .venv + dependencies, React/Vite frontend dependencies,
rem             Kaggle dataset download, training pipeline, MLflow tracking,
rem             model serialization, and full Python + Frontend verification.
rem ============================================================================

cd /d "%~dp0"

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MLFLOW_DISABLE_AGENT_HINT=1"

set "SKIP_INSTALL=0"
set "FORCE_INSTALL=0"
set "SKIP_TUNE=0"
set "SKIP_TESTS=0"
set "NO_PAUSE=0"

for %%A in (%*) do (
    if /i "%%~A"=="--no-pause" set "NO_PAUSE=1"
)

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--skip-install" (
    set "SKIP_INSTALL=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--force-install" (
    set "FORCE_INSTALL=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--skip-tune" (
    set "SKIP_TUNE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--skip-tests" (
    set "SKIP_TESTS=1"
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
echo Run "setup.bat --help" for usage information.
goto :fail

:usage
echo.
echo Usage: setup.bat [OPTIONS]
echo.
echo One-time setup after cloning the repository:
echo   - Creates .venv and installs missing Python packages (requirements.txt + -e .)
echo   - Verifies Node.js/npm and installs frontend\node_modules
echo   - Downloads Data\house_prices.csv (if missing) and runs full ML training
echo   - Logs runs to MLflow and serializes models\house_price_pipeline.joblib
echo   - Runs Python (ruff + pytest) and Frontend (vitest + tsc + vite build) checks
echo.
echo Options:
echo   --skip-install   Skip Python and npm install checks
echo   --force-install  Reinstall all Python and npm dependencies even if present
echo   --skip-tune      Skip Optuna/RandomizedSearchCV tuning if hyperparameters.yaml exists
echo   --skip-tests     Skip ruff, pytest, vitest, and vite build checks
echo   --no-pause       Do not pause for keypress at completion or on error
echo   --help, -h       Show this help message and exit
echo.
exit /b 0

:args_done
echo ============================================================================
echo   House Price Prediction - One-Time Full Environment Setup
echo ============================================================================
echo Working directory: "%CD%"
echo.

rem ----------------------------------------------------------------------------
rem [1/13] Create or reuse Python virtual environment (.venv)
rem ----------------------------------------------------------------------------
echo [1/13] Checking Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo Creating .venv virtual environment...
    set "BASE_PYTHON="
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "BASE_PYTHON=python"
    ) else (
        py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
        if not errorlevel 1 set "BASE_PYTHON=py -3"
    )
    if "!BASE_PYTHON!"=="" (
        echo [ERROR] Python 3.10+ ^(3.13 recommended^) was not found on PATH.
        echo Install Python from https://www.python.org/downloads/ and check "Add Python to PATH".
        goto :fail
    )
    !BASE_PYTHON! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv virtual environment.
        goto :fail
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment python not found at ".venv\Scripts\python.exe".
    goto :fail
)

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
for /f "delims=" %%V in ('"%VENV_PYTHON%" --version 2^>^&1') do echo [OK] Using %%V ^(%VENV_PYTHON%^)
echo.

rem ----------------------------------------------------------------------------
rem [2/13] Check and install Python dependencies (requirements.txt + editable pkg)
rem ----------------------------------------------------------------------------
echo [2/13] Checking Python dependencies...
if "%SKIP_INSTALL%"=="1" (
    echo [SKIP] Skipping Python dependency installation ^(--skip-install^).
) else (
    set "NEED_PY_INSTALL=0"
    if "%FORCE_INSTALL%"=="1" (
        set "NEED_PY_INSTALL=1"
    ) else (
        "%VENV_PYTHON%" -c "import importlib.metadata, fastapi, uvicorn, pydantic, httpx, joblib, pandas, numpy, scipy, sklearn, lightgbm, xgboost, optuna, mlflow, yaml, matplotlib, seaborn, kagglehub, pytest, ruff; importlib.metadata.version('house-price-prediction')" >nul 2>&1
        if errorlevel 1 set "NEED_PY_INSTALL=1"
    )
    if "!NEED_PY_INSTALL!"=="1" (
        echo Installing missing Python packages from requirements.txt and editable package...
        "%VENV_PYTHON%" -m pip install -r requirements.txt
        if errorlevel 1 (
            echo [ERROR] Failed to install packages from requirements.txt.
            goto :fail
        )
        "%VENV_PYTHON%" -m pip install --no-build-isolation --no-deps -e .
        if errorlevel 1 (
            echo [ERROR] Failed to install local package in editable mode.
            goto :fail
        )
        echo [OK] Python dependencies installed.
    ) else (
        echo [OK] All Python dependencies and editable package are already installed.
    )
)
echo.

rem ----------------------------------------------------------------------------
rem [3/13] Check Node.js/npm and install Frontend dependencies
rem ----------------------------------------------------------------------------
echo [3/13] Checking Node.js and React frontend dependencies...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH.
    echo Install Node.js LTS from https://nodejs.org/ and re-run setup.bat.
    goto :fail
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    goto :fail
)
for /f "delims=" %%N in ('node -v 2^>^&1') do echo [OK] Node.js %%N detected.

if not exist "frontend\package.json" (
    echo [ERROR] Frontend manifest missing at "frontend\package.json".
    goto :fail
)

if "%SKIP_INSTALL%"=="1" (
    echo [SKIP] Skipping frontend dependency installation ^(--skip-install^).
) else (
    set "NEED_FE_INSTALL=0"
    if "%FORCE_INSTALL%"=="1" set "NEED_FE_INSTALL=1"
    if not exist "frontend\node_modules\vite\bin\vite.js" set "NEED_FE_INSTALL=1"
    if not exist "frontend\node_modules\react\package.json" set "NEED_FE_INSTALL=1"
    if not exist "frontend\node_modules\lucide-react\package.json" set "NEED_FE_INSTALL=1"
    if not exist "frontend\node_modules\typescript\bin\tsc" set "NEED_FE_INSTALL=1"
    if not exist "frontend\node_modules\vitest\vitest.mjs" set "NEED_FE_INSTALL=1"

    if "!NEED_FE_INSTALL!"=="1" (
        echo Installing frontend npm packages in frontend\...
        call npm --prefix frontend install
        if errorlevel 1 (
            echo [ERROR] Failed to install frontend npm dependencies.
            goto :fail
        )
        echo [OK] Frontend dependencies installed.
    ) else (
        echo [OK] All frontend dependencies are already installed.
    )
)
echo.

rem ----------------------------------------------------------------------------
rem [4/13] Download and verify raw dataset (Data\house_prices.csv)
rem ----------------------------------------------------------------------------
echo [4/13] Checking and verifying raw dataset ^(Data\house_prices.csv^)...
"%VENV_PYTHON%" Data\data_download.py
if errorlevel 1 (
    echo [ERROR] Dataset download failed.
    echo If Kaggle authentication is required, configure %%USERPROFILE%%\.kaggle\kaggle.json
    echo or set KAGGLE_USERNAME and KAGGLE_KEY environment variables.
    goto :fail
)
"%VENV_PYTHON%" -m src.data.load_data
if errorlevel 1 (
    echo [ERROR] Raw dataset verification failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [5/13] Exploratory Data Analysis (EDA)
rem ----------------------------------------------------------------------------
echo [5/13] Running Exploratory Data Analysis ^(notebooks\01_eda.py^)...
"%VENV_PYTHON%" notebooks\01_eda.py
if errorlevel 1 (
    echo [ERROR] EDA pipeline failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [6/13] Data cleaning, stratified splitting, and leakage checks
rem ----------------------------------------------------------------------------
echo [6/13] Cleaning dataset and creating leakage-safe train/test splits...
"%VENV_PYTHON%" -m src.data.split
if errorlevel 1 (
    echo [ERROR] Data splitting and leakage verification failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [7/13] Train and benchmark candidate regression models
rem ----------------------------------------------------------------------------
echo [7/13] Training and comparing baseline and ensemble models...
"%VENV_PYTHON%" -m src.models.train
if errorlevel 1 (
    echo [ERROR] Model comparison training failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [8/13] Hyperparameter optimization (Optuna + RandomizedSearchCV)
rem ----------------------------------------------------------------------------
if "%SKIP_TUNE%"=="1" (
    if exist "config\hyperparameters.yaml" (
        echo [8/13] Skipping hyperparameter tuning ^(--skip-tune; using config\hyperparameters.yaml^).
    ) else (
        echo [8/13] config\hyperparameters.yaml missing; running hyperparameter tuning...
        "%VENV_PYTHON%" -m src.models.hyperparameter_tuning
        if errorlevel 1 (
            echo [ERROR] Hyperparameter tuning failed.
            goto :fail
        )
    )
) else (
    echo [8/13] Running hyperparameter tuning ^(Optuna + 3-fold CV^)...
    "%VENV_PYTHON%" -m src.models.hyperparameter_tuning
    if errorlevel 1 (
        echo [ERROR] Hyperparameter tuning failed.
        goto :fail
    )
)
echo.

rem ----------------------------------------------------------------------------
rem [9/13] Full model evaluation, residual diagnostics, and error segmentation
rem ----------------------------------------------------------------------------
echo [9/13] Evaluating tuned champion model and generating diagnostic plots...
"%VENV_PYTHON%" -m src.models.evaluate
if errorlevel 1 (
    echo [ERROR] Model evaluation failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [10/13] MLflow experiment tracking and @production model registry
rem ----------------------------------------------------------------------------
echo [10/13] Logging runs to MLflow and registering @production model...
"%VENV_PYTHON%" -m src.models.mlflow_tracking
if errorlevel 1 (
    echo [ERROR] MLflow tracking and registration failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [11/13] Build and serialize end-to-end production ML pipeline
rem ----------------------------------------------------------------------------
echo [11/13] Training and serializing production pipeline ^(models\house_price_pipeline.joblib^)...
"%VENV_PYTHON%" -m src.pipeline.training_pipeline
if errorlevel 1 (
    echo [ERROR] Production training pipeline failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [12/13] Python lint and automated test verification
rem ----------------------------------------------------------------------------
if "%SKIP_TESTS%"=="1" (
    echo [12/13] Skipping Python lint and pytest checks ^(--skip-tests^).
) else (
    echo [12/13] Running ruff lint checks and pytest test suite...
    "%VENV_PYTHON%" -m ruff check Data\data_download.py src tests
    if errorlevel 1 (
        echo [ERROR] Ruff lint checks failed.
        goto :fail
    )
    "%VENV_PYTHON%" -m pytest -v
    if errorlevel 1 (
        echo [ERROR] Pytest verification suite failed.
        goto :fail
    )
)
echo.

rem ----------------------------------------------------------------------------
rem [13/13] Frontend tests, TypeScript check, and Vite build verification
rem ----------------------------------------------------------------------------
if "%SKIP_TESTS%"=="1" (
    echo [13/13] Skipping frontend verification ^(--skip-tests^).
) else (
    echo [13/13] Running frontend unit tests, typecheck, and Vite production build...
    call npm --prefix frontend run test
    if errorlevel 1 (
        echo [ERROR] Frontend Vitest unit tests failed.
        goto :fail
    )
    call npm --prefix frontend run build
    if errorlevel 1 (
        echo [ERROR] Frontend TypeScript / Vite build failed.
        goto :fail
    )
)
echo.

echo ============================================================================
echo   SETUP AND VERIFICATION FINISHED SUCCESSFULLY
echo ============================================================================
echo Verified Environment ^& Artifacts:
echo   - Python Virtual Env  : .venv\Scripts\python.exe
echo   - Frontend Modules    : frontend\node_modules ^& frontend\dist
echo   - Serialized Pipeline : models\house_price_pipeline.joblib
echo   - Model Metadata      : models\metadata.json
echo   - Processed Splits    : data\processed\train.csv, data\processed\test.csv
echo   - MLflow Store        : mlflow_experiments\mlflow.db
echo   - Reports ^& Figures   : reports\
echo.
echo Next step: Simply run "start.bat" anytime to verify and launch the full app.
echo ============================================================================
if "%NO_PAUSE%"=="0" pause
exit /b 0

:fail
echo.
echo ============================================================================
echo   SETUP FAILED - See error details above.
echo ============================================================================
if "%NO_PAUSE%"=="0" pause
exit /b 1
