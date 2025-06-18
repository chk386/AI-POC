import base64
import datetime
import io
import os
from typing import Optional, Union

import markdown
import whisper
from IPython.display import Image as IPImage
from IPython.display import display
from langchain_core.messages import AIMessageChunk
from PIL import Image
from pydub import AudioSegment
from rembg import remove
from weasyprint import HTML


def merge_files(voice_files: list[str], output_file: str):
    """
    여러 개의 음성 파일을 하나로 합치는 함수

    Parameters:
    voice_files (list): 합칠 음성 파일들의 경로 리스트
    output_file (str): 합쳐진 음성 파일의 출력 경로

    Returns:
    None
    """
    combined = AudioSegment.empty()

    for mp3_file in voice_files:
        audio = AudioSegment.from_mp3(mp3_file)
        combined += audio

    combined.export(output_file, format="mp3")


def split_audio_by_speaker(diarization, audio_file_path, DATA_DIR="./data"):
    diarized_list = []
    audio = AudioSegment.from_file(audio_file_path)
    audio_file_name = audio_file_path.split("/")[-1]

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        # 오디오 파일 자르기
        start_time = turn.start * 1000  # pydub는 밀리초 단위 사용
        end_time = turn.end * 1000
        audio_segment = audio[start_time:end_time]

        # 자른 파일 저장
        segment_filename = f"{DATA_DIR}/{audio_file_name.split('.')[0]}_{turn.start:.2f}_{turn.end:.2f}_{speaker}.mp3"
        audio_segment.export(segment_filename, format="mp3")
        segment_result = extract_text_from_audio(segment_filename)

        result = {
            "시작시간": str(turn.start),
            "끝시간": str(turn.end),
            "화자": str(speaker),
            "텍스트": str(segment_result["text"]),
        }

        diarized_list.append(result)

    return diarized_list


def extract_text_from_audio(audio_file_path: str, model_type: str = "large"):
    # 모델 로드 (크기 옵션: tiny, base, small, medium, large)
    model: whisper.Whisper = whisper.load_model(name=model_type)

    result = model.transcribe(audio_file_path, language="ko")

    return result


def noise_volume_normalize(voice_file_path: str, noise_filter_freq=3000, volume_db=5):
    """
    노이즈 제거 및 소리 크기 조절
    """
    audio = AudioSegment.from_file(voice_file_path)
    # 노이즈 제거
    audio = audio.low_pass_filter(noise_filter_freq)

    # 소리 크기 조절
    more_loud = audio + volume_db

    name = voice_file_path.split(".")[0]
    ext = voice_file_path.split(".")[1]
    new_file_name = f"{name}_new.{ext}"
    more_loud.export(new_file_name, format="mp3")

    return new_file_name


def get_files_by_pattern(directory: str, file_pattern: str) -> list[str]:
    """
    주어진 디렉토리에서 'file_pattern'이 포함된 파일명을 반환하는 함수

    Parameters:
    directory (str): 파일을 검색할 디렉토리 경로
    file_name(str): 파일명 패턴

    Returns:
    list: 'file_pattern'이 포함된 파일명 리스트
    """
    speaker_files = []
    for filename in os.listdir(directory):
        filename = os.path.join(directory, filename)
        if file_pattern in filename:
            speaker_files.append(filename)

    speaker_files.sort()

    return speaker_files


def get_dir(file_name: str):
    dir = f"./{os.path.splitext(os.path.basename(file_name))[0]}"

    # DATA_DIR가 없으면 디렉토리 생성 함수
    if not os.path.exists(dir):
        os.makedirs(dir)

    return dir


if __name__ == "__main__":
    import os

    current_directory = os.path.dirname(os.path.abspath(__file__))
    noise_volume_normalize(voice_file_path=f"{current_directory}/ayun.mp3")


def stream_response(response, return_output=False):
    """
    AI 모델로부터의 응답을 스트리밍하여 각 청크를 처리하면서 출력합니다.

    이 함수는 `response` 이터러블의 각 항목을 반복 처리합니다. 항목이 `AIMessageChunk`의 인스턴스인 경우,
    청크의 내용을 추출하여 출력합니다. 항목이 문자열인 경우, 문자열을 직접 출력합니다. 선택적으로, 함수는
    모든 응답 청크의 연결된 문자열을 반환할 수 있습니다.

    매개변수:
    - response (iterable): `AIMessageChunk` 객체 또는 문자열일 수 있는 응답 청크의 이터러블입니다.
    - return_output (bool, optional): True인 경우, 함수는 연결된 응답 문자열을 문자열로 반환합니다. 기본값은 False입니다.

    반환값:
    - str: `return_output`이 True인 경우, 연결된 응답 문자열입니다. 그렇지 않으면, 아무것도 반환되지 않습니다.
    """
    answer = ""
    for token in response:
        if isinstance(token, AIMessageChunk):
            answer += token.content
            print(token.content, end="", flush=True)
        elif isinstance(token, str):
            answer += token
            print(token, end="", flush=True)
    if return_output:
        return answer


def image_to_base64(image_path: str):
    with open(image_path, "rb") as image_file:
        # 파일을 바이너리로 읽어서 base64로 인코딩
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def bytes_to_base64(image_bytes: bytes) -> str:
    """
    이미지 바이트 데이터를 base64 문자열로 인코딩합니다.

    매개변수:
        image_bytes (bytes): base64로 인코딩할 이미지 바이트 데이터

    반환값:
        str: base64로 인코딩된 문자열
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def remove_background(input_path: str):
    with open(input_path, "rb") as file:
        return remove(file.read())


def base64_to_file(
    base64_string: str,
    output_path: str = None,
    prefix: str = "base64_output",
    extension: str = "jpg",
) -> str:
    """
    Base64 문자열을 파일로 저장합니다.

    매개변수:
        base64_string (str): 저장할 Base64 인코딩된 문자열
        output_path (str, optional): 저장할 파일 경로. None인 경우 자동 생성됨
        prefix (str, optional): 자동 생성된 파일명의 접두사. 기본값은 "base64_output"
        extension (str, optional): 파일 확장자. 기본값은 "jpg"

    반환값:
        str: 저장된 파일의 경로
    """
    # Base64 문자열을 바이트로 디코딩
    try:
        # Base64 문자열에서 'data:image/jpeg;base64,' 같은 헤더가 있으면 제거
        if ";base64," in base64_string:
            base64_string = base64_string.split(";base64,")[1]

        bytes_data = base64.b64decode(base64_string)
    except Exception as e:
        raise ValueError(f"Base64 디코딩 중 오류 발생: {str(e)}")

    # 바이트 데이터를 파일로 저장하는 기존 함수 활용
    return save_bytes_to_file(bytes_data, output_path, prefix, extension)


def save_bytes_to_file(bytes_data, output_path=None, prefix="output", extension="jpg"):
    """
    바이트 데이터를 파일로 저장합니다.

    매개변수:
        bytes_data (bytes): 저장할 바이트 데이터
        output_path (str, optional): 저장할 파일 경로. None인 경우 자동 생성됨
        prefix (str, optional): 자동 생성된 파일명의 접두사. 기본값은 "output"
        extension (str, optional): 파일 확장자. 기본값은 "jpg"

    반환값:
        str: 저장된 파일의 경로
    """
    # 출력 경로가 지정되지 않은 경우 타임스탬프를 이용해 파일명 생성
    if output_path is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.getcwd()  # 현재 작업 디렉토리
        filename = f"{prefix}_{timestamp}.{extension}"
        output_path = os.path.join(output_dir, filename)

    # 디렉토리가 존재하지 않으면 생성
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 바이트 데이터를 파일로 저장
    with open(output_path, "wb") as file:
        file.write(bytes_data)

    print(f"파일이 저장되었습니다: {output_path}")
    return output_path


def display_image(
    image: Union[Image.Image, bytes, str],
    width: Optional[int] = None,
    height: Optional[int] = None,
    format: str = "PNG",
):
    """
    주피터 노트북에서 이미지를 지정된 크기로 표시합니다.

    매개변수:
        image: PIL.Image 객체, 이미지 바이트 또는 이미지 경로
        width: 표시할 이미지 너비 (픽셀)
        height: 표시할 이미지 높이 (픽셀)
        format: 이미지 형식 ('PNG', 'JPEG' 등)
    """
    # 이미지 객체 준비
    if isinstance(image, str):
        # 파일 경로인 경우
        pil_image = Image.open(image)
        close_after = True
    elif isinstance(image, bytes):
        # 바이트 데이터인 경우
        pil_image = Image.open(io.BytesIO(image))
        close_after = True
    elif isinstance(image, Image.Image):
        # 이미 PIL 이미지 객체인 경우
        pil_image = image
        close_after = False
    else:
        raise TypeError(
            "지원되지 않는 이미지 형식입니다. PIL.Image 객체, 바이트 또는 파일 경로여야 합니다."
        )

    # 이미지를 바이트로 변환
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format)
    buffer.seek(0)

    # 필요한 경우 원본 이미지 닫기
    if close_after:
        pil_image.close()

    # IPython.display.Image로 표시
    display(IPImage(data=buffer.getvalue(), width=width, height=height))


def markdown_to_pdf(markdown_text: str, output_pdf: str):
    """
    마크다운 파일을 PDF로 변환합니다.

    Args:
        markdown_text (str): 입력 마크다운 문자열
        output_pdf (str): 출력 PDF 파일 경로
    """

    # 마크다운을 HTML로 변환
    html_text = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])

    # 기본 HTML 템플릿에 내용 삽입
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Markdown to PDF</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 2cm; }}
            code {{ background-color: #f4f4f4; padding: 2px 4px; }}
            pre {{ background-color: #f4f4f4; padding: 10px; }}
            img {{ max-width: 100%; }}
        </style>
    </head>
    <body>
        {html_text}
    </body>
    </html>
    """

    # HTML을 PDF로 변환
    HTML(string=html_template).write_pdf(output_pdf)

    print(f"PDF가 성공적으로 생성되었습니다: {output_pdf}")
