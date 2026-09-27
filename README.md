# P4G-KOR-savefile-PC-to-PSVita
# Persona 4 Golden Steam → Korean PS Vita Save Converter

Steam판 **Persona 4 Golden** 세이브를 **한국어 PS Vita판 (`PCSH00021`)**에서 사용할 수 있도록 변환하는 도구입니다.

기존 P4G PC → Vita 세이브 변환 도구는 주로 북미판/유럽판 Vita를 대상으로 하며, 한국판은 세이브 구조에 일부 차이가 있어 일반적인 방식으로 변환하면 로드 시 `C2-12828-1` 오류가 발생할 수 있습니다.

이 도구는 실제 Steam 세이브와 한국판 Vita 세이브를 바이트 단위로 비교하고, 실제 PS Vita에서 반복 테스트하여 확인한 변환 규칙을 기반으로 제작되었습니다.

---

# 한국어

## 주요 기능

- Steam판 P4G 세이브를 한국 PS Vita판 `PCSH00021`용으로 변환
- New Game+ / 클리어 데이터 기반 세이브 지원
- 한국판 Vita 고유 세이브 구조 보존
- 한국판 주인공 이름 데이터 보존
- 한국판 고유 구조값 `0x44` 보존
- Vita Rescue / Retry 영역 보존
- `sdslot.dat` 수정하지 않음
- `system.bin` 수정하지 않음
- Steam `.bin` / `.binslot` 쌍 무결성 검사
- 기존 `vita-savemgr` SLOT을 직접 수정하는 방식
- 변환 전 전체 savemgr SLOT 자동 ZIP 백업
- GUI에서 ZIP 백업 복원 가능

## 실제 확인된 동작

한국어 PS Vita 실기에서 변환된 세이브가 정상적으로 로드되는 것을 확인했습니다.

기존 변환 과정에서 발생하던:

`C2-12828-1`

오류 없이 정상적으로 게임을 시작할 수 있습니다.

현재 실제로 확인된 Steam NG+ 계승 데이터:

- 돈
- 인간 파라미터 / Social Stats
- NG+ 기반 게임 상태

Persona Compendium, Max Social Link 보상 아이템, 의상, Skill Card 기록 및 기타 NG+ 승계 정보도 메인 세이브 데이터와 함께 이식되지만, 모든 항목이 개별적으로 실기 확인된 것은 아닙니다.

## 한국판 세이브 구조의 차이

한국 Vita판 `PCSH00021`의 세이브 구조는 북미/유럽 Vita판과 완전히 동일하지 않습니다.

테스트 과정에서 Steam 데이터를 한국판에 그대로 이식했을 때, 한국판 기준:

`0x44`

값까지 Steam 값으로 변경하면 게임 로딩 시 `C2-12828-1` 오류가 발생하는 것을 확인했습니다.

실제 테스트 세이브:

```text
Korean 0x44–0x47 : 64 0C 00 00
                  = 0x00000C64
                  = 3172

Steam equivalent : 74 0C 00 00
                  = 0x00000C74
                  = 3188
```

두 값의 차이는 정확히:

```text
0x10 = 16 bytes
```

입니다.

한국판과 PC판 사이의 이름 관련 구조 크기 차이 역시 `0x10`이므로, 이 값은 한국판 고유의 내부 구조 offset/size와 관련된 값으로 추정됩니다.

따라서 이 변환기는 **한국판 `0x44` 값을 항상 원본 그대로 유지합니다.**

## 최종 변환 규칙

다음 영역은 한국판 Vita 원본 데이터를 유지합니다.

```text
KR 0x0010–0x0023
한국판 이름 버퍼 #1

KR 0x0044
한국판 고유 구조값

KR 0x0054–0x0067
한국판 이름 버퍼 #2

KR 0x15100 이후
Rescue / Retry / trailing save structure
```

또한 다음 파일은 수정하지 않습니다.

```text
sdslot.dat
system.bin
```

그 외 `0x15100` 이전의 매핑 가능한 메인 게임 데이터는 Steam 세이브에서 이식합니다.

현재 사용되는 매핑:

```text
Korean 0x0000–0x000F
← Steam 동일 offset

Korean 0x0024–0x0053
← Steam offset +0x10

단, Korean 0x0044는 원본 유지

Korean 0x0068–0x150FF
← Steam offset +0x20
```

## 사용 방법

1. 한국판 Persona 4 Golden에서 정상적인 세이브를 하나 만듭니다.

2. PS Vita에서 `vita-savemgr`를 실행합니다.

3. `PCSH00021`의 백업 SLOT을 **vita-savemgr에서 직접 생성**합니다.

예:

```text
ux0:data/savegames/PCSH00021/SLOT0
```

4. 해당 vita-savemgr SLOT을 PC에서 접근할 수 있도록 합니다.

5. 프로그램을 실행합니다.

6. Steam Persona 4 Golden의 save 폴더를 선택합니다.

일반적인 위치:

```text
Steam\userdata\<SteamID>\1113000\remote
```

7. Vita에서 직접 생성된 기존:

```text
PCSH00021\SLOTn
```

폴더를 선택합니다.

8. Steam 원본 세이브 슬롯을 선택합니다.

9. Vita 대상 게임 슬롯을 선택합니다.

10. 변환을 실행합니다.

11. 변환 후 PS Vita에서 **같은 vita-savemgr SLOT**을 Restore 합니다.

12. Persona 4 Golden을 실행하고 세이브를 로드합니다.

## 매우 중요

Windows에서 다음처럼 savemgr SLOT 폴더를 직접 복제하지 마세요.

```text
SLOT0 → SLOT1
```

실제 테스트 결과:

```text
vita-savemgr가 직접 만든 SLOT
→ 정상 로드

Windows에서 폴더 복사로 만든 SLOT
→ C2-12828-1
```

따라서 반드시 **vita-savemgr가 먼저 SLOT을 생성한 뒤**, 이 프로그램이 그 기존 SLOT을 in-place 방식으로 수정해야 합니다.

## 자동 백업

변환 전에 선택한 Vita savemgr SLOT 전체가 자동으로 ZIP 백업됩니다.

Windows 기준:

```text
Documents\P4G_Vita_Backups
```

프로그램 GUI에서 이전 ZIP 백업으로 해당 SLOT을 복원할 수도 있습니다.

## LOAD 화면 표시 정보

현재 변환기는 `sdslot.dat`을 수정하지 않습니다.

따라서 LOAD 화면에서:

- 날짜
- 플레이 시간
- 난이도
- Times Cleared
- 기타 표시 정보

가 기존 한국판 세이브 정보로 남아 있을 수 있습니다.

실제 게임 데이터와는 별개의 표시용 메타데이터입니다.

게임에서 변환된 세이브를 정상적으로 불러온 뒤 다시 저장하면 게임이 해당 정보를 다시 갱신할 수 있습니다.

## 요구 사항

- Python 3.9 이상
- Persona 4 Golden Steam판
- Persona 4 Golden 한국 PS Vita판
- Title ID: `PCSH00021`
- `vita-savemgr`
- 세이브 백업 및 Restore가 가능한 PS Vita 환경

## 현재 상태

현재 버전은 **Experimental / Hardware Tested** 상태입니다.

다음 사항은 실제 PS Vita에서 확인되었습니다.

```text
변환된 세이브 정상 LOAD
C2-12828-1 없음
Steam 돈 계승 확인
Steam 인간 파라미터 계승 확인
```

다양한 진행도의 세이브와 NG+ 데이터에 대한 추가 테스트 및 피드백을 환영합니다.

## 주의

항상 원본 Vita 세이브를 별도로 백업해 두세요.

이 프로젝트는 비공식 커뮤니티 도구이며 ATLUS, SEGA, Sony, Valve와 관련이 없습니다.

Persona 4 Golden 및 관련 상표의 권리는 각 권리자에게 있습니다.

---

# English

## Overview

This tool converts **Persona 4 Golden Steam save files** for use with the **Korean PS Vita release (`PCSH00021`)**.

Existing P4G PC-to-Vita save converters generally target the North American and European Vita releases. The Korean release uses a slightly different save structure, and directly applying the standard Vita conversion layout can cause a:

`C2-12828-1`

error when loading the converted save.

This converter was developed by comparing real Steam and Korean Vita save files byte-by-byte and repeatedly testing converted saves on actual PS Vita hardware.

## Features

- Converts Steam P4G saves for Korean PS Vita version `PCSH00021`
- Supports New Game+ / clear-data-based saves
- Preserves Korean Vita-specific save structures
- Preserves Korean protagonist name buffers
- Preserves the Korean-specific structural value at `0x44`
- Preserves Vita Rescue / Retry sections
- Does not modify `sdslot.dat`
- Does not modify `system.bin`
- Validates Steam `.bin` / `.binslot` pairs
- Modifies an existing `vita-savemgr` SLOT in place
- Automatically creates a full ZIP backup before conversion
- Includes a ZIP backup restore function

## Confirmed Working

The converted save has been successfully loaded on actual Korean PS Vita hardware without the previous:

`C2-12828-1`

crash.

The following Steam New Game+ data has been confirmed to transfer correctly:

- Money
- Social Stats / Human Parameters
- General NG+ save state

Other NG+ data such as the Persona Compendium, Max Social Link reward items, costumes, Skill Card records, and related carry-over information are transferred as part of the main save data, but not every individual feature has been manually verified yet.

## Korean Save Structure Difference

The Korean Vita save structure is not completely identical to the NA/EU Vita format.

During testing, copying the Steam-equivalent value into Korean offset:

`0x44`

consistently caused the game to crash while loading.

Example from the tested save:

```text
Korean 0x44–0x47 : 64 0C 00 00
                  = 0x00000C64
                  = 3172

Steam equivalent : 74 0C 00 00
                  = 0x00000C74
                  = 3188
```

The difference is exactly:

```text
0x10 = 16 bytes
```

The known size difference between the Korean and PC name-related structures is also `0x10`, suggesting that this value is related to an internal Korean-specific structure offset or size.

For this reason, the converter always preserves the original Korean value at `0x44`.

## Final Conversion Rule

The following Korean Vita regions are preserved:

```text
KR 0x0010–0x0023
Korean name buffer #1

KR 0x0044
Korean-specific structural value

KR 0x0054–0x0067
Korean name buffer #2

KR 0x15100 onward
Korean Rescue / Retry / trailing save structure
```

The following files are also left untouched:

```text
sdslot.dat
system.bin
```

Most other mapped game-state data before `0x15100` is transplanted from the Steam save.

Current mapping:

```text
Korean 0x0000–0x000F
← same Steam offset

Korean 0x0024–0x0053
← Steam offset +0x10

except Korean 0x0044,
which is preserved

Korean 0x0068–0x150FF
← Steam offset +0x20
```

## Usage

1. Create a valid save in the Korean PS Vita version of Persona 4 Golden.

2. Run `vita-savemgr` on the Vita.

3. Create a backup SLOT for `PCSH00021` directly using `vita-savemgr`.

Example:

```text
ux0:data/savegames/PCSH00021/SLOT0
```

4. Make that savemgr SLOT accessible from your PC.

5. Run the converter.

6. Select your Steam Persona 4 Golden save directory.

Typical location:

```text
Steam\userdata\<SteamID>\1113000\remote
```

7. Select the existing:

```text
PCSH00021\SLOTn
```

folder that was created directly by `vita-savemgr`.

8. Select the Steam source save slot.

9. Select the Vita target game slot.

10. Run the conversion.

11. Return to the Vita.

12. Restore the **same vita-savemgr SLOT**.

13. Launch Persona 4 Golden and load the save.

## Very Important

Do not manually create or duplicate vita-savemgr SLOT folders on Windows.

For example:

```text
SLOT0 → SLOT1
```

should not be done using normal Windows folder copy.

Hardware testing showed:

```text
SLOT created directly by vita-savemgr
→ loads correctly

SLOT created by manually duplicating a folder on Windows
→ C2-12828-1
```

Always let `vita-savemgr` create the SLOT first, then modify that existing SLOT in place using this converter.

## Automatic Backups

Before conversion, the entire selected Vita savemgr SLOT is automatically backed up as a ZIP file.

Default Windows location:

```text
Documents\P4G_Vita_Backups
```

The GUI also includes an option to restore a previous ZIP backup into the existing SLOT.

## Save List Metadata

The converter intentionally does not modify `sdslot.dat`.

Because of this, the Vita LOAD screen may initially continue showing the original Korean save's:

- Date
- Play time
- Difficulty
- Times Cleared
- Other display metadata

This does not necessarily represent the actual converted game-state data.

After successfully loading the converted save and saving again in-game, the game may refresh this metadata itself.

## Requirements

- Python 3.9 or newer
- Persona 4 Golden on Steam
- Korean PS Vita release of Persona 4 Golden
- Title ID: `PCSH00021`
- `vita-savemgr`
- A PS Vita environment capable of backing up and restoring save data

## Project Status

Current status:

**Experimental / Hardware Tested**

The following have been confirmed on actual hardware:

```text
Converted save loads successfully
No C2-12828-1 crash
Steam money transferred correctly
Steam Social Stats transferred correctly
```

Additional testing with different game progress points and NG+ saves is welcome.

## Disclaimer

Always keep an untouched backup of your original Vita save.

This is an unofficial community tool and is not affiliated with ATLUS, SEGA, Sony, or Valve.

Persona 4 Golden and all related trademarks belong to their respective owners.
