import instaloader
import os
import sys
from datetime import datetime
from config import MY_USERNAME, MY_PASSWORD, TARGET_ACCOUNTS, SAVE_DIR


def get_loader():
    L = instaloader.Instaloader(
        dirname_pattern=os.path.join(SAVE_DIR, "{target}"),
        filename_pattern="{date_utc:%Y%m%d_%H%M%S}",
        download_video_thumbnails=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        compress_json=False,
        quiet=True,
    )
    return L


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


def download_stories(L, profile):
    """현재 올라와 있는 스토리 다운로드 (24시간짜리)"""
    try:
        stories = list(L.get_stories(userids=[profile.userid]))

        if not stories:
            print(f"  └ [스토리] 현재 올라온 스토리 없음")
            return 0

        count = 0
        for story in stories:
            for item in story.get_items():
                L.download_storyitem(item, target=os.path.join(SAVE_DIR, profile.username, "stories"))
                count += 1

        print(f"  └ [스토리] {count}개 저장")
        return count

    except instaloader.exceptions.PrivateProfileNotFollowedException:
        print(f"  └ [스토리] 비공개 계정 (팔로우 필요)")
        return 0
    except Exception as e:
        print(f"  └ [스토리] 오류: {e}")
        return 0


def download_highlights(L, profile):
    """하이라이트 전체 다운로드 (영구 보관된 스토리 모음)"""
    try:
        highlights = list(L.get_highlights(profile))

        if not highlights:
            print(f"  └ [하이라이트] 없음")
            return 0

        count = 0
        for highlight in highlights:
            folder = os.path.join(SAVE_DIR, profile.username, "highlights", highlight.title)
            os.makedirs(folder, exist_ok=True)
            for item in highlight.get_items():
                L.download_storyitem(item, target=folder)
                count += 1

        print(f"  └ [하이라이트] {len(highlights)}개 묶음, 총 {count}개 저장")
        return count

    except Exception as e:
        print(f"  └ [하이라이트] 오류: {e}")
        return 0


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print(f"\n{'='*40}")
    print(f"  인스타 스토리 다운로더")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*40}\n")

    L = get_loader()

    if not login(L):
        sys.exit(1)

    total = 0
    for username in TARGET_ACCOUNTS:
        print(f"\n[→] {username}")
        try:
            profile = instaloader.Profile.from_username(L.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"  └ 계정 없음: {username}")
            continue

        total += download_stories(L, profile)
        total += download_highlights(L, profile)

    print(f"\n{'='*40}")
    print(f"[완료] 총 {total}개 저장 → {os.path.abspath(SAVE_DIR)}")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
