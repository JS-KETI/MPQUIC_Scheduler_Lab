# MPQUIC Scheduler Lab · JS-KETI

- 2주차 미완료 원인 분석 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/fix/%239-week2-incomplete-diagnosis/reports/week2/2%EC%A3%BC%EC%B0%A8%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%EC%9B%90%EC%9D%B8%20%EB%B6%84%EC%84%9D.md
- 수정 검증: 원본 미완료 62회 모두 전체 수신. 630회 완료·621회 전체 수신, 시간 증가와 종료 후 기록 범위 별도 확인

- 2주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/week2/2%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md

ns-3 MP-QUIC 스케줄러의 환경 구축·결과 재현·원인 분석을 보관하는 실험 저장소입니다.

- 1주차 진행상황 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/week1/1%EC%A3%BC%EC%B0%A8%20%EC%A7%84%ED%96%89%EC%83%81%ED%99%A9.md
- 코드·CSV·그림·로그·패치 인덱스 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/artifacts/README.md
- 1주차 상세 실험 기록 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/reports/week1/1%EC%A3%BC%EC%B0%A8%20%EC%83%81%EC%84%B8%20%EC%8B%A4%ED%97%98%20%EA%B8%B0%EB%A1%9D.md
- 작업 관례 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/blob/main/docs/JS_KETI_CONVENTIONS.md

- 주차별 보고서 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/main/reports

## 재현 자료

- 검증 환경: Ubuntu 24.04 · WSL 2 · Python 3.12 · g++ 13
- 210회 실행·기준 대조: `artifacts/week1-2026-10-01/`
- 단일 경로 원인 분석·조건별 실험: `artifacts/one-path-analysis-2026-10-01/`
- 실행별 명령·소스 버전·환경·검증 결과는 각 폴더의 provenance·validation·로그에 보관
- 최초 `setup.sh` 설치 기록: `artifacts/setup-test-2026-10-01/`
- 고정 5Mbps·원본 링크 조건 5~6Mbps의 측정값·실행 기록 보존

## 버전 근거

- 기반: https://github.com/ssjShirley/mpquic
- 원본 기준: `99df419d0bb49e81b9afa1f4747769ab3f9e53ae`
- 1주차 setup 보존 : https://github.com/JS-KETI/MPQUIC_Scheduler_Lab/tree/week1-setup-20261001
- 단일 경로 분석: `lab/w1-one-path-diagnosis-20261001`
- 제공 01·02 패치와 추가 관찰·호환 패치를 구분해 보관. 원본 라이선스 유지

---

## 원본 프로젝트 안내


A Multipath Extension to the QUIC Module in ns-3
================================

The implementation is described in [this paper](https://dl.acm.org/doi/10.1145/3592149.3592803).

Please use the issue tracker for bugs/questions.

## MPQUIC code base
This repository contains in the `src/quic` for a multipath extension to the QUIC protocol for ns-3.

[src/quic/Readme](https://github.com/ssjShirley/mpquic-ns3/blob/mpquic-1.2/src/quic/README.md) details the code structure and the implementation align the [IETF draft](https://datatracker.ietf.org/doc/draft-ietf-quic-multipath/04/).


## Install

### Prerequisites ###

Our implementation requires basic environment settings for ns-3. For Ubuntu22.04 users, please use the following cmd to install the prerequisities. For users with different OS, please refer to [the ns-3 documentation](https://www.nsnam.org/documentation/) for more detailed instructions on how to set up your system to install ns-3.

```bash
apt-get update 
apt-get install -y build-essential python3 python3-dev git libeigen3-dev python3-pandas python3-numpy python3-matplotlib font-manager
```

### Downloading ####

Please download the repository by https, ssh, or other options.

```bash
git clone git@github.com:ssjShirley/mpquic-ns3.git mpquic
```

### Compilation ###

Please compile and build mpquic with the following cmd:

```bash
cd mpquic
./waf configure --enable-examples --enable-tests
./waf build
```

### View Experimental Results for WNS3 ###

Following jupyter files present the Figures 7 to 13 in the paper.

1. [`scalable-draw-figure7.ipynb`](https://github.com/ssjShirley/mpquic-ns3/blob/mpquic-1.2/wns3-draw-figures/scalable-draw-figure7.ipynb)
2. [`cwnd-draw-figure8.ipynb`](https://github.com/ssjShirley/mpquic-ns3/blob/mpquic-1.2/wns3-draw-figures/cwnd-draw-figure8.ipynb)
3. [`schedule-draw-figure9-10.ipynb`](https://github.com/ssjShirley/mpquic-ns3/blob/mpquic-1.2/wns3-draw-figures/schedule-draw-figure9-10.ipynb)
4. [`scheduler-cpr-two-path-figure11-13.ipynb`](https://github.com/ssjShirley/mpquic-ns3/blob/mpquic-1.2/wns3-draw-figures/scheduler-cpr-two-path-figure11-13.ipynb)


### Reproduce Experimental Results for WNS3 ###

Please use the following script to reproduce the experimental results in WNS3 paper. It might take few hours to generate all required data.
```bash
./wns3-2023-all-exp-figures.sh
```


#### Reproduce Results with Docker ####

For docker users, please load the image by
```bash
docker pull ssjshirley/mpquic-ns3:latest
```

Or, you can build the image with `Dockerfile` by
```bash
docker build -t ssjshirley/mpquic-ns3 .
```

To run the docker image and the data and figures will be stored in `$PWD/results`. (This may take few hours.)
```bash
docker run -it -v $PWD/results:/root/workspace/mpquic/results-wns3 ssjshirley/mpquic-ns3:latest
```


## Original QUIC code base
The ns-3 QUIC module can be found at https://github.com/signetlabdei/quic.

The implementation is described in [this paper](https://arxiv.org/abs/1902.06121).
