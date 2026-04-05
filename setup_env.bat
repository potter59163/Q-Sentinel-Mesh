@echo off
echo ============================================================
echo  Q-Sentinel Mesh — Environment Setup
echo ============================================================

:: Step 1: Create virtual environment
python -m venv .venv
call .venv\Scripts\activate.bat

:: Step 2: Upgrade pip
python -m pip install --upgrade pip

:: Step 3: Install PyTorch with CUDA 12.8 (RTX 5060 / Blackwell compatible)
echo Installing PyTorch 2.10.0 with CUDA 12.8...
pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 --index-url https://download.pytorch.org/whl/cu128

:: Step 4: Install all other dependencies
echo Installing remaining dependencies...
pip install -r requirements.txt

echo Verifying PQC backend...
python -c "from src.federated.pqc_crypto import pqc_backend_name, pqc_backend_is_real; print('PQC backend:', pqc_backend_name(), '| real=', pqc_backend_is_real())"

echo.
echo ============================================================
echo  Setup complete! Activate environment with:
echo  .venv\Scripts\activate.bat
echo ============================================================
pause
