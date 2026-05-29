#!/bin/bash
# ==============================================================================
# 새싹 방범대 - 로컬 개발 환경 및 의존성 라이브러리 설치 자동화 스크립트
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "새싹 방범대 로컬 개발 환경 및 의존성 라이브러리 설치 시작"
echo "=========================================================="

OS_TYPE="$(uname -s)"
echo "감지된 OS: $OS_TYPE"

# 1. 시스템 의존성 설치
if [ "$OS_TYPE" = "Darwin" ]; then
    echo "macOS 환경 감지: Homebrew를 사용하여 필수 패키지를 빌드/설치합니다."
    if ! command -v brew &> /dev/null; then
        echo "Error: Homebrew가 설치되어 있지 않습니다. https://brew.sh/ 를 먼저 설치해주세요."
        exit 1
    fi
    echo "Homebrew 패키지 설치 진행 (gcc, llvm, libpq, redis)..."
    brew install gcc llvm libpq redis || true
    
    # macOS Apple Silicon (M1/M2/M3)용 컴파일 헤더 및 라이브러리 경로 매핑
    BREW_PREFIX=$(brew --prefix)
    export LDFLAGS="-L$BREW_PREFIX/opt/libpq/lib -L$BREW_PREFIX/opt/llvm/lib"
    export CPPFLAGS="-I$BREW_PREFIX/opt/libpq/include -I$BREW_PREFIX/opt/llvm/include"
    export PATH="$BREW_PREFIX/opt/llvm/bin:$PATH"
    
elif [ "$OS_TYPE" = "Linux" ]; then
    echo "Linux 환경 감지: APT 패키지 매니저로 필수 컴파일 패키지를 설치합니다."
    sudo apt-get update
    sudo apt-get install -y build-essential gcc g++ gfortran python3-dev libpq-dev redis-tools
else
    echo "지원하지 않는 OS 유형입니다. docs/install_oss.md를 참조하여 수동 설치해 주세요."
    exit 1
fi

# 2. Python 가상환경 생성 및 활성화
if [ ! -d ".venv" ]; then
    echo "Python 가상환경(.venv) 생성 중..."
    python3 -m venv .venv
fi

echo "가상환경 활성화..."
source .venv/bin/activate

echo "pip, setuptools, wheel 패키지 최신화..."
pip install --upgrade pip setuptools wheel

# 3. Cython 및 numpy 설치 (LightFM 컴파일 대비)
echo "Cython 및 numpy 빌드/설치..."
pip install "cython" "numpy>=1.22.0"

# 4. LightFM 소스 다운로드 및 Cython 3 + Python 3.14 호환 패치 후 컴파일 설치
echo "LightFM 호환 컴파일 세팅 시작..."
rm -rf /tmp/lightfm-build
git clone https://github.com/lyst/lightfm.git /tmp/lightfm-build

echo "Cython 3.0+ 호환성을 위한 'noexcept' 패치 적용..."
python3 -c "
path = '/tmp/lightfm-build/lightfm/_lightfm_fast.pyx.template'
with open(path, 'r') as f:
    text = f.read()
text = text.replace('cdef int reverse_pair_compare(const_void *a, const_void *b) nogil:', 'cdef int reverse_pair_compare(const_void *a, const_void *b) noexcept nogil:')
text = text.replace('cdef int int_compare(const_void *a, const_void *b) nogil:', 'cdef int int_compare(const_void *a, const_void *b) noexcept nogil:')
text = text.replace('cdef int flt_compare(const_void *a, const_void *b) nogil:', 'cdef int flt_compare(const_void *a, const_void *b) noexcept nogil:')
with open(path, 'w') as f:
    f.write(text)
print('   -> template 파일 noexcept 패치 완료.')
"

echo "Cythonizing LightFM templates..."
cd /tmp/lightfm-build
python setup.py cythonize
cd "$PROJECT_ROOT"

echo "LightFM 빌드 및 가상환경 설치..."
if [ "$OS_TYPE" = "Darwin" ]; then
    CC=clang CXX=clang++ pip install /tmp/lightfm-build
else
    pip install /tmp/lightfm-build
fi
rm -rf /tmp/lightfm-build
echo "LightFM 컴파일 설치 완료."

# 5. 나머지 Python 패키지 설치
echo "나머지 의존성 패키지 설치 진행 (requirements.txt)..."
pip install -r requirements.txt

echo "=========================================================="
echo "의존성 라이브러리 설치가 성공적으로 완료되었습니다!"
echo "가상환경 활성화 명령어: source .venv/bin/activate"
echo "=========================================================="
