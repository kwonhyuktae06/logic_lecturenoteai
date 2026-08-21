"""
작성일: 2024-07-08
작성자: 한동희
GPU Test Script
CUDA 호환성 테스트 코드
"""
import torch

print(torch.cuda.is_available()) #값이 false면 CUDA가 설치되지 않았거나 GPU가 없음 또는 호환되지 않는 GPU를 사용하고 있다는 의미