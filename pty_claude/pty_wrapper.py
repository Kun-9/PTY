#!/usr/bin/env python3
import os
import pty
import selectors
import shutil
import signal
import subprocess
import sys
import termios
import tty
import time


def read_available(master_fd, sel, timeout=0.2):
    data_chunks = []
    events = sel.select(timeout)
    for key, _ in events:
        if key.fileobj == master_fd:
            try:
                chunk = os.read(master_fd, 4096)
            except OSError:
                chunk = b""
            if chunk:
                data_chunks.append(chunk)
            else:
                return b""
    return b"".join(data_chunks)


def send_notification():
    # macOS 알림 센터로 간단한 알림 발송
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'display notification "Claude 응답이 도착했습니다." with title "Claude"',
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    # 실행 모드와 명령 인자 분리
    demo_mode = False
    notify_mode = False
    # PTY 알림은 명시적으로 켜는 경우에만 동작
    user_args = []
    for arg in sys.argv[1:]:
        if arg == "--demo":
            demo_mode = True
        elif arg == "--notify":
            notify_mode = True
        elif arg == "--no-notify":
            notify_mode = False
        else:
            user_args.append(arg)

    # 실행할 명령을 인자, 환경 변수, PATH 순서로 결정
    if user_args:
        cmd = user_args
    else:
        env_cmd = os.environ.get("CLAUDE_PATH") or os.environ.get("CLAUDE_CODE_PATH")
        if env_cmd:
            cmd = [env_cmd]
        else:
            found = shutil.which("claude")
            cmd = [found] if found else []
    if not cmd:
        sys.stderr.write("claude 실행 파일을 찾지 못했습니다.\n")
        sys.stderr.write("PATH에 설치하거나 CLAUDE_PATH/CLAUDE_CODE_PATH로 경로를 지정하세요.\n")
        sys.stderr.write("또는 실행 파일 경로를 인자로 전달할 수 있습니다.\n")
        sys.exit(1)

    # PTY 쌍을 생성하고 터미널 환경을 구성
    master_fd, slave_fd = pty.openpty()
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")

    # PTY를 stdin/stdout/stderr로 연결해 프로세스를 시작
    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)

    # 읽기 이벤트를 등록해 PTY 출력을 비동기로 수신
    sel = selectors.DefaultSelector()
    sel.register(master_fd, selectors.EVENT_READ)
    stdin_fd = sys.stdin.fileno()
    old_tty = None
    notify_pending = False
    notify_on_any_output = False
    last_notify = 0.0
    notify_cooldown = 2.0
    terminate_requested = False

    # 외부에서 들어오는 종료 신호 감지
    def handle_signal(_signum, _frame):
        nonlocal terminate_requested
        terminate_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not demo_mode:
        # 터미널 입력을 즉시 전달하기 위해 raw 모드로 전환
        if sys.stdin.isatty():
            old_tty = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd)
            sel.register(sys.stdin, selectors.EVENT_READ)
        else:
            notify_on_any_output = True

    try:
        if demo_mode:
            # 초기 출력(프롬프트 등)을 받아 화면에 표시
            start = time.time()
            while time.time() - start < 2.0:
                out = read_available(master_fd, sel)
                if out:
                    sys.stdout.buffer.write(out)
                    sys.stdout.buffer.flush()

            # 간단한 명령 전송 및 응답 읽음
            os.write(master_fd, b"help\n")
            time.sleep(0.5)
            out = read_available(master_fd, sel, timeout=0.5)
            if out:
                sys.stdout.buffer.write(out)
                sys.stdout.buffer.flush()

            # 종료 명령 전송 및 남은 출력 정리
            os.write(master_fd, b"exit\n")
            for _ in range(10):
                out = read_available(master_fd, sel, timeout=0.2)
                if out:
                    sys.stdout.buffer.write(out)
                    sys.stdout.buffer.flush()
                if proc.poll() is not None:
                    break
            return

        # 실시간 입출력 전달 및 응답 도착 시 알림 발송
        while True:
            events = sel.select(timeout=0.2)
            for key, _ in events:
                if key.fileobj == master_fd:
                    data = os.read(master_fd, 4096)
                    if not data:
                        return
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    if notify_mode and (notify_pending or notify_on_any_output):
                        now = time.time()
                        if now - last_notify >= notify_cooldown:
                            send_notification()
                            last_notify = now
                        if notify_pending:
                            notify_pending = False
                elif key.fileobj == sys.stdin:
                    data = os.read(stdin_fd, 1024)
                    if data:
                        # 사용자가 Enter 입력 시 응답 알림 대기 시작
                        if b"\n" in data or b"\r" in data:
                            notify_pending = True
                        # 모든 입력을 PTY로 전달 (Ctrl+C 포함)
                        os.write(master_fd, data)
            if terminate_requested:
                break
            if proc.poll() is not None:
                break

    finally:
        # 리소스를 닫고 필요하면 하위 프로세스를 종료
        if old_tty is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty)
        sel.close()
        try:
            os.close(master_fd)
        except OSError:
            pass
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=2)


if __name__ == "__main__":
    main()
