# 论文创作 Agent 系统 - Windows 安装脚本
# 使用方法：在 PowerShell 中运行 .\install.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  论文创作 Agent 系统 - 安装向导" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/5] 检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：未检测到 Python，请先安装 Python 3.9+" -ForegroundColor Red
    Write-Host "下载地址：https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "检测到 $pythonVersion" -ForegroundColor Green

# 检查 Python 版本
$versionMatch = $pythonVersion -match "(\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        Write-Host "警告：Python 版本过低，建议使用 3.9+" -ForegroundColor Yellow
    }
}

Write-Host ""

# 创建虚拟环境
Write-Host "[2/5] 创建虚拟环境..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "虚拟环境已存在，跳过创建" -ForegroundColor Green
} else {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误：创建虚拟环境失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "虚拟环境创建成功" -ForegroundColor Green
}

Write-Host ""

# 激活虚拟环境
Write-Host "[3/5] 激活虚拟环境..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "虚拟环境已激活" -ForegroundColor Green

Write-Host ""

# 安装依赖
Write-Host "[4/5] 安装依赖包..." -ForegroundColor Yellow
pip install -r scripts\requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：依赖安装失败" -ForegroundColor Red
    exit 1
}
Write-Host "核心依赖安装成功" -ForegroundColor Green

Write-Host ""

# 询问是否安装完整版
Write-Host "[5/5] 可选：安装完整版 AIGC 检测" -ForegroundColor Yellow
Write-Host "完整版包含 GPT-2 困惑度检测，准确率更高（约 2.5 GB）" -ForegroundColor Yellow
$installFull = Read-Host "是否安装完整版？(y/N)"
if ($installFull -eq "y" -or $installFull -eq "Y") {
    Write-Host "正在安装 PyTorch（CPU 版）..." -ForegroundColor Yellow
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    Write-Host "正在安装 Transformers..." -ForegroundColor Yellow
    pip install transformers>=4.30.0
    Write-Host "完整版安装成功" -ForegroundColor Green
} else {
    Write-Host "跳过完整版安装，使用轻量版" -ForegroundColor Green
}

Write-Host ""

# 验证安装
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  验证安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "测试 aigc_detect.py..." -ForegroundColor Yellow
python scripts\aigc_detect.py --help | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ aigc_detect.py 正常" -ForegroundColor Green
} else {
    Write-Host "❌ aigc_detect.py 异常" -ForegroundColor Red
}

Write-Host "测试 synonym_replace.py..." -ForegroundColor Yellow
python scripts\synonym_replace.py --help | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ synonym_replace.py 正常" -ForegroundColor Green
} else {
    Write-Host "❌ synonym_replace.py 异常" -ForegroundColor Red
}

Write-Host "测试 text_analysis.py..." -ForegroundColor Yellow
python scripts\text_analysis.py --help | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ text_analysis.py 正常" -ForegroundColor Green
} else {
    Write-Host "❌ text_analysis.py 异常" -ForegroundColor Red
}

Write-Host "测试 format_checker.py..." -ForegroundColor Yellow
python scripts\format_checker.py --help | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ format_checker.py 正常" -ForegroundColor Green
} else {
    Write-Host "❌ format_checker.py 异常" -ForegroundColor Red
}

Write-Host ""

# 安装完成
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "使用方法：" -ForegroundColor Cyan
Write-Host "  1. 将参考资料放入 references/ 目录" -ForegroundColor White
Write-Host "  2. 在 Claude Code 中说：「帮我写论文，主题是...」" -ForegroundColor White
Write-Host ""
Write-Host "单独使用 Python 工具：" -ForegroundColor Cyan
Write-Host "  python scripts/aigc_detect.py --input paper.md" -ForegroundColor White
Write-Host "  python scripts/synonym_replace.py --input paper.md" -ForegroundColor White
Write-Host "  python scripts/text_analysis.py --input paper.md" -ForegroundColor White
Write-Host "  python scripts/format_checker.py --input paper.md" -ForegroundColor White
Write-Host ""