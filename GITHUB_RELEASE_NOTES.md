# P4G Steam → Korean Vita Save Converter v1.0

## 한국어

Steam판 **Persona 4 Golden** 세이브를 한국 PS Vita판 **PCSH00021**에서 사용할 수 있도록 변환하는 첫 공개 버전입니다.

> **필수 조건**
> - 커펌/HENkaku 환경의 PS Vita
> - `vita-savemgr` / Vita Save Manager 설치
> - Persona 4 Golden 한국 Vita판 (`PCSH00021`)
> - Persona 4 Golden Steam판 세이브
> - Python 3.9 이상

### 주요 기능

- Steam P4G 세이브 → 한국 Vita판 `PCSH00021` 변환
- NG+ / 클리어 데이터 기반 세이브 지원
- 한국판 고유 세이브 구조 보존
- 한국판 주인공 이름 버퍼 보존
- 한국판 고유 구조값 `0x44` 보존
- Rescue / Retry / trailing save 영역 보존
- `sdslot.dat` / `system.bin` 수정하지 않음
- Steam `.bin` / `.binslot` 무결성 검사
- 기존 vita-savemgr SLOT을 in-place 방식으로 수정
- 변환 전 전체 SLOT 자동 ZIP 백업
- GUI에서 백업 복원 지원

### 실기 테스트 결과

실제 한국판 PS Vita에서 다음 사항을 확인했습니다.

- 변환된 세이브 정상 로드
- `C2-12828-1` 오류 없음
- Steam판 소지금 정상 계승
- Steam판 인간 파라미터 / Social Stats 정상 계승

다른 NG+ 승계 데이터도 메인 세이브 영역과 함께 이식되지만, 모든 항목을 개별적으로 검증한 것은 아닙니다.

### 매우 중요

Windows에서 `SLOT0 → SLOT1`처럼 vita-savemgr SLOT을 직접 복사해서 만들지 마세요.

반드시 **PS Vita의 vita-savemgr가 직접 만든 기존 SLOT**을 선택한 뒤, 이 프로그램이 그 SLOT을 수정하도록 해야 합니다.

### 개발

이 프로그램은 **OpenAI ChatGPT의 도움을 받아 Python으로 제작**되었습니다.

Steam판과 한국 Vita판 세이브 파일을 바이트 단위로 비교하고, 문제가 발생하는 영역을 단계적으로 분리한 뒤 실제 PS Vita에서 반복 테스트하여 변환 규칙을 확인했습니다.

### 라이선스

프로그램 소스 코드는 **MIT License**로 배포됩니다.

이 프로그램에는 Persona 4 Golden의 게임 파일, 펌웨어, 암호화 키, 실제 게임 세이브 데이터 또는 콘솔 개조 소프트웨어가 포함되어 있지 않습니다.

---

## English

This is the first public release of a converter for using **Persona 4 Golden Steam saves** with the **Korean PS Vita release (`PCSH00021`)**.

> **Requirements**
> - A modded / HENkaku-enabled PS Vita
> - `vita-savemgr` / Vita Save Manager installed
> - Korean PS Vita version of Persona 4 Golden (`PCSH00021`)
> - Persona 4 Golden Steam save data
> - Python 3.9 or newer

### Features

- Converts Steam P4G saves to Korean Vita `PCSH00021`
- Supports NG+ / clear-data-based saves
- Preserves Korean Vita-specific save structures
- Preserves Korean protagonist name buffers
- Preserves the Korean-specific structural value at `0x44`
- Preserves Rescue / Retry / trailing save sections
- Leaves `sdslot.dat` and `system.bin` untouched
- Validates Steam `.bin` / `.binslot` pairs
- Modifies an existing vita-savemgr SLOT in place
- Automatically creates a full ZIP backup before conversion
- Includes a GUI backup restore function

### Hardware-tested

Confirmed on an actual Korean PS Vita:

- Converted save loads successfully
- No `C2-12828-1` crash
- Steam money carries over correctly
- Steam Social Stats / Human Parameters carry over correctly

Other NG+ carry-over data is transferred as part of the main save structure, but not every individual item has been manually verified yet.

### Very important

Do **not** manually create new vita-savemgr SLOT folders by copying them in Windows, such as `SLOT0 → SLOT1`.

Always create the SLOT directly with **vita-savemgr on the Vita**, then let this converter modify that existing SLOT in place.

### Development

This tool was **developed in Python with the assistance of OpenAI ChatGPT**.

The conversion rule was derived through byte-level comparison of real Steam and Korean Vita saves, binary bisect testing of problematic regions, and repeated testing on actual PS Vita hardware.

### License

Source code is released under the **MIT License**.

This package does not contain Persona 4 Golden game files, firmware, encryption keys, real game save data, or console modification software.

---

## Disclaimer

Always keep an untouched backup of your original save.

This is an unofficial community project and is not affiliated with or endorsed by ATLUS, SEGA, Sony, Valve, or OpenAI.

Persona 4 Golden and all related trademarks belong to their respective owners.
