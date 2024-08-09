import streamlit as st
import pandas as pd
from data_loader import data as all_data, SCHOOL_TYPE_ADJUSTMENT, lowest_ability_codes, lowest_ability_ui_options, \
    classify_data, remove_duplicates
from tabs.report_generation import generate_report, needed_columns
import numpy as np
import time

def preprocess_data(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=needed_columns)
    df = df[df.columns.intersection(needed_columns)]
    for col in needed_columns:
        if col not in df.columns:
            df[col] = np.nan
    return df[needed_columns]

def process_uploaded_data(user_data, all_data):
    # 사용자 데이터 전처리
    user_data = remove_duplicates(user_data)
    user_data = preprocess_data(user_data)

    # 신설/첨단 데이터 추출
    new_advanced_data = all_data[
        (all_data['분류'].isin(['신설', '첨단'])) &
        (all_data['대학명'].isin(user_data['대학명'])) &
        (all_data['전형구분'].isin(user_data['전형구분'])) &
        (all_data['계열구분'].isin(user_data['계열구분']))
    ]

    # 교과와 종합 전형 분리
    final_selection = {
        '교과': user_data[user_data['전형구분'] == '교과'],
        '학종': user_data[user_data['전형구분'] == '종합'],
        '교과_신설첨단': new_advanced_data[new_advanced_data['전형구분'] == '교과'],
        '학종_신설첨단': new_advanced_data[new_advanced_data['전형구분'] == '종합']
    }

    return final_selection, new_advanced_data

def show_direct_upload():
    st.session_state['report_data_source'] = "업로드"
    st.info("엑셀 파일을 업로드하고 기본 정보를 입력하세요.")

    uploaded_file = st.file_uploader("최종 선택 데이터 엑셀 파일 업로드", type="xlsx")

    if uploaded_file is not None:
        user_data = pd.read_excel(uploaded_file)
        st.success("파일 업로드 완료")

        # 기본 정보 입력
        st.markdown(
            """
            <style>
            [data-testid="stTabs"] button {
                flex: 1;
            }
            .stButton button {
                display: block;
                margin: 0 auto;
            }
            </style>
            """, unsafe_allow_html=True
        )
        st.info("수시전략 도출에 필요한 정보를 입력합니다.")

        student_name = st.text_input("👤 학생 이름을 입력하세요", key="direct_student_name")
        st.write(f"이름 : {student_name}")

        school_type = st.radio("🏫 고교 유형을 선택하세요", ["일반고", "학군지 일반고", "지역자사고", "전사고", "과학고", "외고"], index=0,
                               key="direct_school_type")

        field = st.multiselect("📚 계열을 선택하세요", ["인문", "자연"], key="direct_field")

        detail_field_options = {
            "인문": [
                "경영", "경제", "교육", "국어국문", "국제", "기타언어", "데이터",
                "독일독어", "디자인", "무역", "법학", "사회복지", "사회학", "스페인어",
                "스포츠", "심리", "아동유아", "언론미디어", "언어학", "역사(사학)", "영어영문",
                "일본어", "자유전공", "정치외교", "종교", "중국어", "지리", "철학", "첨단",
                "프랑스어", "행정", "AI(인문)"
            ],
            "자연": [
                "간호", "건설", "건축", "기계", "물리", "반도체", "보건", "산업공학", "생명",
                "생활과학", "수의학", "수학", "스마트팜", "식품", "신약개발", "약학", "에너지",
                "의학", "전기전자", "지구과학", "치대", "컴공", "통계", "한의예", "헬스케어",
                "화생공", "화학", "환경"
            ]
        }

        detail_fields_selected = []
        for selected_field in field:
            with st.expander(f"📂 세부 계열을 선택하세요 ({selected_field})"):
                detail_fields = st.multiselect(f"세부 계열 ({selected_field})", detail_field_options[selected_field],
                                               key=f"direct_{selected_field}")
                detail_fields_selected.extend(detail_fields)
        st.write(f"선택된 세부 계열 : {', '.join(detail_fields_selected)}")

        score = st.number_input("📊 성적을 입력하세요", min_value=1.00, max_value=9.00, value=2.00, step=0.10,
                                key="direct_score")
        if school_type in ["갓반고", "자사고"]:
            adjusted_score = max(score * 0.9, 1.00)
            st.write(f"입력한 성적: {score:.2f}, 조정된 성적: {adjusted_score:.2f}")
        else:
            adjusted_score = score
            st.write(f"입력한 성적: {score:.2f}")

        lowest_ability = st.selectbox("📉 수능최저 역량을 선택하세요", lowest_ability_ui_options, key="direct_lowest_ability")
        lowest_ability_code = lowest_ability_codes[lowest_ability]

        non_subject_level = st.radio("📒 비교과 활동 수준을 선택하세요", ["상", "중", "하"], index=1, key="direct_non_subject_level")

        major_subjects_strong = st.radio("주요과목 강함", ["YES", "NO"], index=1, key="direct_major_subjects_strong")

        gender = st.radio("👤 성별을 선택하세요", ["남자", "여자"], key="direct_gender")

        admission_type = st.multiselect("📝 전형 구분을 선택하세요", ["교과", "종합"], default=["교과", "종합"],
                                        key="direct_admission_type")

        if st.button("정보 입력", key="direct_info_submit"):
            adjustment_factor = SCHOOL_TYPE_ADJUSTMENT.get(school_type, 1.0)
            adjusted_score = max(score * adjustment_factor, 1.00)

            student_info = {
                'name': student_name,
                'school_type': school_type,
                'field': field,
                'detail_fields': detail_fields_selected,
                'score': round(score, 2),
                'adjusted_score': round(adjusted_score, 2),
                'lowest_ability': lowest_ability,
                'lowest_ability_code': lowest_ability_code,
                'non_subject_level': non_subject_level,
                'major_subjects_strong': major_subjects_strong,
                'gender': gender,
                'admission_type': admission_type
            }

            st.session_state['user_student_info'] = student_info
            st.success("아래와 같이 정보 입력이 완료되었습니다.")
            st.write(student_info)

        if st.button("보고서 생성", key="direct_report_generate"):
            if 'user_student_info' not in st.session_state:
                st.warning("학생 정보를 먼저 입력해주세요.")
            else:
                with st.spinner("보고서 작성 중입니다..."):
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(1)
                        progress_bar.progress(i + 1)

                    final_selection, new_advanced_data = process_uploaded_data(user_data, all_data)

                    st.session_state['final_selection'] = final_selection
                    st.session_state['user_new_advanced_data'] = new_advanced_data

                    html, tables, file_id = generate_report(final_selection, st.session_state['user_student_info'],
                                                            all_data, st.session_state['additional_data'])

                st.success("보고서 생성이 완료되었습니다!")
                st.components.v1.html(html, height=600, scrolling=True)
                st.success(f"보고서가 Google Drive에 업로드되었습니다. File ID: {file_id}")


if __name__ == "__main__":
    show_direct_upload()