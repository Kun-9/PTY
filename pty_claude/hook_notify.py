#!/usr/bin/env python3
import json
import os
import subprocess
import sys


def load_config():
    """설정 파일에서 알림 규칙 로드"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        # 설정 파일이 없으면 모든 hook 비활성화
        return {}


def should_notify(hook_type, tool_name, config):
    """설정에 따라 알림 표시 여부 결정"""
    hook_config = config.get(hook_type, {})

    if not hook_config.get("enabled", False):
        return False

    # 도구 필터가 설정된 경우 확인
    tool_filter = hook_config.get("tools", [])
    if tool_filter and tool_name not in tool_filter:
        return False

    return True


def main():
    # 훅 입력(JSON)을 읽어 세션 흐름을 따라간다.
    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        hook_data = {}

    # 설정 파일 로드
    config = load_config()

    hook_type = hook_data.get("hook_event_name", "")

    # PreToolUse: 도구 사용 알림
    if hook_type == "PreToolUse":
        tool_name = hook_data.get("tool_name", "Unknown")
        cwd = hook_data.get("cwd", "")

        # 설정에 따라 알림 표시 여부 결정
        if should_notify(hook_type, tool_name, config):
            # 작업 디렉토리의 마지막 폴더명만 추출
            project_name = cwd.split("/")[-1] if cwd else "Unknown"

            # 알림 표시
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "도구: {tool_name}" with title "Claude [{project_name}]"',
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # JSON 응답 출력 (필수 - 자동 허용)
        print(json.dumps({"allow": True}))

    # Stop: 응답 완료 알림
    elif hook_type == "Stop":
        cwd = hook_data.get("cwd", "")

        # 설정에 따라 알림 표시 여부 결정
        if should_notify(hook_type, None, config):
            project_name = cwd.split("/")[-1] if cwd else "Unknown"

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "응답이 완료되었습니다." with title "Claude [{project_name}]"',
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    # PermissionRequest: 권한 요청 알림
    elif hook_type == "PermissionRequest":
        cwd = hook_data.get("cwd", "")
        tool_name = hook_data.get("tool_name", "Unknown")

        # 설정에 따라 알림 표시 여부 결정
        if should_notify(hook_type, tool_name, config):
            project_name = cwd.split("/")[-1] if cwd else "Unknown"

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "권한 요청: {tool_name}" with title "Claude [{project_name}]"',
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
