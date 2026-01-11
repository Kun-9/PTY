# PTY Claude Code

Claude Code를 PTY 래퍼로 실행 / Hook 기반 알림 수신 모듈

## 주요 기능

- **PTY 래퍼**: Claude Code를 PTY 환경에서 실행하여 실시간 입출력 처리
- **Hook 알림**: PreToolUse, Stop, PermissionRequest 이벤트 알림 수신
- **설정 기반 필터링**: 특정 도구 및 이벤트만 선택적 알림 표시
- **프로젝트 구분**: 작업 디렉토리별 알림 구분 표시

## 요구사항

- Python 3.8 이상
- macOS (osascript 사용)
- Claude Code CLI 설치 및 PATH 등록

## 설치

```bash
# 프로젝트 클론
git clone <repository-url>
cd pty

# 패키지 설치 (선택사항)
pip install -e .
```

## 실행 방법

### 패키지 설치 후

```bash
# 개발 모드로 설치
pip install -e .

# 명령어로 실행
pty-claude
pty-claude --notify
pty-claude --demo
```

### 직접 실행

```bash
# 기본 실행
python3 -m pty_claude

# PTY 알림 활성화
python3 -m pty_claude --notify

# 데모 모드 (자동 명령 전송)
python3 -m pty_claude --demo

# Claude 경로 지정
CLAUDE_PATH=/path/to/claude python3 -m pty_claude
```

## Hook 설정

### 글로벌 설정

모든 프로젝트에서 알림을 받으려면 `~/.claude/settings.json` 파일에 hook 등록:

```bash
# 파일 생성 또는 수정
vi ~/.claude/settings.json
```

내용:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /${USER_PATH}/pty/pty_claude/hook_notify.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /${USER_PATH}/pty/pty_claude/hook_notify.py"
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /${USER_PATH}/pty/pty_claude/hook_notify.py"
          }
        ]
      }
    ]
  }
}
```

**주의**: `command`의 `${USER_PATH}` 경로를 본인의 실제 설치 경로로 수정

특정 프로젝트에만 적용하려면 Claude Code 실행 후 `/hooks` 명령으로 등록:

- **이벤트**: PreToolUse, Stop, PermissionRequest
- **명령**: `python3 /${USER_PATH}/pty/pty_claude/hook_notify.py`

### 알림 필터 설정

`pty_claude/config.json` 파일로 알림 선택 ON/OFF:

```json
{
  "PreToolUse": {
    "enabled": true,
    "tools": ["AskUserQuestion"]
  },
  "Stop": {
    "enabled": true
  },
  "PermissionRequest": {
    "enabled": true
  }
}
```

#### 설정 항목

- `enabled`: Hook 활성화 여부
- `tools`: 특정 도구만 필터링 (빈 배열 시 모든 도구)

## 파일 구조

```
pty/
├── pty_claude/                 # 메인 패키지
│   ├── __init__.py            # 패키지 초기화
│   ├── __main__.py            # 모듈 실행 진입점
│   ├── pty_wrapper.py         # PTY 래퍼 메인 스크립트
│   ├── hook_notify.py         # Hook 이벤트 처리 스크립트
│   └── config.json            # 알림 필터 설정
├── tests/                      # 테스트 디렉토리
│   └── __init__.py
├── .claude/                    # 프로젝트별 설정 (선택사항)
│   └── settings.json          # 로컬 Hook 등록 설정
├── pyproject.toml             # 패키지 메타데이터
├── MANIFEST.in                # 패키지 포함 파일
├── LICENSE                    # 라이센스
└── README.md
```

## 동작 원리

### PTY 래퍼

1. PTY 쌍 생성 및 터미널 환경 구성
2. Claude Code 프로세스를 PTY로 연결
3. 사용자 입력을 PTY로 전달
4. PTY 출력을 터미널에 실시간 표시
5. `--notify` 옵션 사용 시 응답 완료 알림 발송

### Hook 알림

1. Claude Code가 Hook 이벤트 발생 시 `hook_notify.py` 실행
2. stdin으로 JSON 데이터 수신 (hook_event_name, tool_name, cwd 등)
3. `config.json` 설정 확인
4. 필터 조건 충족 시 macOS 알림 표시

### 알림 예시

- **PreToolUse**: `Claude [pty] - 도구: AskUserQuestion`
- **Stop**: `Claude [pty] - 응답이 완료되었습니다.`
- **PermissionRequest**: `Claude [pty] - 권한 요청: Write`

## 특징

### Ctrl+C 동작

Claude Code 원래 동작 유지:
- 첫 번째 Ctrl+C: 입력 취소
- 두 번째 Ctrl+C: 종료

### 프로젝트별 알림

작업 디렉토리 이름이 알림 제목에 표시되어 여러 프로젝트 구분 가능
