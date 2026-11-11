@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================================
rem setup.bat - Complete environment setup, data download, training, MLflow
rem             tracking, pipeline serialization, and verification for Windows.
rem ============================================================================

cd /d "%~dp0"

set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MLFLOW_DISABLE_AGENT_HINT=1"

set "SKIP_INSTALL=0"
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
echo Runs complete project setup, dataset download, EDA, data splitting,
echo model training, hyperparameter tuning, evaluation, MLflow logging,
echo production pipeline serialization, linting, and tests.
echo.
echo Options:
echo   --skip-install   Skip pip install steps (use existing .venv packages)
echo   --skip-tune      Skip Optuna/RandomizedSearchCV tuning if hyperparameters.yaml exists
echo   --skip-tests     Skip ruff lint and pytest verification checks
echo   --no-pause       Do not pause for keypress at completion or on error
echo   --help, -h       Show this help message and exit
echo.
exit /b 0

:args_done
echo ============================================================================
echo   House Price Prediction - Complete Setup ^& Training Pipeline
echo ============================================================================
echo Working directory: "%CD%"
echo.

rem ----------------------------------------------------------------------------
rem [1/11] Create or reuse Python virtual environment (.venv)
rem ----------------------------------------------------------------------------
echo [1/11] Checking Python virtual environment (.venv)...
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
for /f "delims=" %%V in ('"%VENV_PYTHON%" --version 2^>^&1') do echo Using %%V ^(%VENV_PYTHON%^)
echo.

rem ----------------------------------------------------------------------------
rem [2/11] Install dependencies and editable package
rem ----------------------------------------------------------------------------
if "%SKIP_INSTALL%"=="1" (
    echo [2/11] Skipping dependency installation ^(--skip-install^).
) else (
    echo [2/11] Installing dependencies from requirements.txt and editable package...
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
)
echo.

rem ----------------------------------------------------------------------------
rem [3/11] Download and verify raw dataset (Data\house_prices.csv)
rem ----------------------------------------------------------------------------
echo [3/11] Downloading and verifying raw dataset ^(Data\house_prices.csv^)...
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
rem [4/11] Exploratory Data Analysis (EDA)
rem ----------------------------------------------------------------------------
echo [4/11] Running Exploratory Data Analysis ^(notebooks\01_eda.py^)...
"%VENV_PYTHON%" notebooks\01_eda.py
if errorlevel 1 (
    echo [ERROR] EDA pipeline failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [5/11] Data cleaning, stratified splitting, and leakage checks
rem ----------------------------------------------------------------------------
echo [5/11] Cleaning dataset and creating leakage-safe train/test splits...
"%VENV_PYTHON%" -m src.data.split
if errorlevel 1 (
    echo [ERROR] Data splitting and leakage verification failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [6/11] Train and benchmark candidate regression models
rem ----------------------------------------------------------------------------
echo [6/11] Training and comparing baseline and ensemble models...
"%VENV_PYTHON%" -m src.models.train
if errorlevel 1 (
    echo [ERROR] Model comparison training failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [7/11] Hyperparameter optimization (Optuna + RandomizedSearchCV)
rem ----------------------------------------------------------------------------
if "%SKIP_TUNE%"=="1" (
    if exist "config\hyperparameters.yaml" (
        echo [7/11] Skipping hyperparameter tuning ^(--skip-tune; using config\hyperparameters.yaml^).
    ) else (
        echo [7/11] config\hyperparameters.yaml missing; running hyperparameter tuning...
        "%VENV_PYTHON%" -m src.models.hyperparameter_tuning
        if errorlevel 1 (
            echo [ERROR] Hyperparameter tuning failed.
            goto :fail
        )
    )
) else (
    echo [7/11] Running hyperparameter tuning ^(Optuna + 3-fold CV^)...
    "%VENV_PYTHON%" -m src.models.hyperparameter_tuning
    if errorlevel 1 (
        echo [ERROR] Hyperparameter tuning failed.
        goto :fail
    )
)
echo.

rem ----------------------------------------------------------------------------
rem [8/11] Full model evaluation, residual diagnostics, and error segmentation
rem ----------------------------------------------------------------------------
echo [8/11] Evaluating tuned champion model and generating diagnostic plots...
"%VENV_PYTHON%" -m src.models.evaluate
if errorlevel 1 (
    echo [ERROR] Model evaluation failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [9/11] MLflow experiment tracking and @production model registry
rem ----------------------------------------------------------------------------
echo [9/11] Logging runs to MLflow and registering @production model...
"%VENV_PYTHON%" -m src.models.mlflow_tracking
if errorlevel 1 (
    echo [ERROR] MLflow tracking and registration failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [10/11] Build and serialize end-to-end production ML pipeline
rem ----------------------------------------------------------------------------
echo [10/11] Training and serializing production pipeline ^(models\house_price_pipeline.joblib^)...
"%VENV_PYTHON%" -m src.pipeline.training_pipeline
if errorlevel 1 (
    echo [ERROR] Production training pipeline failed.
    goto :fail
)
echo.

rem ----------------------------------------------------------------------------
rem [11/11] Code lint and automated test verification
rem ----------------------------------------------------------------------------
if "%SKIP_TESTS%"=="1" (
    echo [11/11] Skipping lint and pytest checks ^(--skip-tests^).
) else (
    echo [11/11] Running ruff lint checks and pytest test suite...
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

echo ============================================================================
echo   SETUP AND COMPLETE TRAINING FINISHED SUCCESSFULLY
echo ============================================================================
echo Generated Artifacts:
echo   - Serialized Pipeline : models\house_price_pipeline.joblib
echo   - Model Metadata      : models\metadata.json
echo   - Processed Splits    : data\processed\train.csv, data\processed\test.csv
echo   - MLflow Store        : mlflow_experiments\mlflow.db
echo   - Reports ^& Figures   : reports\
echo.
echo Next step: Run start.bat to launch the FastAPI prediction server.
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
