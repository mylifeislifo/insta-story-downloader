import instaloader
import os
import sys
import json
import time
import argparse
from datetime import datetime
from config import MY_USERNAME, MY_PASSWORD, TARGET_ACCOUNTS, SAVE_DIR

TRACKING_FILE = ".downloaded_ids.json"


# ──────────────────────────────────────────
# 중복 추적
# ──────────────────────────────────────────

def load_downloaded() -> set:
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_downloaded(ids: set):
    with open(TRACKING_FILE, "w") as f:
        json.dump(list(ids), f)


# ──────────────────────────────────────────
# 로더 / 로그인
# ──────────────────────────────────────────

def get_loader():
    return instaloader.Instaloader(
        dirname_pattern=os.path.join(SAVE_DIR, "{target}"),
        filename_pattern="{date_utc:%Y%m%d_%H%M%S}",
        download_video_thumbnails=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        compress_json=False,
        quiet=True,
    )


def login(L):
    session_file = f".session_{MY_USERNAME}"

    if os.path.exists(session_file):
        try:
            L.load_session_from_file(MY_USERNAME, session_file)
            print(f"[✓] 세션 재사용: {MY_USERNAME}")
            return True
        except Exception:
            pass

    try:
        L.login(MY_USERNAME, MY_PASSWORD)
        L.save_session_to_file(session_file)
        print(f"[✓] 로그인 성공: {MY_USERNAME}")
        return True
    except instaloader.exceptions.BadCredentialsException:
        print("[✗] 아이디/비밀번호 오류. config.py 확인해줘.")
        return False
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        code = input("[!] 2단계 인증 코드 입력: ")
        L.two_factor_login(code)
        L.save_session_to_file(session_file)
        return True
    except Exception as e:
        print(f"[✗] 로그인 실패: {e}")
        return False


# ──────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────

def download_stories(L, profile, downloaded: set) -> int:
    try:
        stories = list(L.get_stories(userids=[profile.userid]))
        if not stories:
            print("  └ [스토리] 현재 없음")
            return 0

        new, skip = 0, 0
        for story in stories:
            for item in story.get_items():
                media_id = str(item.mediaid)
                if media_id in downloaded:
                    skip += 1
                    continue
                folder = os.path.join(SAVE_DIR, profile.username, "stories")
                os.makedirs(folder, exist_ok=True)
                L.download_storyitem(item, target=folder)
                downloaded.add(media_id)
                new += 1

        print(f"  └ [스토리] 신규 {new}개 저장 / {skip}개 중복 스킵")
        return new

    except instaloader.exceptions.PrivateProfileNotFollowedException:
        print("  └ [스토리] 비공개 계정 (팔로우 필요)")
        return 0
    except Exception as e:
        print(f"  └ [스토리] 오류: {e}")
        return 0


def download_highlights(L, profile, downloaded: set) -> int:
    try:
        highlights = list(L.get_highlights(profile))
        if not highlights:
            print("  └ [하이라이트] 없음")
            return 0

        new, skip = 0, 0
        for highlight in highlights:
            folder = os.path.join(SAVE_DIR, profile.username, "highlights", highlight.title)
            os.makedirs(folder, exist_ok=True)
            for item in highlight.get_items():
                media_id = str(item.mediaid)
                if media_id in downloaded:
                    skip += 1
                    continue
                L.download_storyitem(item, target=folder)
                downloaded.add(media_id)
                new += 1

        print(f"  └ [하이라이트] 신규 {new}개 저장 / {skip}개 중복 스킵")
        return new

    except Exception as e:
        print(f"  └ [하이라이트] 오류: {e}")
        return 0


# ──────────────────────────────────────────
# 1회 실행
# ──────────────────────────────────────────

def run_once(L):
    downloaded = load_downloaded()
    total_new = 0

    print(f"\n{'─'*44}")
    print(f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─'*44}")

    for username in TARGET_ACCOUNTS:
        print(f"\n[→] {username}")
        try:
            profile = instaloader.Profile.from_username(L.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"  └ 계정 없음: {username}")
            continue

        total_new += download_stories(L, profile, downloaded)
        total_new += download_highlights(L, profile, downloaded)

    save_downloaded(downloaded)
    print(f"\n  ✅ 이번 회차 신규 {total_new}개 저장")
    return total_new


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="인스타 스토리 자동 다운로더")
    parser.add_argument(
        "--interval", type=int, default=0,
        help="반복 실행 간격 (분). 0이면 1회만 실행. 예: --interval 30"
    )
    args = parser.parse_args()

    os.makedirs(SAVE_DIR, exist_ok=True)

    print(f"\n{'═'*44}")
    print(f"  📸 인스타 스토리 다운로더")
    if args.interval:
        print(f"  🔁 {args.interval}분마다 자동 실행")
    print(f"{'═'*44}")

    L = get_loader()
    if not login(L):
        sys.exit(1)

    if args.interval == 0:
        # 1회 실행
        run_once(L)
    else:
        # 주기 반복
        round_num = 1
        while True:
            print(f"\n  [Round {round_num}]")
            run_once(L)
            print(f"\n  ⏳ {args.interval}분 후 다시 실행... (Ctrl+C로 종료)")
            time.sleep(args.interval * 60)
            round_num += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[중단됨] 다운로더 종료.")
        sys.exit(0)
