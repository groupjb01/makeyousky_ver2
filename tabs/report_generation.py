import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from openai import OpenAI
import os
from dotenv import load_dotenv
import matplotlib.font_manager as fm
import numpy as np
import time
from data_loader import expert_knowledge
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import matplotlib as mpl
from matplotlib.backends.backend_svg import FigureCanvasSVG
from data_loader import university_groups, get_university_group, get_group_universities
from data_loader import ranking


# 환경 변수 로드 및 OpenAI 클라이언트 설정
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# 한글 폰트 설정
font_path = '/Users/isaac/Library/Fonts/KoPubDotumLight.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['font.size'] = 12
plt.rcParams['axes.unicode_minus'] = False

# 전역 폰트 설정 추가
mpl.rcParams['font.family'] = font_prop.get_name()
mpl.rcParams['axes.unicode_minus'] = False

# Seaborn 스타일 설정
sns.set_theme(style="whitegrid", palette="pastel")

# 색상 정의
TARGET_COLOR = '#1E90FF'  # 파란색
SERIES_COLOR = '#FFA500'  # 주황색
OTHER_COLOR = '#32CD32'  # 초록색


def set_font_for_all_axes(fig):
    for ax in fig.get_axes():
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                     ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontproperties(font_prop)
        # 범례에도 폰트 적용
        if ax.get_legend() is not None:
            for text in ax.get_legend().get_texts():
                text.set_fontproperties(font_prop)


def format_value(value):
    if pd.isna(value):
        return '-'
    elif isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def save_report_as_html(report, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)


def upload_to_google_drive(filename):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = 'ipsi-428408-4e099f78a875.json'

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    drive_service = build('drive', 'v3', credentials=credentials)

    folder_id = '1W6siHzHU0BmkM9ZI33c_Q-wSuuTUi5k3'
    file_metadata = {
        'name': filename,
        'parents': [folder_id],
        'mimeType': 'text/html'
    }
    media = MediaFileUpload(filename, resumable=True, mimetype='text/html')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')
    return file.get('id')


needed_columns = [
    '대학명', '전형구분', '전형명', '모집단위', '계열', '계열구분', '계열상세명',
    '2025년_모집인원', '2024년_모집인원', '2023년_모집인원', '2022년_모집인원',
    '전년대비2025년_모집인원변화', '그룹',
    '2024년_경쟁률', '2023년_경쟁률', '2022년_경쟁률',
    '2024년_입결70%', '2023년_입결70%', '2022년_입결70%',
    '2024년_입결50%', '2023년_입결50%', '2022년_입결50%',
    '2024년_충원율(%)', '2023년_충원율(%)', '2022년_충원율(%)',
    '2024년_추가합격자수', '2023년_추가합격자수', '2022년_추가합격자수',
    '2025년_최저요약', '2025년_수능최저코드', '2024년_수능최저',
    '2024년_경쟁률백분위', '2024년_경쟁률변동(%)', '2024년_계열경쟁률변동(%)',
    '3개년_경쟁률_평균', '3개년_경쟁률_변동(%)',
    '2024년_입결70%변동(%)', '3개년_입결70%_평균', '3개년_입결50%_평균',
    '2024년_충원율백분위', '2024년_충원율변동(%)', '3개년_충원율_평균',
    '2024년_계열경쟁률', '2023년_계열경쟁률', '2022년_계열경쟁률',
    '2024년_계열입결70%', '2023년_계열입결70%', '2022년_계열입결70%', '2024년_계열입결70%변동(%)',
    '2024년_계열충원율(%)', '2023년_계열충원율(%)', '2022년_계열충원율(%)',
    '3개년_계열경쟁률_평균', '3개년_계열입결70%_평균', '3개년_계열충원율_평균', '2024년_계열충원율변동(%)'
]


def generate_overall_opinion_prompt(student_info, university_list, university_data):
    prompt = f"""
    다음 전문지식과 학생 정보, 지원 가능 대학 목록, 모집단위 정보, 입시 데이터를 참고하여 학생의 대학 지원에 대한 전략적이고 간결한 종합 의견을 제시해주세요.

    전문지식:
    {expert_knowledge}
    
    학생 정보:
    {student_info}
    
    지원 가능 대학 목록:
    {university_list}  
    
    지원 대학 데이터 : 
    {university_data} 
    
    
    # 요구사항:
    아래 형식에 맞춰 작성하되, 전체 내용은 200단어 이내로 제한하세요. 각 섹션을 문단 형태로 기술하고, 핵심 내용은 간결하게 표현하세요. 전문가 지식을 활용하여 분석 및 조언을 제공하되, 프롬프트에 직접적으로 언급하지 마세요. 예를 들어, 전문가 지식에 학교 랭킹을 그룹별로 나눠놨는데 그룹 1에 속한 대학이고 이런 건 언급금지. 단지 비슷한 대학 수준과 랭킹을 참고하는 정도로 하라는 의미임. 
    대신, 이 지식을 바탕으로 학생의 상황에 맞는 구체적이고 개별화된 조언을 제시하세요.
    입결은 수치가 1.00에 가까울수록 높은 성적을 의미하고, 상대적으로 입결70% 수치가 낮으면 이를 '입결이 높다'라고 함을 명심하세요.
    특정 모집단위의 입결이 높다고 '우수'하다거나 '경쟁력'있다고 표현하지 말고, 학생의 성적과 비교해서 도전 가능성이 있다 등으로 표현할 것(학생 성적 < 입결70%인 경우나 성적이 입결과 근사한 경우)
    만약 '입결70% < 학생 성적'인 상황이면 커트라인이 성적보다 높은 곳에 지원하는 상황이기 때문에 이 점에 대해 적절히 설명할 것. 
    비교 분석 시 "~보다 높다/낮다"는 표현을 사용하여 명확히 비교하세요.

    어조는 ~합니다. ~입니다. 를 유지하세요. 

    
    # 출력 형식 : 각 섹션을 번호로 구분하고, 세부 내용은 반드시 문단 형태로 작성하세요. 
    
    고정 멘트 : (학생이름) 학생의 성적, 수능최저역량, 생활기록부 기재 수준, 주요과목 역량을 종합적으로 분석하여 다음과 같은 전략을 제안드립니다. (student_info에 입력이 다 돼 있는 경우. 수능최저 역량을 안적었다면 수능최저 역량을 빼고 ~를 고려하여 라고 결측된 정보를 빼고 멘트 작성)
    
    1. 전형 선택  
    (지원가능 대학 목록을 보고 교과 전형 또는 종합전형이 어느 정도로 분포 돼 있는지를 보고 멘트 작성.) 
    (지원가능 대학 목록에 교과, 종합 전형 중 하나라도 아예 없거나 한 쪽이 절대적으로 많은 경우 이유를 설명. 종합 전형을 추천하는 경우에는 생활기록부 내용이 강점이 있는 경우이며, 교과 전형을 주로 추천하는 경우는 학생의 내신성적이 높거나 수능최저역량이 높은 경우가 많음. 이를 참고하여 이유를 설명.) 
    (개조식이 아닌 문단 형태로 작성하세요. 불렛포인트는 사용하지 마세요.)
    
    2. 추천 대학 및 모집단위 
    (3-5개의 대학/학과를 추천하고, 각각의 경쟁률, 입결, 수능최저기준, 선택 근거를 간단히 설명. 
    (전형을 구분하여 기술(교과)중앙대학교 기계공학부는~ / (종합)동국대학교 경영학과는~)
    (개조식이 아닌 문단 형태로 작성하세요. 불렛포인트는 사용하지 마세요.)
    
    3. 수능최저 등 전반적인 지원 전략
    (수능 준비 전략, 전반적인 지원 전략, 주의해야 할 점 등을 설명)
    (3학년은 내신성적, 생활기록부 내용을 보완할 수 있는 시기가 끝났으므로 학교 성적 향상, 생활기록부 내용 강화 등은 권유하지 말 것.)
    (개조식이 아닌 문단 형태로 작성하세요. 불렛포인트는 사용하지 마세요.)
    
    고정 멘트 : 위 내용을 고려해서 최종 지원 전략을 수립하시기 바랍니다. 각 대학 및 학과에 대한 자세한 내용은 대학별 심층분석 내용을 참고바랍니다.
    
    예시) 
    
    A 학생의 성적, 수능최저역량, 생활기록부 기재 수준, 주요과목 역량을 종합적으로 분석하여 다음과 같은 전략을 제안드립니다.
    
    1. 전형 선택
    • 교과전형과 종합전형을 균형있게 고려해볼 필요가 있습니다. 
    • 교과전형의 경우 수능최저학력기준을 충족할 수 있는지가 관건이 될 것으로 보입니다. 
    • 종합전형은 생활기록부 기재 수준이 중요한데, '중' 수준으로 평가된다면 어느 정도 경쟁력이 있을 것으로 예상됩니다.
    
    2. 지원 대학 및 학과 선정
    • 중앙대학교 전자전기공학부: 경쟁률이 높은 편이나(2024년 7.50:1), 학생의 희망 전공과 정확히 일치합니다. 단, 수능최저학력기준(3합7)을 충족할 수 있는지 신중히 고려해야 합니다.
    • 건국대학교 전기전자공학부: 경쟁률(2024년 11.14:1)이 다소 높지만, 수능최저학력기준이 없어 지원의 기회가 있을 수 있습니다.
    • 서울과학기술대학교 전기정보공학과: 상대적으로 낮은 경쟁률(2024년 5.03:1)을 보이고 있어 지원을 고려해볼 만합니다. 수능최저학력기준(2합7)도 상대적으로 달성 가능성이 높아 보입니다.    
    • 아주대학교 전자공학과: 직접적인 데이터는 없지만, 산업공학과의 경우 2024년 경쟁률이 8.94:1로 중간 수준입니다. 전자공학과도 비슷한 수준일 것으로 예상되며, 지원을 고려해볼 만합니다.    
    • 동국대학교 전자전기공학부: 종합전형의 경우 2024년 경쟁률이 13.41:1로 다소 높은 편이나, 교과전형은 상대적으로 낮을 수 있습니다. 수능최저가 없어 기회가 있을 수 있습니다.
    
    3. 수능 대비
    • 현재 수능최저역량이 낮은 편이므로, 이를 높이는 것이 선택의 폭을 넓힐 수 있는 중요한 전략이 될 수 있습니다. 
    • 특히 자연계열에서 중요한 수학, 과학 과목에 집중할 필요가 있습니다.
    
    4. 지원 전략
    • 경쟁률과 입결의 주기적 변동을 고려해야 합니다. 
    • 작년에 경쟁률이 높았던 학과는 올해 다소 하락할 가능성이 있으므로, 이를 전략적으로 활용할 수 있습니다. 
    • 신설 학과나 학과 선호도 변화가 큰 전공의 경우 변동 가능성이 크므로 주의가 필요합니다.
    
    5. 안전장치
    • 지원 대학 선정 시 경쟁률, 충원율, 모집인원 변화 등을 종합적으로 고려하여 펑크 가능성을 최소화해야 합니다. 
    • 특히 모집인원이 5명 이하인 학과는 예측이 어려우므로 주의가 필요합니다.
    
    위 내용을 다각도로 고려해서 최종 지원 전략을 수립하시기 바랍니다. 각 대학 및 학과에 대한 자세한 내용은 대학별 심층분석 내용을 참고바랍니다.

    """
    return prompt


# def generate_top_3_recommendations_prompt(university_data, admission_type):
#     # 최대 3개의 대학 데이터만 선택
#     selected_data = university_data[:3]
#
#     # 실제 데이터 개수
#     data_count = len(selected_data)
#
#     prompt = f"""
#     다음 전문지식과 소신 지원 대상 대학 정보를 참고하여 {admission_type} 전형의 소신 지원 BEST {data_count}에 대한 간결하고 전략적인 분석을 제공해주세요. 전문지식을 참고하여 작성하세요.
#
#     전문지식:
#     {expert_knowledge}
#
#     소신 지원 대상 대학 정보:
#     {selected_data}
#
#     요구사항: 어조는 ~합니다. ~입니다. 등 정중한 어조로 하세요. You never randomly generate fictitious data other than the data provided.
#     1. {admission_type} 전형에 대해서만 분석하세요.
#     2. {data_count}개 대학/학과에 대해 분석하세요.
#     3. 각 대학/학과의 3개년 경쟁률, 입결, 충원율 추이를 요약하고, 주기적 변동 패턴이 있는지 분석하세요.
#     4. 경쟁률이 6대 1 이하인 경우 특별히 언급하고, 그 의미와 다음 해 변동 가능성을 설명하세요.
#     5. 모집인원의 변화가 40% 이상인 경우 이를 지적하고, 그 영향을 분석하세요.
#     6. 50%와 70% 컷의 차이가 큰 경우 이를 언급하고, 그 의미를 설명하세요.
#     7. 각 대학/학과의 전형 방법이나 수능 최저 기준 변화가 있다면 언급하세요.
#     8. 각 대학/학과별로 100단어 이내로 작성하되, 대학별로 한 문단씩 나누어 작성하세요. 한 대학
#     9. 응답 형식: 목록에 데이터가 1개 밖에 없다면 1개만 작성
#        1. 대학명 모집단위 : ~~~
#        2. 대학명 모집단위 : ~~~
#        3. 대학명 모집단위 : ~~~
#     """
#
#     for i in range(data_count):
#         prompt += f"   {i + 1}. 대학명 학과명: 분석 내용\n"
#
#     return prompt

def generate_detailed_analysis_prompt(university_info, admission_data, comparison_data):
    prompt = f"""
    다음 전문지식과 대학/학과 정보, 입시 데이터, 비교 데이터를 참고하여 상세 분석 보고서를 작성해 주세요.

    전문지식:
    {expert_knowledge}
    
    
    대학/모집단위 정보:
    {university_info}
    
    입시 데이터:
    {admission_data}
    
    비교 데이터:
    {comparison_data}
    
    요구사항:
    아래 형식에 맞춰 작성하되, 전체 내용은 300단어 이내로 제한하세요. 각 섹션을 문단 형태로 기술하고, 핵심 내용은 간결하게 표현하세요. 전문가 지식을 활용하여 분석 및 조언을 제공하되, 프롬프트에 직접적으로 언급하지 마세요. 예를 들어, 전문가 지식에 학교 랭킹을 그룹별로 나눠놨는데 그룹 1에 속한 대학이고 이런 건 언급금지. 단지 비슷한 대학 수준과 랭킹을 참고하는 정도로 하라는 의미임. 
    대신, 이 지식을 바탕으로 학생의 상황에 맞는 구체적이고 개별화된 조언을 제시하세요.
    각 섹션을 번호로 구분하고, 세부 내용은 불렛 포인트(•)로 작성하세요. 객관적이고 분석적인 어조를 유지하세요.
    입결은 수치가 1.00에 가까울수록 높은 성적을 의미하고, 상대적으로 입결70% 수치가 낮으면 이를 '입결이 높다'라고 함을 명심하세요.
    비교 분석 시 "~보다 높다/낮다"는 표현을 사용하여 명확히 비교하세요.
    어조는 ~합니다. ~입니다. 를 유지하세요. 
    
    ## 출력 형식:
    
    1. 경쟁률 및 입결 분석
    (최근 3년간의 경쟁률 추이, 입결 분석, 50%와 70% 컷의 차이, 3개년 평균과의 비교 등을 종합적으로 분석)
    
    2. 충원율 및 모집인원 분석
    (최근 충원율, 3개년 평균과의 비교, 모집인원 변화, 전형 방법이나 수능 최저 기준의 변화 등을 분석)
    
    3. 타학교 동일/유사계열 비교
    (2-3개의 타 대학 유사 학과와 경쟁률, 입결, 충원율 측면에서 비교 분석)
    
    4. 의견
    (전반적인 경쟁력, 학과의 선호도 변화 가능성, 주기적 변동성을 고려한 의견, 지원자를 위한 구체적인 조언 등을 종합적으로 제시)
    
    ## 예시 
    1. 경쟁률 분석
    • 아주대학교 산업공학과의 3개년 경쟁률 추이는 2022년 데이터가 없으나 2023년 18.21에서 2024년 8.94로 크게 감소했습니다.
    • 이는 경쟁률이 절반 이하로 줄어든 것으로, 지원 기회가 상대적으로 증가했다고 볼 수 있습니다. 
    • 그러나 여전히 8대 1이 넘는 경쟁률을 보이고 있어 상당한 경쟁이 예상됩니다.
    
    2. 입결 분석
    • 2024년 70% 입결은 2.24로 나타났습니다. 
    • 50% 컷과의 차이에 대한 정보는 제공되지 않았지만, 2.24라는 수치는 상위권 학생들이 지원하는 학과임을 보여줍니다. 
    • 3개년 평균과의 비교 데이터가 없어 추세를 파악하기는 어렵지만, 현재의 입결은 꽤 높은 수준입니다.
    
    3. 충원율 분석
    • 2024학년도 충원율은 68.75%로 중간 정도의 수준을 보이고 있습니다. 
    • 이는 합격자들의 등록 의지가 어느 정도 있으면서도 추가 합격의 기회도 존재할 수 있음을 의미합니다.
    
    4. 다른 학교와의 비교
    • 아주대학교 산업공학과의 경쟁률(8.94)은 동국대학교 산업시스템공학과(9.38)와 비슷한 수준이지만, 서울과학기술대학교 산업공학과(MSDE)(4.14)보다는 높습니다. 
    • 입결 면에서 아주대학교(2.24)는 서울과학기술대학교 산업공학과(MSDE)(1.92)보다 다소 낮은 편입니다. 
    • 충원율 측면에서는 아주대학교(68.75%)가 동국대학교(130.77%)보다 낮고, 서울과학기술대학교(200.00%)보다 훨씬 낮습니다.
    
    5. 의견
    • 최근 경쟁률이 크게 감소했지만, 여전히 높은 수준의 경쟁률을 유지하고 있어 지원 시 신중한 접근이 필요합니다.
    • 입결이 높은 편이므로, 지원을 고려하는 학생들은 자신의 교과 성적을 면밀히 검토해야 합니다.
    • 이 학과의 교과 전형은 수능최저학력기준으로 2개 영역 합 5등급 이내를 요구하고 있어, 수능 준비에도 신경을 써야 합니다.
    • 산업공학과의 특성상 수학과 과학 과목에 대한 이해도가 중요할 것으로 보입니다.
    • 최근의 급격한 경쟁률 하락이 일시적인 현상인지 지속될 것인지 지켜볼 필요가 있습니다.
    • 충원율이 다른 대학들에 비해 낮은 편인 점은 합격자들의 등록 의지가 상대적으로 높다는 것을 의미할 수 있습니다.
    
    종합적으로, 아주대학교 산업공학과는 경쟁률과 입결이 다른 대학들과 비교했을 때 중간 정도 수준이므로, 지원자의 성적과 목표에 따라 적절한 선택이 될 수 있습니다. 다만, 수능최저학력기준과 최근의 경쟁률 변화를 고려하여 신중하게 접근해야 할 것입니다.
    
    """
    return prompt


def generate_gpt_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "You are a helpful assistant that generates reports based on university admission data. Please refer to the expert knowledge provided in the prompt when answering. Answer in Korean."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    # GPT 응답의 줄바꿈을 HTML <br> 태그로 변환
    return response.choices[0].message.content.strip().replace('\n', '<br>')


def analyze_university(row, all_data, index, admission_type, student_info):
    html = f"<h3>{index}. {row['대학명']} {row['모집단위']} - {admission_type} 전형</h3>"

    # 경쟁률 분석
    html += "<h4>경쟁률 분석</h4>"
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 5))

    years = ['2022년', '2023년', '2024년']
    competition_rates = [row['2022년_경쟁률'], row['2023년_경쟁률'], row['2024년_경쟁률']]
    series_rates = [row['2022년_계열경쟁률'], row['2023년_계열경쟁률'], row['2024년_계열경쟁률']]

    ax1.plot(years, competition_rates, marker='o', color=TARGET_COLOR, label='모집단위')
    ax1.plot(years, series_rates, marker='o', linestyle='--', color=SERIES_COLOR, label='계열평균')
    ax1.set_title('3개년 경쟁률 추이')
    ax1.set_ylabel('경쟁률')
    ax1.legend()

    labels = ['2024년 경쟁률', '3개년 평균']
    unit_values = [row['2024년_경쟁률'], row['3개년_경쟁률_평균']]
    series_values = [row['2024년_계열경쟁률'], row['3개년_계열경쟁률_평균']]

    x = np.arange(len(labels))
    width = 0.35

    ax2.bar(x - width / 2, unit_values, width, label='모집단위', color=TARGET_COLOR)
    ax2.bar(x + width / 2, series_values, width, label='계열평균', color=SERIES_COLOR)
    ax2.set_title('2024년 vs 3개년 평균 경쟁률')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.legend()

    labels = ['모집단위', '계열평균']
    values = [row['2024년_경쟁률변동(%)'], row['2024년_계열경쟁률변동(%)']]

    ax3.barh(labels, values, color=[TARGET_COLOR, SERIES_COLOR])
    ax3.set_title('2024년 경쟁률 변동(%)')
    ax3.set_xlabel('변동률 (%)')
    for i, v in enumerate(values):
        ax3.text(v, i, f' {v:.2f}%', va='center')

    set_font_for_all_axes(fig)
    plt.tight_layout()

    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', bbox_inches='tight')
    svg = buffer.getvalue()
    plt.close(fig)

    html += f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" style="width:100%;max-width:1000px;">'

    html += f"<ul>"
    html += f"<li>2024학년도 경쟁률: {format_value(row['2024년_경쟁률'])} (계열 평균: {format_value(row['2024년_계열경쟁률'])})</li>"
    html += f"<li>2024학년도 경쟁률 변동(%): {format_value(row['2024년_경쟁률변동(%)'])} (계열 평균: {format_value(row['2024년_계열경쟁률변동(%)'])})</li>"
    html += f"<li>3개년 평균 경쟁률: {format_value(row['3개년_경쟁률_평균'])} (계열 평균: {format_value(row['3개년_계열경쟁률_평균'])})</li>"
    html += f"</ul>"

    # 입결 분석
    html += "<h4>입결 분석</h4>"
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 5))

    entrance_scores = [row['2022년_입결70%'], row['2023년_입결70%'], row['2024년_입결70%']]
    series_scores = [row['2022년_계열입결70%'], row['2023년_계열입결70%'], row['2024년_계열입결70%']]

    ax1.plot(years, entrance_scores, marker='o', color=TARGET_COLOR, label='모집단위')
    ax1.plot(years, series_scores, marker='o', linestyle='--', color=SERIES_COLOR, label='계열평균')
    ax1.set_title('3개년 입결 70% 추이', fontproperties=font_prop)
    ax1.set_ylabel('입결 70%', fontproperties=font_prop)
    ax1.set_xticklabels(years, fontproperties=font_prop)
    ax1.legend(prop=font_prop)

    labels = ['2024년 입결 70%', '3개년 평균']
    unit_values = [row['2024년_입결70%'], row['3개년_입결70%_평균']]
    series_values = [row['2024년_계열입결70%'], row['3개년_계열입결70%_평균']]

    x = np.arange(len(labels))
    width = 0.35

    ax2.bar(x - width / 2, unit_values, width, label='모집단위', color=TARGET_COLOR)
    ax2.bar(x + width / 2, series_values, width, label='계열평균', color=SERIES_COLOR)
    ax2.set_ylabel('입결 70%')
    ax2.set_title('2024년 vs 3개년 평균 입결 70%')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.legend()

    labels = ['모집단위', '계열평균']
    values = [row['2024년_입결70%변동(%)'], row['2024년_계열입결70%변동(%)']]

    ax3.barh(labels, values, color=[TARGET_COLOR, SERIES_COLOR])
    ax3.set_title('2024년 입결 70% 변동(%)', fontproperties=font_prop)
    ax3.set_xlabel('변동률 (%)', fontproperties=font_prop)
    for i, v in enumerate(values):
        ax3.text(v, i, f' {v:.2f}%', va='center')

    set_font_for_all_axes(fig)
    plt.tight_layout()

    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', bbox_inches='tight')
    svg = buffer.getvalue()
    plt.close(fig)

    html += f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" style="width:100%;max-width:1000px;">'

    html += f"<ul>"
    html += f"<li>2024학년도 70% 입결: {format_value(row['2024년_입결70%'])} (계열 평균: {format_value(row['2024년_계열입결70%'])})</li>"
    html += f"<li>2024학년도 70% 입결 변동(%): {format_value(row['2024년_입결70%변동(%)'])} (계열 평균: {format_value(row['2024년_계열입결70%변동(%)'])})</li>"
    html += f"<li>3개년 평균 70% 입결: {format_value(row['3개년_입결70%_평균'])} (계열 평균: {format_value(row['3개년_계열입결70%_평균'])})</li>"
    html += f"</ul>"

    # 충원율 분석
    html += "<h4>충원율 분석</h4>"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

    fill_rates = [row['2022년_충원율(%)'], row['2023년_충원율(%)'], row['2024년_충원율(%)']]
    series_fill_rates = [row['2022년_계열충원율(%)'], row['2023년_계열충원율(%)'], row['2024년_계열충원율(%)']]

    ax1.fill_between(years, fill_rates, alpha=0.5, color=TARGET_COLOR, label='모집단위')
    ax1.plot(years, fill_rates, 'o-', color=TARGET_COLOR)
    ax1.fill_between(years, series_fill_rates, alpha=0.5, color=SERIES_COLOR, label='계열평균')
    ax1.plot(years, series_fill_rates, 'o-', color=SERIES_COLOR)
    ax1.set_title('3개년 충원율 추이')
    ax1.set_ylabel('충원율 (%)')
    ax1.legend()

    labels = ['2024년 충원율', '3개년 평균']
    unit_values = [row['2024년_충원율(%)'], row['3개년_충원율_평균']]
    series_values = [row['2024년_계열충원율(%)'], row['3개년_계열충원율_평균']]

    x = np.arange(len(labels))
    width = 0.35

    ax2.bar(x - width / 2, unit_values, width, label='모집단위', color=TARGET_COLOR)
    ax2.bar(x + width / 2, series_values, width, label='계열평균', color=SERIES_COLOR)
    ax2.set_ylabel('충원율 (%)')
    ax2.set_title('2024년 vs 3개년 평균 충원율')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.legend()

    set_font_for_all_axes(fig)
    plt.tight_layout()

    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', bbox_inches='tight')
    svg = buffer.getvalue()
    plt.close(fig)

    html += f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" style="width:100%;max-width:1000px;">'

    html += f"<ul>"
    html += f"<li>2024학년도 충원율: {format_value(row['2024년_충원율(%)'])}% (계열 평균: {format_value(row['2024년_계열충원율(%)'])}%)</li>"
    html += f"<li>2024학년도 충원율 변동(%): {format_value(row['2024년_충원율변동(%)'])} (계열 평균: {format_value(row['2024년_계열충원율변동(%)'])})</li>"
    html += f"<li>3개년 평균 충원율: {format_value(row['3개년_충원율_평균'])}% (계열 평균: {format_value(row['3개년_계열충원율_평균'])}%)</li>"
    html += f"</ul>"

    # 다른 학교와 비교해보기 섹션
    html += "<h4>다른학교 같은 계열들과의 비교</h4>"

    university = row['대학명']
    group = row['그룹']
    current_admission_type = row['전형구분']
    current_field_type = row['계열구분']

    group_data = all_data[
        (all_data['그룹'] == group) &
        (all_data['전형구분'] == current_admission_type) &
        (all_data['계열구분'] == current_field_type)
        ]

    group_competition_rates = group_data.groupby('대학명')['2024년_계열경쟁률'].first()
    group_competition_rates[university] = row['2024년_경쟁률']

    group_entrance_scores = group_data.groupby('대학명')['2024년_계열입결70%'].first()
    group_entrance_scores[university] = row['2024년_입결70%']

    group_fill_rates = group_data.groupby('대학명')['2024년_계열충원율(%)'].first()
    group_fill_rates[university] = row['2024년_충원율(%)']

    # 비교 데이터 생성
    comparison_data = pd.DataFrame({
        '대학명': group_competition_rates.index,
        '경쟁률': group_competition_rates.values,
        '입결70%': group_entrance_scores.values,
        '충원율(%)': group_fill_rates.values
    })
    comparison_data = comparison_data.sort_values('대학명')

    # 시각화
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 5))

    # 경쟁률 비교
    all_universities = list(group_competition_rates.index)
    y_pos = np.arange(len(all_universities))
    ax1.bar(y_pos, group_competition_rates.values, color=OTHER_COLOR)
    ax1.bar(all_universities.index(university), group_competition_rates[university], color=TARGET_COLOR)
    ax1.set_title('경쟁률 비교')
    ax1.set_ylabel('경쟁률')
    ax1.set_xticks(y_pos)
    ax1.set_xticklabels(all_universities, rotation=45, ha='right')

    # 입결70% 비교
    ax2.bar(y_pos, group_entrance_scores.values, color=OTHER_COLOR)
    ax2.bar(all_universities.index(university), group_entrance_scores[university], color=TARGET_COLOR)
    ax2.set_title('입결70% 비교')
    ax2.set_ylabel('입결70%')
    ax2.set_xticks(y_pos)
    ax2.set_xticklabels(all_universities, rotation=45, ha='right')

    # 충원율 비교 (히트맵)
    data = pd.DataFrame({'충원율(%)': group_fill_rates})
    sns.heatmap(data.T, ax=ax3, cmap='YlOrRd', annot=True, fmt='.2f')
    ax3.set_title('충원율 비교')
    ax3.set_xticklabels(group_fill_rates.index, rotation=45, ha='right')

    set_font_for_all_axes(fig)
    plt.tight_layout()

    buffer = io.StringIO()
    fig.savefig(buffer, format='svg', bbox_inches='tight')
    svg = buffer.getvalue()
    plt.close(fig)

    html += f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" style="width:100%;max-width:1000px;">'

    # 표 형식으로 데이터 표시
    html += "<table style='width:100%; border-collapse: collapse; margin-top: 10px; font-size: 10px;'>"
    html += "<tr><th style='border: 1px solid black; padding: 5px; text-align: center;'>대학명</th><th style='border: 1px solid black; padding: 5px; text-align: center;'>경쟁률</th><th style='border: 1px solid black; padding: 5px; text-align: center;'>입결70%</th><th style='border: 1px solid black; padding: 5px; text-align: center;'>충원율(%)</th></tr>"

    for univ in group_competition_rates.index:
        html += f"<tr>"
        html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{univ}</td>"
        html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_competition_rates.get(univ, '-'))}</td>"
        html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_entrance_scores.get(univ, '-'))}</td>"
        html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_fill_rates.get(univ, '-'))}</td>"
        html += f"</tr>"

    html += f"<tr>"
    html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>평균</td>"
    html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_competition_rates.mean())}</td>"
    html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_entrance_scores.mean())}</td>"
    html += f"<td style='border: 1px solid black; padding: 5px; text-align: center;'>{format_value(group_fill_rates.mean())}</td>"
    html += f"</tr>"
    html += "</table>"

    # 분석 및 의견
    html += "<h4>분석 및 의견</h4>"
    university_info = f"{row['대학명']} {row['모집단위']} {admission_type} 전형"
    admission_data = row.to_dict()
    gpt_insight_prompt = generate_detailed_analysis_prompt(university_info, admission_data, comparison_data)
    gpt_insight_response = generate_gpt_response(gpt_insight_prompt)
    html += f"<p>{gpt_insight_response}</p>"

    html += "<hr>"

    return html


def generate_university_list(final_selection):
    html = ""
    for category, proportion in [("소신", 0.3), ("적정", 0.7)]:
        category_html = f"<h3>{category}:</h3>"
        category_has_data = False
        for admission_type in ['교과', '학종']:
            if admission_type in final_selection and not final_selection[admission_type].empty:
                df = final_selection[admission_type]
                if category == "소신":
                    filtered_df = df.head(int(len(df) * proportion))
                else:
                    filtered_df = df.tail(int(len(df) * (1 - proportion)))

                if not filtered_df.empty:
                    category_has_data = True
                    category_html += f"<h4>{admission_type} 전형:</h4>"
                    category_html += "<ul>"
                    for _, row in filtered_df.iterrows():
                        category_html += f"<li>{row['대학명']} {row['모집단위']}</li>"
                    category_html += "</ul>"

        if category_has_data:
            html += category_html

    return html


def generate_report(final_selection, student_info, all_data, additional_data):
    with open("header.png", "rb") as image_file:
        encoded_header = base64.b64encode(image_file.read()).decode()

    with open("/Users/isaac/Library/Fonts/KoPubDotumLight.ttf", "rb") as font_file:
        encoded_font = base64.b64encode(font_file.read()).decode()

    # 데이터 전처리 부분 수정
    processed_data = {}
    for admission_type in ['교과', '학종']:
        if admission_type in final_selection and not final_selection[admission_type].empty:
            df = final_selection[admission_type]
            total_count = len(df)
            sincere_count = int(total_count * 0.3)
            processed_data[admission_type] = {
                'sincere': df.head(sincere_count),
                'appropriate': df.tail(total_count - sincere_count)
            }
        else:
            processed_data[admission_type] = {
                'sincere': pd.DataFrame(),
                'appropriate': pd.DataFrame()
            }



    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>대학입시 전략 보고서</title>
        <style>
            @font-face {{
                font-family: 'KoPubDotum';
                src: url(data:font/truetype;charset=utf-8;base64,{encoded_font}) format('truetype');
                font-weight: normal;
                font-style: normal;
            }}
            :root {{
                --bg-color: #ffffff;
                --text-color: #333333;
                --table-border-color: #dddddd;
                --table-header-bg: #f2f2f2;
                --box-bg-color: #e6e6e6;
                --box-text-color: #333333;
            }}
            @media (prefers-color-scheme: dark) {{
                :root {{
                    --bg-color: #1e1e1e;
                    --text-color: #e0e0e0;
                    --table-border-color: #4a4a4a;
                    --table-header-bg: #2c2c2c;
                    --box-bg-color: #3a3a3a;
                    --box-text-color: #ffffff;
                }}
            }}
            body {{ 
                font-family: 'KoPubDotum', Arial, sans-serif; 
                line-height: 1.6; 
                padding: 20px; 
                font-size: 14px;
                background-color: var(--bg-color);
                color: var(--text-color);
            }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ 
                border: 1px solid var(--table-border-color); 
                padding: 8px; 
                text-align: center; 
            }}
            th {{ background-color: var(--table-header-bg); }}
            img {{ max-width: 100%; height: auto; }}
            .section {{ margin-bottom: 30px; }}
            .basic-info {{ font-size: 12px; }}
            .basic-info th, .basic-info td {{ padding: 4px; }}
            .detailed-table {{ font-size: 10px; }}
            .detailed-table th, .detailed-table td {{ padding: 3px; }}
            @media (prefers-color-scheme: dark) {{
                img {{
                    filter: brightness(.8) contrast(1.2);
                }}
            }}
            .admission-type-box {{
                background-color: var(--box-bg-color);
                color: var(--box-text-color);
                padding: 10px;
                margin-bottom: 15px;
                border-radius: 5px;
                font-weight: bold;
            }}
            @media print {{
                .admission-type-box {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    background-color: #e6e6e6 !important;
                    color: #333333 !important;
                }}
            }}
        </style>

    </head>
    <body>
        <img src="data:image/png;base64,{encoded_header}" alt="Report Header">

        <div class="section">
            <h2>기본 정보 🏫</h2>
            <table class="basic-info">
                    <tr>
                        <th>성명</th>
                        <th>학교유형</th>
                        <th>계열</th>
                        <th>희망계열</th>
                        <th>내신성적</th>
                        <th>수능최저역량</th>
                        <th>비교과 활동수준</th>
                        <th>주요과목 우수</th>
                    </tr>
                    <tr>
                        <td>{student_info['name']}</td>
                        <td>{student_info['school_type']}</td>
                        <td>{', '.join(student_info['field'])}</td>
                        <td>{', '.join(student_info['detail_fields'])}</td>
                        <td>{student_info['score']}</td>
                        <td>{student_info['lowest_ability']}</td>
                        <td>{student_info['non_subject_level']}</td>
                        <td>{'Yes' if student_info['major_subjects_strong'] == 'YES' else 'No'}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
    <h2>지원 가능선 🎯</h2>
    <table style="width:100%; border-collapse: collapse; font-size: 12px;">
        <tr>
            <th style="width:50%; border: 1px solid black; padding: 10px;">교과</th>
            <th style="width:50%; border: 1px solid black; padding: 10px;">종합</th>
        </tr>
        <tr>
            <td style="vertical-align: top; border: 1px solid black; height: 100px;">
                <table style="width:100%; height:100%; border-collapse: collapse;">
        """

    # 교과 데이터 추가
    if '교과' in final_selection and not final_selection['교과'].empty:
        for _, row in final_selection['교과'].iterrows():
            html += f"""
                    <tr>
                        <td style="padding: 5px; border: none;">{row['대학명']}</td>
                        <td style="padding: 5px; border: none;">{row['모집단위']}</td>
                    </tr>
                """
    else:
        html += "<tr><td style='padding: 5px; border: none; text-align: center; vertical-align: middle; height: 100px;'>-</td></tr>"

    html += """
                    </table>
                </td>
                <td style="vertical-align: top; border: 1px solid black; height: 100px;">
                    <table style="width:100%; height:100%; border-collapse: collapse;">
            """
    # 학종 데이터 추가
    if '학종' in final_selection and not final_selection['학종'].empty:
        for _, row in final_selection['학종'].iterrows():
            html += f"""
                    <tr>
                        <td style="padding: 5px; border: none;">{row['대학명']}</td>
                        <td style="padding: 5px; border: none;">{row['모집단위']}</td>
                    </tr>
                """
    else:
        html += "<tr><td style='padding: 5px; border: none; text-align: center; vertical-align: middle; height: 100px;'>-</td></tr>"

    html += """
                    </table>
                </td>
            </tr>
        </table>
    </div>
    """

    university_data = {
        '교과': final_selection.get('교과', pd.DataFrame()).to_dict('records'),
        '학종': final_selection.get('학종', pd.DataFrame()).to_dict('records')
    }
    university_list = generate_university_list(final_selection)
    gpt_prompt = generate_overall_opinion_prompt(student_info, university_list, university_data)
    gpt_response = generate_gpt_response(gpt_prompt)
    html += f"""
            <div class="section">
                <h2>종합 의견 📝</h2>
                <p>{gpt_response}</p>
            </div>
        """

    with open("best_3_explanation.png", "rb") as image_file:
        encoded_best_3 = base64.b64encode(image_file.read()).decode()

    html += f"""
        <div class="section">
            <h2>대학별 심층분석 🔍</h2>
            <img src="data:image/png;base64,{encoded_best_3}" alt="Sincere Application Explanation">
        </div>
    """

    def sort_by_ranking(df):
        ranking_dict = {univ: i for i, univ in enumerate(ranking)}
        df['ranking'] = df['대학명'].map(ranking_dict).fillna(len(ranking))
        return df.sort_values('ranking').drop('ranking', axis=1)

    for admission_type in ['교과', '학종']:
        html += f"<div class='admission-type-box'>{admission_type if admission_type == '교과' else '종합'} 전형</div>"

        if admission_type in final_selection and not final_selection[admission_type].empty:
            df = final_selection[admission_type]
            df_grouped = df.groupby('대학명').first().reset_index()
            df_sorted = sort_by_ranking(df_grouped)
            df_top_3 = df_sorted.head(3)

            for i, (_, row) in enumerate(df_top_3.iterrows()):
                html += analyze_university(row, all_data, i + 1, admission_type, student_info)
        else:
            html += f"<p>{admission_type if admission_type == '교과' else '종합'} 전형에서 추천하는 대학이 없습니다.</p>"

    html += "</div>"

    tables = generate_detailed_tables(processed_data)

    html += "<br>"  # 구분선 전 줄바꿈 추가
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<br>"  # 구분선 후 줄바꿈 추가
    html += "<div class='section'>"
    html += "<h2>지원 가능안 상세 📋</h2>"
    for i, table in enumerate(tables):
        html += f"<div class='admission-type-box'>{table['title'] if '교과' in table['title'] else '종합 전형'}</div>"
        if table['data'] is not None and not table['data'].empty:
            html += f"<div class='detailed-table'>{table['data'].to_html(index=False)}</div>"
        else:
            html += f"<p>{table['title'].split()[0]} 전형에서 추천하는 대학이 없습니다.</p>"

        # 교과 전형과 종합 전형 사이에 줄바꿈 추가
        if i == 0:  # 첫 번째 테이블(교과 전형) 후에 줄바꿈 추가
            html += "<br>"


    html += "</div>"

    html += "<br>"
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<br>"
    html += "<div class='section'>"
    html += "<h2>대학별 2025학년도 핵심정리 🎓</h2>"

    # 교과와 학종 데이터를 안전하게 결합
    all_filtered_data = pd.concat([
        final_selection.get('교과', pd.DataFrame()),
        final_selection.get('학종', pd.DataFrame())
    ], ignore_index=True)

    if not all_filtered_data.empty and '대학명' in all_filtered_data.columns:
        ranking_dict = {univ: i for i, univ in enumerate(ranking)}
        all_filtered_data['ranking'] = all_filtered_data['대학명'].map(ranking_dict)
        all_filtered_data = all_filtered_data.sort_values('ranking').drop('ranking', axis=1)
        unique_universities = all_filtered_data.drop_duplicates(subset=['대학명', '전형구분', '전형명'])
    else:
        unique_universities = pd.DataFrame(columns=['대학명', '전형구분', '전형명'])

    for admission_type in ['교과', '종합']:
        html += f"<div class='admission-type-box'>{admission_type} 전형</div>"
        filtered_universities = unique_universities[unique_universities['전형구분'] == admission_type]

        if not filtered_universities.empty:
            for _, row in filtered_universities.iterrows():
                match = additional_data[(additional_data['대학명'] == row['대학명']) &
                                        (additional_data['전형구분'] == row['전형구분']) &
                                        (additional_data['전형명'] == row['전형명'])]
                if not match.empty:
                    html += f"<h4 style='border-bottom: 1px solid var(--table-border-color); padding-bottom: 5px;'>{row['대학명']} - {row['전형명']}</h4>"
                    core_summary = match.iloc[0]['2025학년도_핵심정리']
                    core_summary_html = core_summary.replace('\n', '<br>')
                    html += f"<p style='margin-left: 20px;'>{core_summary_html}</p>"
        else:
            html += "<p>추천한 대학, 전형과 관련된 특이사항만 표시합니다.</p>"

        html += "<br>"

    html += "</div>"


    # 신설/첨단융합학과 정보 추가
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<div class='section'>"
    html += "<br>"  # 줄바꿈과 공백 추가
    html += "<h2>대학별 신설/첨단융합학과 🔬</h2>"

    column_mapping = {
        '대학명': '대학명',
        '전형명': '전형명',
        '모집단위': '모집단위',
        '2025년_모집인원': '모집인원',
        '2025년_최저요약': '수능최저',
        '2024년_경쟁률': '24 경쟁률',
        '2023년_경쟁률': '23 경쟁률',
        '2024년_입결70%': '24 입결70%',
        '2024년_충원율(%)': '24 충원율(%)'
    }

    for i, admission_type in enumerate(['교과', '학종']):
        html += f"<div class='admission-type-box'>{admission_type if admission_type == '교과' else '종합'} 전형</div>"

        if f'{admission_type}_신설첨단' in final_selection:
            df = final_selection[f'{admission_type}_신설첨단'].copy()

            if not df.empty:
                # 추천한 대학과 전형에 관련된 신설/첨단학과만 필터링
                recommended_universities = set(
                    final_selection[admission_type]['대학명']) if admission_type in final_selection else set()
                df = df[df['대학명'].isin(recommended_universities)]

                if not df.empty:
                    df = df.fillna('-')
                    columns_to_display = ['대학명', '전형명', '모집단위', '모집인원',
                                          '수능최저', '24 경쟁률', '23 경쟁률', '24 입결70%', '24 충원율(%)']
                    df.columns = [column_mapping.get(col, col) for col in df.columns]
                    columns_to_display = [col for col in columns_to_display if col in df.columns]
                    html += f"<div class='detailed-table'>{df[columns_to_display].to_html(index=False)}</div>"
                else:
                    html += "<p>추천한 대학, 전형과 관련된 신설/첨단학과만 표시합니다.</p>"
            else:
                html += "<p>추천한 대학, 전형과 관련된 신설/첨단학과만 표시합니다.</p>"
        else:
            html += "<p>추천한 대학, 전형과 관련된 신설/첨단학과만 표시합니다.</p>"

        if i == 0:
            html += "<br>"

    html += "</div>"

    html += """
            </body>
            </html>
            """

    html_filename = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    save_report_as_html(html, html_filename)

    file_id = upload_to_google_drive(html_filename)

    os.remove(html_filename)

    return html, tables, file_id


def generate_detailed_tables(processed_data):
    tables = []
    column_mapping = {
        '대학명': '대학명',
        '전형명': '전형명',
        '모집단위': '모집단위',
        '2025년_모집인원': '모집인원',
        '2025년_최저요약': '수능최저',
        '2024년_경쟁률': '24 경쟁률',
        '2023년_경쟁률': '23 경쟁률',
        '2024년_입결70%': '24 입결70%',
        '2024년_충원율(%)': '24 충원율(%)'
    }

    columns_to_display = ['대학명', '전형명', '모집단위', '모집인원',
                          '수능최저', '24 경쟁률', '23 경쟁률', '24 입결70%', '24 충원율(%)']

    for admission_type in ['교과', '학종']:
        if admission_type in processed_data:
            sincere_df = processed_data[admission_type]['sincere']
            appropriate_df = processed_data[admission_type]['appropriate']

            if not sincere_df.empty or not appropriate_df.empty:
                df = pd.concat([
                    sincere_df.assign(구분='소신'),
                    appropriate_df.assign(구분='적정')
                ])

                df = df.fillna('-')
                df.columns = [column_mapping.get(col, col) for col in df.columns]
                df = df[[col for col in columns_to_display if col in df.columns]]
                tables.append({
                    'title': f"{admission_type} 전형",
                    'data': df
                })
            else:
                tables.append({
                    'title': f"{admission_type} 전형",
                    'data': None
                })

    return tables


def show_report_generation():
    st.info("최종 필터링된 데이터로 보고서를 작성합니다.")

    # 세션 상태 초기화
    if 'report_data_source' not in st.session_state:
        st.session_state['report_data_source'] = "기존"

    # 보고서 작성 탭에서는 항상 기존 방식 사용
    st.session_state['report_data_source'] = "기존"

    if 'final_selection' not in st.session_state:
        st.warning("최종 필터링을 먼저 완료해주세요.")
        return

    final_selection = st.session_state['final_selection']
    student_info = st.session_state['student_info']
    new_advanced_data = {
        '교과': st.session_state.get('subject_new_or_advanced_filtered', pd.DataFrame()),
        '학종': st.session_state.get('comprehensive_new_or_advanced_filtered', pd.DataFrame())
    }

    all_data = st.session_state.get('all_data', pd.DataFrame())

    # 랭킹에 따라 데이터 재정렬
    def sort_by_ranking(df):
        if '대학명' in df.columns:
            ranking_dict = {univ: i for i, univ in enumerate(ranking)}
            df['ranking'] = df['대학명'].map(ranking_dict).fillna(len(ranking))
            return df.sort_values('ranking').drop('ranking', axis=1)
        return df

    # 각 카테고리별로 데이터 정렬
    for key in final_selection.keys():
        final_selection[key] = sort_by_ranking(final_selection[key])

    def preprocess_data(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=needed_columns)
        df = df[df.columns.intersection(needed_columns)]
        for col in needed_columns:
            if col not in df.columns:
                df[col] = np.nan
        return df[needed_columns]

    if st.button("보고서 생성"):
        with st.spinner("보고서 작성 중입니다..."):
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(1)
                progress_bar.progress(i + 1)

            processed_final_selection = {
                '교과': preprocess_data(final_selection.get('교과', pd.DataFrame())),
                '학종': preprocess_data(final_selection.get('학종', pd.DataFrame())),
                '교과_신설첨단': preprocess_data(new_advanced_data.get('교과', pd.DataFrame())),
                '학종_신설첨단': preprocess_data(new_advanced_data.get('학종', pd.DataFrame()))
            }

            all_data = preprocess_data(all_data)

            additional_data = st.session_state['additional_data']
            html, tables, file_id = generate_report(processed_final_selection, student_info, all_data, additional_data)

        st.success("보고서 생성이 완료되었습니다!")
        st.components.v1.html(html, height=600, scrolling=True)
        st.success(f"보고서가 Google Drive에 업로드되었습니다. File ID: {file_id}")

if __name__ == "__main__":
    show_report_generation()