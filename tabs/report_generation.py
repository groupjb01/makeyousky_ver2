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
api_key = os.getenv('API_KEY')
client = OpenAI(api_key=api_key)

# 한글 폰트 설정
font_path = 'KoPubDotumLight.ttf'
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


def generate_overall_opinion_prompt(student_info, university_list):
    prompt = f"""
    다음 전문지식과 학생 정보, 지원 가능 대학 목록을 참고하여 학생의 대학 지원에 대한 전략적이고 간결한 종합 의견을 제시해주세요.

    전문지식:
    {expert_knowledge}

    학생 정보:
    {student_info}

    지원 가능 대학 목록:
    {university_list}

    요구사항: 어조는 ~합니다. ~입니다. 등 정중한 어조로 하세요. 
    1. 학생의 현재 성적과 목표 대학 간의 격차를 분석하세요.
    2. 소신 지원과 그 외 지원의 균형을 제안하되, 각 카테고리별로 1-2개 대학을 추천하세요.
    3. 추천 대학의 3개년 입시 결과(경쟁률, 입결, 충원율)를 간략히 언급하고, 주기적 변동 가능성을 고려하세요.
    4. 200단어 이내로 작성하세요.
    """
    return prompt


def generate_top_3_recommendations_prompt(university_data, admission_type):
    # 최대 3개의 대학 데이터만 선택
    selected_data = university_data[:3]

    # 실제 데이터 개수
    data_count = len(selected_data)

    prompt = f"""
    다음 전문지식과 소신 지원 대상 대학 정보를 참고하여 {admission_type} 전형의 소신 지원 BEST {data_count}에 대한 간결하고 전략적인 분석을 제공해주세요. 전문지식을 참고하여 작성하세요.

    전문지식:
    {expert_knowledge}

    소신 지원 대상 대학 정보:
    {selected_data}

    요구사항: 어조는 ~합니다. ~입니다. 등 정중한 어조로 하세요. You never randomly generate fictitious data other than the data provided.  
    1. {admission_type} 전형에 대해서만 분석하세요.
    2. {data_count}개 대학/학과에 대해 분석하세요.
    3. 각 대학/학과의 3개년 경쟁률, 입결, 충원율 추이를 요약하고, 주기적 변동 패턴이 있는지 분석하세요.
    4. 경쟁률이 6대 1 이하인 경우 특별히 언급하고, 그 의미와 다음 해 변동 가능성을 설명하세요.
    5. 모집인원의 변화가 40% 이상인 경우 이를 지적하고, 그 영향을 분석하세요.
    6. 50%와 70% 컷의 차이가 큰 경우 이를 언급하고, 그 의미를 설명하세요.
    7. 각 대학/학과의 전형 방법이나 수능 최저 기준 변화가 있다면 언급하세요.
    8. 각 대학/학과별로 100단어 이내로 작성하되, 대학별로 한 문단씩 나누어 작성하세요. 한 대학 
    9. 응답 형식: 목록에 데이터가 1개 밖에 없다면 1개만 작성  
       1. 대학명 모집단위 : ~~~ 
       2. 대학명 모집단위 : ~~~ 
       3. 대학명 모집단위 : ~~~
    """

    for i in range(data_count):
        prompt += f"   {i + 1}. 대학명 학과명: 분석 내용\n"

    return prompt

def generate_detailed_analysis_prompt(university_info, admission_data, comparison_data):
    prompt = f"""
    다음 전문지식과 대학/학과 정보, 입시 데이터, 그리고 다른 학교와의 비교 데이터를 참고하여 상세 분석 보고서를 작성해 주세요. 전문지식을 참고하여 작성하세요.

    전문지식:
    {expert_knowledge}

    대학/학과 정보:
    {university_info}

    입시 데이터:
    {admission_data}

    다른 학교와의 비교 데이터:
    {comparison_data.to_string(index=False)}

    요구사항: 어조는 ~합니다. ~입니다. 등 정중한 어조로 하세요. 
    1. 3개년 데이터를 바탕으로 경쟁률, 입결, 충원율의 추이를 분석하고, 주기적 변동 패턴이 있는지 확인하세요.
    2. 경쟁률이 6대 1 이하이거나 10대 1 이상인 경우, 그 의미를 분석하고 다음 해 변동 가능성을 예측하세요.
    3. 모집인원 변화가 40% 이상인 경우, 그 영향을 설명하세요.
    4. 50%와 70% 컷의 차이를 분석하고, 그 의미를 설명하세요.
    5. 전형 방법이나 수능 최저 기준의 변화가 있다면 그 영향을 분석하세요.
    6. 학과의 선호도 변화 가능성(예: 경영학, 교육학, 행정학 등)을 고려하여 분석하세요.
    7. 주기적 변동성을 고려한 의견도 포함하세요.
    8. 다른 학교와의 비교 데이터를 활용하여 해당 대학/학과의 경쟁력을 분석하세요.
    9. 이 모든 것을 한 문단으로, 300단어 이내로 작성하세요.
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
    return response.choices[0].message.content.strip()


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

    # 심층 분석
    html += "<h4>심층 분석</h4>"

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
                        <th>학교유형</th>
                        <th>계열</th>
                        <th>희망계열</th>
                        <th>내신성적</th>
                        <th>수능최저역량</th>
                        <th>비교과 활동수준</th>
                        <th>주요과목 우수</th>
                    </tr>
                    <tr>
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
                <table>
                    <tr>
                        <th></th>
                        <th>교과</th>
                        <th>학생부 종합</th>
                    </tr>
        """

    for category in ['소신 지원', '적정 지원']:
        html += f"<tr><td>{category}</td>"
        for admission_type in ['교과', '학종']:  # '종합'을 '학종'으로 변경
            if admission_type in processed_data:
                df = processed_data[admission_type]['sincere' if category == '소신 지원' else 'appropriate']
                unis = [f"{row['대학명']} {row['모집단위']}" for _, row in df.iterrows()]
                formatted_unis = []
                for i in range(0, len(unis[:5]), 2):
                    if i + 1 < len(unis):
                        formatted_unis.append(f"{unis[i]}<br>{unis[i + 1]}")
                    else:
                        formatted_unis.append(unis[i])
                html += f"<td>{', '.join(formatted_unis)}</td>"
            else:
                html += "<td>-</td>"
        html += "</tr>"

    html += """
                </table>
            </div>
        """



    university_list = generate_university_list(final_selection)
    gpt_prompt = generate_overall_opinion_prompt(student_info, university_list)
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
                <h2>소신 지원 BEST 3 🌟</h2>
                <img src="data:image/png;base64,{encoded_best_3}" alt="Sincere Application Explanation">
            </div>
        """

    # 소신 지원 BEST 3 생성 부분 수정
    sincere_data = {
        '교과': processed_data.get('교과', {}).get('sincere', pd.DataFrame()),
        '학종': processed_data.get('학종', {}).get('sincere', pd.DataFrame())
    }

    if not (sincere_data['교과'].empty and sincere_data['학종'].empty):
        html += "<div class='section'>"
        html += "<h2>소신 지원 BEST 3 🌟</h2>"

        for admission_type in ['교과', '학종']:
            if not sincere_data[admission_type].empty:
                html += f"<div class='admission-type-box'>{admission_type if admission_type == '교과' else '종합'} 전형</div>"
                gpt_strategy_prompt = generate_top_3_recommendations_prompt(
                    sincere_data[admission_type].to_dict('records'), admission_type)
                gpt_strategy_response = generate_gpt_response(gpt_strategy_prompt)

                # 줄바꿈을 HTML <br> 태그로 변환
                gpt_strategy_response = gpt_strategy_response.strip().replace('\n', '<br>')

                # 변환된 응답을 HTML에 추가
                html += f"<p style='white-space: pre-wrap;'>{gpt_strategy_response}</p>"

        html += "</div>"

    else:
        html += "<p>소신 지원 BEST 3에 대한 데이터가 없습니다.</p>"


    html += "<h3>🔍 각 소신지원 안에 대해 자세히 설명드리겠습니다.</h3>"

    for admission_type, label in [('교과', '교과 전형'), ('학종', '종합 전형')]:
        if admission_type in processed_data and not processed_data[admission_type]['sincere'].empty:
            html += "<div class='section'>"
            html += f"<div class='admission-type-box'>{label}</div>"
            for i, (_, row) in enumerate(processed_data[admission_type]['sincere'].iterrows(), 1):
                html += analyze_university(row, all_data, i, admission_type, student_info)
            html += "</div>"
        else:
            html += f"<div class='section'><div class='admission-type-box'>{label}</div><p>{label}에 대한 소신지원 데이터가 없습니다.</p></div>"

    tables = generate_detailed_tables(processed_data)

    html += "<br>"  # 구분선 전 줄바꿈 추가
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<br>"  # 구분선 후 줄바꿈 추가
    html += "<div class='section'>"
    html += "<h2>지원 가능안 상세 📋</h2>"
    for i, table in enumerate(tables):
        html += f"<div class='admission-type-box'>{table['title'] if '교과' in table['title'] else '종합 전형'}</div>"
        if table['data'] is not None:
            html += f"<div class='detailed-table'>{table['data'].to_html(index=False)}</div>"
        else:
            html += f"<p>{table['title']} 지원 데이터가 없거나 필요한 열이 존재하지 않습니다.</p>"

        # 교과 전형과 종합 전형 사이에 줄바꿈 추가
        if i == 0:  # 첫 번째 테이블(교과 전형) 후에 줄바꿈 추가
            html += "<br>"

    html += "</div>"

    html += "<br>"
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<br>"
    html += "<div class='section'>"
    html += "<h2>대학별 2025학년도 핵심정리 🎓</h2>"

    all_filtered_data = pd.concat([final_selection['교과'], final_selection['학종']], ignore_index=True)

    # ranking을 사용하여 대학 정렬
    ranking_dict = {univ: i for i, univ in enumerate(ranking)}
    all_filtered_data['ranking'] = all_filtered_data['대학명'].map(ranking_dict)
    all_filtered_data = all_filtered_data.sort_values('ranking').drop('ranking', axis=1)

    unique_universities = all_filtered_data.drop_duplicates(subset=['대학명', '전형구분', '전형명'])


    for admission_type in ['교과', '종합']:
        html += f"<div class='admission-type-box'>{admission_type} 전형</div>"
        filtered_universities = unique_universities[unique_universities['전형구분'] == admission_type]

        for _, row in filtered_universities.iterrows():
            match = additional_data[(additional_data['대학명'] == row['대학명']) &
                                    (additional_data['전형구분'] == row['전형구분']) &
                                    (additional_data['전형명'] == row['전형명'])]
            if not match.empty:
                html += f"<h4 style='border-bottom: 1px solid var(--table-border-color); padding-bottom: 5px;'>{row['대학명']} - {row['전형명']}</h4>"
                core_summary = match.iloc[0]['2025학년도_핵심정리']
                core_summary_html = core_summary.replace('\n', '<br>')
                html += f"<p style='margin-left: 20px;'>{core_summary_html}</p>"

        html += "<br>"

    html += "</div>"


    # 신설/첨단융합학과 정보 추가
    html += "<hr style='border-top: 2px solid #bbb;'>"
    html += "<div class='section'>"
    html += "<br>"  # 줄바꿈과 공백 추가
    html += "<h2>대학별 신설/첨단융합학과 🔬</h2>"

    column_mapping = {
        '대학명': '대학명',
        '전형구분': '전형구분',
        '전형명': '전형명',
        '모집단위': '모집단위',
        '2025년_모집인원': '25년 모집인원',
        '2025년_최저요약': '25년 수능최저',
        '2024년_경쟁률': '24년 경쟁률',
        '2023년_경쟁률': '23년 경쟁률',
        '2024년_입결70%': '24년 입결70%',
        '2024년_충원율(%)': '24년 충원율(%)'
    }

    for i, admission_type in enumerate(['교과', '학종']):
        html += f"<div class='admission-type-box'>{admission_type if admission_type == '교과' else '종합'} 전형</div>"

        if f'{admission_type}_신설첨단' in final_selection:
            df = final_selection[f'{admission_type}_신설첨단'].copy()

            if not df.empty:
                # NaN 값을 '-'로 변경
                df = df.fillna('-')

                columns_to_display = ['대학명', '전형구분', '전형명', '모집단위', '25년 모집인원',
                                      '25년 수능최저', '24년 경쟁률', '23년 경쟁률', '24년 입결70%', '24년 충원율(%)']

                # 컬럼 이름 변경
                df.columns = [column_mapping.get(col, col) for col in df.columns]

                # 컬럼이 존재하는 경우에만 표시
                columns_to_display = [col for col in columns_to_display if col in df.columns]

                html += f"<div class='detailed-table'>{df[columns_to_display].to_html(index=False)}</div>"
            else:
                html += f"<p>{admission_type} 전형의 신설/첨단융합학과 데이터가 없습니다.</p>"

        else:
            html += f"<p>{admission_type} 전형의 신설/첨단융합학과 데이터가 없습니다.</p>"

        # 교과 전형과 종합 전형 사이에 줄바꿈 추가
        if i == 0:  # 첫 번째 전형(교과 전형) 후에 줄바꿈 추가
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
        '구분': '구분',
        '대학명': '대학명',
        '전형구분': '전형구분',
        '전형명': '전형명',
        '모집단위': '모집단위',
        '2025년_모집인원': '25년 모집인원',
        '2025년_최저요약': '25년 수능최저',
        '2024년_경쟁률': '24년 경쟁률',
        '2023년_경쟁률': '23년 경쟁률',
        '2024년_입결70%': '24년 입결70%',
        '2024년_충원율(%)': '24년 충원율(%)'
    }

    columns_to_display = ['구분', '대학명', '전형구분', '전형명', '모집단위', '25년 모집인원',
                          '25년 수능최저', '24년 경쟁률', '23년 경쟁률', '24년 입결70%', '24년 충원율(%)']

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

    if 'final_selection' not in st.session_state or 'student_info' not in st.session_state:
        st.warning("최종 필터링과 학생 정보 입력을 먼저 완료해주세요.")
        return

    final_selection = st.session_state['final_selection']
    student_info = st.session_state['student_info']
    all_data = st.session_state.get('all_data', pd.DataFrame())

    def preprocess_data(df):
        df = df[df.columns.intersection(needed_columns)]
        for col in needed_columns:
            if col not in df.columns:
                df[col] = np.nan
        return df[needed_columns]

    if st.button("보고서 생성"):
        with st.spinner("보고서 작성 중입니다..."):
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)

            final_selection = {
                '교과': preprocess_data(final_selection.get('교과', pd.DataFrame())),
                '학종': preprocess_data(final_selection.get('학종', pd.DataFrame())),
                '교과_신설첨단': preprocess_data(final_selection.get('교과_신설첨단', pd.DataFrame())),
                '학종_신설첨단': preprocess_data(final_selection.get('학종_신설첨단', pd.DataFrame()))
            }

            all_data = preprocess_data(all_data)

            additional_data = st.session_state['additional_data']
            html, tables, file_id = generate_report(final_selection, student_info, all_data, additional_data)

        st.success("보고서 생성이 완료되었습니다!")
        st.components.v1.html(html, height=600, scrolling=True)
        st.success(f"보고서가 Google Drive에 업로드되었습니다. File ID: {file_id}")


if __name__ == "__main__":
    show_report_generation()
