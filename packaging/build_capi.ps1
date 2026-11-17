$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $env:CUDA_PATH -or -not $env:CUTLASS_DIR) { throw 'CUDA_PATH and CUTLASS_DIR required' }
$nvcc = Join-Path $env:CUDA_PATH 'bin/nvcc.exe'
$sources = @('csrc/capi/p40_capi.cu','csrc/gemm/pearl_gemm_only_sm61.cu','csrc/gemm/pearl_blake3_sm61.cu','csrc/gemm/noising_sm61.cu','csrc/gemm/noise_generation.cu','csrc/blake3/blake3.cu','csrc/gemm/rng_fill_sm61.cu','csrc/tensor_hash/tensor_hash.cu','csrc/gemm/noise_gemm_sm61.cu','csrc/gemm/pearl_ampere_tc.cu')
$options = @('-shared','-o','p40cuda.dll','-I','csrc','-I','csrc/gemm','-I','csrc/blake3','-I','csrc/tensor_hash','-I',$env:CUTLASS_DIR,'-std=c++20','--expt-relaxed-constexpr','--expt-extended-lambda','--use_fast_math','-gencode','arch=compute_61,code=sm_61','-gencode','arch=compute_86,code=sm_86','-gencode','arch=compute_89,code=sm_89','-O3','-DNDEBUG','-DP40_NO_TORCH','-Xcompiler','/O2')
& $nvcc @options @sources
if ($LASTEXITCODE -ne 0) { throw 'CUDA compilation failed' }
